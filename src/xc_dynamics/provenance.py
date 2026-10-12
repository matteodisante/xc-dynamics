"""Where and how a result was produced, saved next to it.

A run can happen on another machine; this record says which code produced the
result, so it can be checked before the thesis uses it.
"""

import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    """Output of a git command run in repo, or "" if git or the repository is missing."""
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return ""
    return done.stdout.strip()


def now() -> str:
    """Local time with its UTC offset, to the second: 2026-10-12T17:05:23+02:00."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run_record(repo: Path) -> dict:
    """The command, the commit of repo, and the machine of the current run."""
    return {
        "command": " ".join(sys.argv),
        "commit": git(repo, "rev-parse", "HEAD") or "unknown",
        # Any change not committed (files edited or added) means the commit alone
        # does not reproduce the run.
        "uncommitted_changes": bool(git(repo, "status", "--porcelain")),
        "machine": platform.node(),
        "system": platform.platform(),
        "python": platform.python_version(),
        "started": now(),
    }
