import subprocess

def get_remote_commit(repo_url: str, branch: str) -> str | None:
    """Return the head commit SHA of a branch without cloning.
    Uses `git ls-remote`, a single lightweight network call."""
    # normalize: strip trailing .git/slash the same way the build does
    url = repo_url.strip().rstrip("/")
    if not url.endswith(".git"):
        url = url + ".git"
    try:
        out = subprocess.run(
            ["git", "ls-remote", url, branch],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    # output is "<sha>\t<ref>"; take the first line's SHA
    if not out:
        return None
    return out.split()[0]
