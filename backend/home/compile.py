import sys
import os
import re
import importlib.util
from pathlib import Path
from contextlib import contextmanager
from .models import App, Firmware

_flipper_app_dir = Path(__file__).resolve().parent.parent.parent / "flipperzero-ufbt-app"
sys.path.insert(0, str(_flipper_app_dir))

# dedicated scratch workspace for downloaded repos + build artifacts.
# a SIBLING of backend/, so it's outside Django's autoreload watch path
BUILD_WORKSPACE = Path(__file__).resolve().parent.parent.parent / "build_workspace"


@contextmanager
def _in_workspace():
    """Run the enclosed block with CWD set to the build workspace, so the
    submodule's CWD-relative downloads/artifacts land there, not in backend/."""
    BUILD_WORKSPACE.mkdir(parents=True, exist_ok=True)
    prev = os.getcwd()
    os.chdir(BUILD_WORKSPACE)
    try:
        yield
    finally:
        os.chdir(prev)


def _load_submodule(name):
    """Import a module from the vendored submodule by file path."""
    spec = importlib.util.spec_from_file_location(name, _flipper_app_dir / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(app_id: int, firmware_id: int, progress_callback=None) -> str:
    """Build an app by its id, honoring its stored branch + subdir, and return
    the build-result message (which contains the .fap path). All downloads and
    artifacts happen inside BUILD_WORKSPACE."""
    app_object = App.objects.filter(id=app_id).first()
    if not app_object:
        raise ValueError(f'App with id {app_id} not found')
    firmware_object = Firmware.objects.filter(id=firmware_id).first()
    if not firmware_object:
        raise ValueError(f'Firmware with id {firmware_id} not found')

    branch = app_object.branch or "main"
    subdir = (app_object.location_subdir or "").strip("/")

    _main = _load_submodule("main")
    _download = _load_submodule("download")

    _map = {
        "official": _main.FIRMWARE_OFFICIAL,
        "momentum": _main.FIRMWARE_MOMENTUM,
        "unleashed": _main.FIRMWARE_UNLEASHED,
        "rogue_master": _main.FIRMWARE_ROGUE_MASTER,
    }
    firmware = _map.get(firmware_object.firmware_id, _main.FIRMWARE_OFFICIAL)

    # parse author/repo from the origin URL (strip trailing .git / slash)
    m = re.match(
        r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
        (app_object.location_origin or "").strip(),
    )
    if not m:
        return f"Invalid URL: {app_object.location_origin}"
    author, repo = m.groups()

    with _in_workspace():
        # download the repo (submodule's downloader) into ./{repo}
        if not _download.download_repo(author, repo, branch, progress_callback):
            return "Failed to download repository"

        # build the SUBDIR (or repo root if no subdir) via the submodule's inner build(), which takes a path and runs ufbt against it
        base = f"./{repo}/{repo}-{branch}"
        target = f"{base}/{subdir}" if subdir else base
        return _main.build(target, firmware, progress_callback)
