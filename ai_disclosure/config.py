"""Project files: one TOML file per project followed."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .models import Rule

REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Checkbox:
    id: str
    label: str
    match: tuple[str, ...]
    since: str


@dataclass(frozen=True)
class Project:
    slug: str
    name: str
    repository: str
    branch: str = ""
    policy_url: str = ""
    trailer_since: str = ""
    checkboxes: tuple[Checkbox, ...] = ()
    bots: frozenset[str] = frozenset()
    model_rules: tuple[Rule, ...] = field(default_factory=tuple)

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repository}"


def _date(value: object, where: str) -> str:
    text = str(value or "")
    if text and not DATE_RE.match(text):
        raise ConfigError(f"{where}: expected a date as YYYY-MM-DD, got {text!r}")
    return text


def load_project(path: Path) -> Project:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    where = str(path)

    project = data.get("project", {})
    repository = project.get("repository", "")
    if not REPOSITORY_RE.match(repository) or repository.startswith("-"):
        raise ConfigError(f"{where}: [project] repository must be 'owner/name', got {repository!r}")
    branch = project.get("branch", "")
    if branch.startswith("-"):
        raise ConfigError(f"{where}: invalid branch {branch!r}")

    policy = data.get("policy", {})
    checkboxes = []
    for index, box in enumerate(policy.get("checkbox", [])):
        match = box.get("match", [])
        match = [match] if isinstance(match, str) else list(match)
        if not box.get("id") or not match:
            raise ConfigError(f"{where}: [[policy.checkbox]] #{index + 1} needs an id and a match")
        checkboxes.append(
            Checkbox(
                id=box["id"],
                label=box.get("label", box["id"]),
                match=tuple(text.lower() for text in match),
                since=_date(box.get("since"), where),
            )
        )

    identities = data.get("identities", {})
    rules = []
    for rule in identities.get("model", []):
        if not rule.get("match") or not rule.get("family"):
            raise ConfigError(f"{where}: [[identities.model]] needs a match and a family")
        rules.append(
            Rule(rule["match"], rule.get("vendor", "Other"), rule["family"], str(rule.get("version", "")))
        )

    return Project(
        slug=path.stem,
        name=project.get("name") or repository.split("/")[1],
        repository=repository,
        branch=branch,
        policy_url=policy.get("url", ""),
        trailer_since=_date(policy.get("trailer_since"), where),
        checkboxes=tuple(checkboxes),
        bots=frozenset(name.lower() for name in identities.get("bots", [])),
        model_rules=tuple(rules),
    )


def load_projects(directory: Path) -> list[Project]:
    paths = sorted(directory.glob("*.toml"))
    if not paths:
        raise ConfigError(f"no project file (*.toml) in {directory}")
    return [load_project(path) for path in paths]
