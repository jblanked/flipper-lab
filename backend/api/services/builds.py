"""
Build + cache logic for compiling apps into .fap files.

A .fap is built on demand and cached in a Build row so later requests
serve instantly. run_build_job drives a background BuildJob with progress;
get_or_build is the synchronous path used by the download view.
"""
import hashlib
import re
from pathlib import Path

from django.core.files import File as DjangoFile

from home.models import App

from home.compile import build

from .git import get_remote_commit

def _commit_for(app) -> str:
    """The source commit an app builds from (its branch's current head)."""
    return get_remote_commit(app.location_origin, app.branch or "main") or ""

def find_fap(build_result) -> str | None:
    """Extract the built .fap's path from build()'s result string.

    build() returns either an error message or a success message containing the
    absolute .fap path; this pulls the path out and confirms it exists.
    """
    if not isinstance(build_result, str) or build_result.startswith(("Failed", "Invalid")):
        return None

    # success messages embed the path, e.g. "...FAP file: /path/to/app.fap"
    m = re.search(r"(/[^\s:]+\.fap)", build_result)
    if m and Path(m.group(1)).exists():
        return m.group(1)

    # fallbacks: the result was a bare path, or a directory to search
    p = Path(build_result.strip())
    if p.suffix == ".fap" and p.exists():
        return str(p)
    root = p if p.is_dir() else p.parent
    if root.exists():
        hits = list(root.glob("**/*.fap"))
        if hits:
            return str(hits[0])
    return None

def cache_fap(app_id: int, firmware_id: int, fap_path: str, commit: str = ""):
    from home.models import Build

    data = Path(fap_path).read_bytes()
    md5 = hashlib.md5(data).hexdigest()

    build_row, _ = Build.objects.get_or_create(
        app_id=app_id, firmware_id=firmware_id,
        defaults={"size": len(data), "md5": md5, "commit": commit},
    )
    if not build_row.file:
        with open(fap_path, "rb") as fh:
            build_row.file.save(f"{app_id}-{firmware_id}.fap", DjangoFile(fh), save=False)
        build_row.size = len(data)
        build_row.md5 = md5
        build_row.commit = commit
        build_row.save()
    return build_row

def get_or_build(app_id: int, firmware_id: int):
    try:
        result = build(app_id, firmware_id)
    except Exception as e:
        return None, str(e)
    fap_path = find_fap(result)
    if not fap_path:
        return None, result
    commit = _commit_for(App.objects.get(id=app_id))
    return cache_fap(app_id, firmware_id, fap_path, commit), None

def run_build_job(job_id: int):
    """Background worker: build an app, reporting progress into its BuildJob."""
    from home.models import BuildJob

    job = BuildJob.objects.get(id=job_id)
    job.status = "running"
    job.save(update_fields=["status"])

    def progress(percent, message):
        # forwarded to build()'s progress_callback; capped at 99 until cached
        BuildJob.objects.filter(id=job.id).update(
            percent=min(int(percent), 99), message=str(message)[:255]
        )

    try:
        result = build(job.app_id, job.firmware_id, progress_callback=progress)
        fap_path = find_fap(result)
        if not fap_path:
            job.status = "failed"
            job.error = f"no .fap: {result}"[:2000]
            job.percent = 100
            job.save()
            return

        commit = _commit_for(App.objects.get(id=job.app_id))
        cache_fap(job.app_id, job.firmware_id, fap_path, commit)
        job.status = "done"
        job.percent = 100
        job.message = "Build complete"
        job.save()
    except Exception as e:
        job.status = "failed"
        job.error = str(e)[:2000]
        job.percent = 100
        job.save()
