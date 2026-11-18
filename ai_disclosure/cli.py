"""Command line: build the site of every project file."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

from . import __version__
from .config import ConfigError, load_projects
from .github import GitHub, GitHubError, find_token
from .gitlog import mirror, read_commits
from .report import build_report


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def build(args: argparse.Namespace) -> int:
    projects = load_projects(args.projects)
    local = dict(item.split("=", 1) for item in args.local)
    unknown = set(local) - {project.slug for project in projects}
    if unknown:
        raise ConfigError(f"--local names no project file: {', '.join(sorted(unknown))}")

    token = "" if args.no_github else find_token()
    github = GitHub(token) if token else None
    if not github:
        _log("No GitHub token: GitHub accounts and pull requests are left out.")

    output: Path = args.output
    data = output / "data"
    data.mkdir(parents=True, exist_ok=True)
    site = resources.files("ai_disclosure") / "site"
    for entry in site.iterdir():
        if entry.is_file():
            shutil.copyfile(entry, output / entry.name)

    index = []
    for project in projects:
        _log(f"{project.name}: reading the history of {project.repository}")
        repository = Path(local[project.slug]) if project.slug in local else mirror(project, args.cache)
        commits = read_commits(repository, project.branch)

        logins = pulls = None
        if github:
            branch = project.branch or "HEAD"
            _log(f"{project.name}: asking GitHub for accounts and pull requests")
            known_path = args.cache / f"{project.slug}-accounts.json"
            known = json.loads(known_path.read_text(encoding="utf-8")) if known_path.exists() else {}
            logins = github.commit_logins(project.repository, branch, known)
            args.cache.mkdir(parents=True, exist_ok=True)
            known_path.write_text(json.dumps(logins), encoding="utf-8")
            since = min((box.since for box in project.checkboxes if box.since), default="")
            if since:
                pulls = github.pull_requests(project.repository, since)

        report = build_report(project, commits, logins, pulls)
        (data / f"{project.slug}.json").write_text(
            json.dumps(report, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        totals = report["totals"]
        index.append(
            {
                "slug": project.slug,
                "name": project.name,
                "repository": project.repository,
                "trailer_since": project.trailer_since,
                "totals": totals,
            }
        )
        _log(
            f"{project.name}: {totals['commits']} commits, {totals['ai_commits']} declaring a model, "
            f"{totals['humans']} people, {len((report['pulls'] or {}).get('items', []))} pull requests"
        )

    (data / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    _log(f"Site written to {output}/")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-disclosure", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("build", help="read the projects and write the static site")
    command.add_argument("--projects", type=Path, default=Path("projects"), help="directory of project files")
    command.add_argument("--output", type=Path, default=Path("_site"), help="where to write the site")
    command.add_argument("--cache", type=Path, default=Path(".cache"), help="where the clones are kept")
    command.add_argument(
        "--local",
        action="append",
        default=[],
        metavar="SLUG=PATH",
        help="read this project from an existing clone instead of cloning it",
    )
    command.add_argument("--no-github", action="store_true", help="do not call the GitHub API")
    command.set_defaults(run=build)

    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except (ConfigError, GitHubError) as error:
        _log(f"error: {error}")
    except subprocess.CalledProcessError as error:
        _log(f"error: {' '.join(error.cmd)} failed: {(error.stderr or '').strip()}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
