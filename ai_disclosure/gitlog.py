"""Read the commits of a project from a git clone."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import Project

_FIELD = "\x1f"
_RECORD = "\x1e"
_FORMAT = _FIELD.join(["%H", "%aN", "%aE", "%aI", "%B"]) + _RECORD


@dataclass(frozen=True)
class Commit:
    sha: str
    author_name: str
    author_email: str
    date: str  # ISO 8601, in the author's own time zone
    message: str


def _git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, errors="replace"
    )
    return result.stdout


def mirror(project: Project, cache: Path) -> Path:
    """Clone the project (history only, no file content) or refresh the clone."""
    path = cache / f"{project.slug}.git"
    if path.exists():
        _git("fetch", "--quiet", "--prune", "--filter=blob:none", "origin", cwd=path)
    else:
        cache.mkdir(parents=True, exist_ok=True)
        _git("clone", "--quiet", "--bare", "--filter=blob:none", f"{project.url}.git", str(path))
        # A bare clone does not track its remote: make later fetches update the branches.
        _git("config", "remote.origin.fetch", "+refs/heads/*:refs/heads/*", cwd=path)
    return path


def default_branch(repository: Path) -> str:
    for ref in ("refs/remotes/origin/HEAD", "HEAD"):
        try:
            return _git("symbolic-ref", "--short", ref, cwd=repository).strip()
        except subprocess.CalledProcessError:
            continue
    return "HEAD"


def read_commits(repository: Path, branch: str = "") -> list[Commit]:
    """The non-merge commits reachable from the branch, oldest first."""
    ref = branch or default_branch(repository)
    output = _git(
        "log", "--no-merges", "--reverse", f"--format={_FORMAT}", ref, "--", cwd=repository
    )
    commits = []
    for record in output.split(_RECORD):
        record = record.lstrip("\n")
        if not record:
            continue
        sha, name, email, date, message = record.split(_FIELD, 4)
        commits.append(Commit(sha, name, email, date, message))
    return commits


def read_changes(repository: Path, branch: str = "") -> dict[str, list[tuple[str, str]]]:
    """The files each non-merge commit adds (A), changes (M) or deletes (D).

    Comparing trees needs no file content, so a clone without it is enough.
    """
    ref = branch or default_branch(repository)
    output = _git(
        "-c", "core.quotePath=false", "log", "--no-merges", "--no-renames", "--name-status",
        f"--format={_RECORD}%H", ref, "--", cwd=repository,
    )
    changes = {}
    for record in output.split(_RECORD)[1:]:
        sha, _, body = record.partition("\n")
        files = []
        for line in body.splitlines():
            status, tab, path = line.partition("\t")
            if tab:
                files.append(({"A": "A", "D": "D"}.get(status[:1], "M"), path))
        changes[sha.strip()] = files
    return changes
