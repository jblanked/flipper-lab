import re
import threading
import time
from typing import Optional

import requests
import yaml
from django.utils import timezone

from home.models import App, Category, SyncRun

_branch_cache: dict[str, str] = {}
_cancel_events: dict[int, threading.Event] = {}

GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"

_RED = "\033[91m"
_YELLOW = "\033[93m"
_BLUE = "\033[94m"
_GRAY = "\033[90m"
_RESET = "\033[0m"


def __get_app_id_from_url(url: str) -> str:
    """Extracts the app ID from a catalog URL."""
    return url.split("/")[-2]


def __parse_github_repo(repo_url: str) -> Optional[tuple[str, str]]:
    """Parses a GitHub URL into (owner, repo)."""
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git|/)?$", repo_url)
    if match:
        owner = match.group(1)
        repo = match.group(2)
        return owner, repo
    return None


def __normalize_path(path: str) -> str:
    """Removes leading './' or '/' from a file path."""
    if path.startswith("./"):
        path = path[2:]
    elif path.startswith("/"):
        path = path[1:]
    return path


def __fetch_text_from_repo(owner: str, repo: str, commit_sha: str, file_path: str) -> str:
    """Fetches a text file from a GitHub repo at a specific commit."""
    url = f"{GITHUB_RAW}/{owner}/{repo}/{commit_sha}/{file_path}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def __resolve_repo_file_path(file_ref: str, subdir: Optional[str]) -> str:
    """Resolves a @-prefixed file ref to an absolute repo path."""
    path = file_ref.lstrip("@")
    path = __normalize_path(path)
    if subdir and not path.startswith(subdir):
        path = f"{subdir}/{path}"
    return path


def __build_raw_url(owner: str, repo: str, commit_sha: str, file_path: str) -> str:
    """Builds a raw.githubusercontent.com URL for a file."""
    return f"{GITHUB_RAW}/{owner}/{repo}/{commit_sha}/{file_path}"


def __get_default_branch(owner: str, repo: str) -> str:
    """Fetches the default branch from GitHub API, cached by owner/repo."""
    key = f"{owner}/{repo}"
    if key in _branch_cache:
        return _branch_cache[key]
    try:
        url = f"{GITHUB_API}/repos/{owner}/{repo}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        branch = resp.json().get("default_branch", "main")
        _branch_cache[key] = branch
        return branch
    except Exception as e:
        print(f"{_YELLOW}  Warning: Could not fetch default branch for {key}: {e}{_RESET}")
        return "main"


def fetch_manifests() -> dict:
    """Fetches all manifest URLs from the Flipper catalog, grouped by category."""
    url = f"{GITHUB_API}/repos/flipperdevices/flipper-application-catalog/git/trees/main?recursive=1"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    all_apps = [
        item["path"]
        for item in data["tree"]
        if item["path"].startswith("applications/")
        and item["path"].endswith("manifest.yml")
    ]
    categories = {}
    for app in all_apps:
        category = app.split("/")[1]
        if category not in categories:
            categories[category] = []
        categories[category].append(
            f"https://raw.githubusercontent.com/flipperdevices/flipper-application-catalog/main/{app}"
        )
    return categories


def load_manifest(url: str) -> dict:
    """Loads and parses a YAML manifest from a URL."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return yaml.safe_load(response.text)

def stop_sync() -> bool:
    """Request cancellation of any currently running sync.

    Returns True if a running sync was found and signalled to stop,
    False if there was nothing to cancel.
    """
    running = SyncRun.objects.filter(status=SyncRun.Status.RUNNING).first()
    if not running:
        return False

    event = _cancel_events.get(running.id)
    if event:
        event.set()
        print(f"{_BLUE}SyncRun #{running.id} cancellation requested{_RESET}")
    else:
        # No event registered, mark as failed.
        running.status = SyncRun.Status.FAILED
        running.error_message = "Stopped (no cancellation signal available)"
        running.finished_at = timezone.now()
        running.save()
    return True


def start_sync() -> bool:
    """Check for manifests and start syncing in a background thread.

    If a sync is already running it will be cancelled first.

    Returns True if manifests were found and a sync was started,
    False if no manifests are available.
    """
    stop_sync()

    try:
        app_manifests = fetch_manifests()
    except Exception as e:
        print(f"{_RED}Error fetching manifests: {e}{_RESET}")
        return False
    if not app_manifests:
        return False

    sync_run = SyncRun.objects.create(status=SyncRun.Status.RUNNING)
    cancel_event = threading.Event()
    _cancel_events[sync_run.id] = cancel_event

    def _run():
        try:
            print(f"{_BLUE}SyncRun #{sync_run.id} started{_RESET}")
            success, processed_count = sync_manifest(cancel_event=cancel_event)
            if cancel_event.is_set():
                # Cancelled mid-flight.
                sync_run.status = SyncRun.Status.CANCELLED
                sync_run.error_message = ""
            elif success:
                sync_run.status = SyncRun.Status.COMPLETED
            else:
                sync_run.status = SyncRun.Status.FAILED
                sync_run.error_message = "Sync completed but no apps were processed"
            sync_run.total_processed = processed_count
            print(f"{_BLUE}SyncRun #{sync_run.id} finished (status={sync_run.status}){_RESET}")
        except Exception as e:
            if cancel_event.is_set():
                sync_run.status = SyncRun.Status.CANCELLED
                sync_run.error_message = ""
            else:
                sync_run.status = SyncRun.Status.FAILED
                sync_run.error_message = str(e)
            _c = _BLUE if cancel_event.is_set() else _RED
            print(f"{_c}SyncRun #{sync_run.id} {'cancelled' if cancel_event.is_set() else 'failed'}: {e}{_RESET}")
        sync_run.finished_at = timezone.now()
        sync_run.save()
        _cancel_events.pop(sync_run.id, None)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return True

def sync_manifest(cancel_event: threading.Event | None = None) -> tuple[bool, int]:
    """Fetch manifests and sync manifest data.

    If *cancel_event* is provided and becomes set, the sync is aborted early.
    """
    try:
        app_manifests: dict = fetch_manifests()
    except Exception as e:
        print(f"{_RED}Error fetching manifests: {e}{_RESET}")
        return False, 0
    if not app_manifests:
        print(f"{_GRAY}No apps loaded{_RESET}")
        return False, 0
    if cancel_event and cancel_event.is_set():
        print(f"{_BLUE}Sync cancelled before processing started{_RESET}")
        return False, 0
    for category_name, manifest_urls in app_manifests.items():
        if cancel_event and cancel_event.is_set():
            print(f"{_BLUE}Sync cancelled mid-flight{_RESET}")
            return False, 0
        category, _ = Category.objects.get_or_create(name=category_name)
        for manifest_url in manifest_urls:
            if cancel_event and cancel_event.is_set():
                print(f"{_BLUE}Sync cancelled mid-flight{_RESET}")
                return False, 0
            time.sleep(3)  # Sleep to avoid hitting GitHub rate limits
            try:
                manifest_data = load_manifest(manifest_url)
                app_id = manifest_data.get("id", __get_app_id_from_url(manifest_url))
                if not app_id:
                    print(f"{_YELLOW}Manifest at {manifest_url} is missing 'id' field, skipping.{_RESET}")
                    continue
                sourcecode_key = manifest_data.get("sourcecode")
                if not sourcecode_key:
                    print(f"{_YELLOW}Manifest at {manifest_url} is missing 'sourcecode' field, skipping.{_RESET}")
                    continue
                repo_url = sourcecode_key.get("location", {}).get("origin")
                if not repo_url:
                    print(f"{_YELLOW}Manifest at {manifest_url} is missing 'location.origin' field, skipping.{_RESET}")
                    continue
                commit_sha = sourcecode_key.get("location", {}).get("commit_sha")
                subdir = sourcecode_key.get("location", {}).get("subdir")

                repo_info = __parse_github_repo(repo_url)
                owner = repo_info[0] if repo_info else None
                repo = repo_info[1] if repo_info else None

                branch = __get_default_branch(owner, repo) if owner and repo else "main"

                # Process changelog
                changelog = manifest_data.get("changelog", "")
                if changelog and "@" in changelog and owner and repo and commit_sha:
                    try:
                        file_path = __resolve_repo_file_path(changelog, subdir)
                        changelog = __fetch_text_from_repo(owner, repo, commit_sha, file_path)
                        print(f"{_GRAY}  Fetched changelog from {file_path}{_RESET}")
                    except Exception as e:
                        print(f"{_YELLOW}  Warning: Could not fetch changelog from '{changelog}': {e}{_RESET}")

                # Process description
                description = manifest_data.get("description", "")
                if description and "@" in description and owner and repo and commit_sha:
                    try:
                        file_path = __resolve_repo_file_path(description, subdir)
                        description = __fetch_text_from_repo(owner, repo, commit_sha, file_path)
                        print(f"{_GRAY}  Fetched description from {file_path}{_RESET}")
                    except Exception as e:
                        print(f"{_YELLOW}  Warning: Could not fetch description from '{description}': {e}{_RESET}")

                # Process icon
                icon = manifest_data.get("icon", "")
                if icon and owner and repo and commit_sha:
                    icon_path = __normalize_path(icon)
                    if subdir and not icon_path.startswith(subdir):
                        icon_path = f"{subdir}/{icon_path}"
                    icon = __build_raw_url(owner, repo, commit_sha, icon_path)
                else:
                    icon = ""

                # Process screenshots
                screenshots_raw = manifest_data.get("screenshots", [])
                screenshots = []
                if screenshots_raw and owner and repo and commit_sha:
                    for ss in screenshots_raw:
                        ss_path = __normalize_path(ss)
                        if subdir and not ss_path.startswith(subdir):
                            ss_path = f"{subdir}/{ss_path}"
                        screenshots.append(__build_raw_url(owner, repo, commit_sha, ss_path))

                app, created = App.objects.update_or_create(
                    fap_id=app_id,
                    defaults={
                        "author": manifest_data.get("author", "Unknown"),
                        "branch": branch,
                        "category": category,
                        "changelog": changelog,
                        "description": description,
                        "icon": icon,
                        "location_origin": repo_url,
                        "location_subdir": subdir or "",
                        "name": manifest_data.get("name", app_id),
                        "screenshots": screenshots,
                        "short_description": manifest_data.get("short_description", ""),
                        "version": manifest_data.get("version", "0.1"),
                    },
                )
                if created:
                    print(f"{_GRAY}Created new app: {app.name} (ID: {app.id}){_RESET}")
                else:
                    print(f"{_GRAY}Updated existing app: {app.name} (ID: {app.id}){_RESET}")
            except Exception as e:
                print(f"{_RED}Error processing manifest at {manifest_url}: {e}{_RESET}")
    return True, len(app_manifests)