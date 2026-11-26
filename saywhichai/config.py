"""Project files: one TOML file per project followed."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .models import Rule

REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LOGO_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./ -]*\.(png|jpe?g|webp|gif|svg)$", re.IGNORECASE)


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Checkbox:
    id: str
    label: str
    match: tuple[str, ...]
    since: str


@dataclass(frozen=True)
class Subjects:
    """How the subject line of a commit names its kind and the part it touches."""

    pattern: re.Pattern
    aliases: dict[str, str] = field(default_factory=dict, compare=False)  # spelling -> the one it counts as

    def read(self, message: str) -> tuple[str, str] | None:
        """The kind and the scope of a commit (lowercase, "" when the pattern has no
        such group), or None when its subject line does not follow the pattern."""
        found = self.pattern.match(message.strip().split("\n", 1)[0])
        if not found:
            return None
        groups = found.groupdict()
        kind, scope = ((groups.get(name) or "").strip().lower() for name in ("kind", "scope"))
        return self.aliases.get(kind, kind), self.aliases.get(scope, scope)


@dataclass(frozen=True)
class Project:
    slug: str
    name: str
    repository: str
    branch: str = ""
    logo: str = ""  # the path of an image in the repository
    policy_url: str = ""
    trailer_since: str = ""
    checkboxes: tuple[Checkbox, ...] = ()
    bots: frozenset[str] = frozenset()
    model_rules: tuple[Rule, ...] = field(default_factory=tuple)
    subjects: Subjects | None = None
    # The sources of Vulnerability-Lookup searched for records citing a commit, () for
    # its default; None when the project file does not ask for the search.
    advisories: tuple[str, ...] | None = None

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

    logo = project.get("logo", "")
    if logo and (not LOGO_RE.match(logo) or ".." in logo):
        raise ConfigError(
            f"{where}: [project] logo must be the path of a PNG, JPEG, WebP, GIF or SVG image "
            f"in the repository, got {logo!r}"
        )

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
        subjects=_subjects(data.get("subjects"), where),
        advisories=_advisories(data.get("advisories"), where),
        slug=path.stem,
        name=project.get("name") or repository.split("/")[1],
        repository=repository,
        branch=branch,
        logo=logo,
        policy_url=policy.get("url", ""),
        trailer_since=_date(policy.get("trailer_since"), where),
        checkboxes=tuple(checkboxes),
        bots=frozenset(name.lower() for name in identities.get("bots", [])),
        model_rules=tuple(rules),
    )


def _subjects(table: object, where: str) -> Subjects | None:
    if table is None:
        return None
    if not isinstance(table, dict) or not isinstance(table.get("pattern"), str):
        raise ConfigError(f"{where}: [subjects] needs a pattern")
    try:
        pattern = re.compile(table["pattern"], re.IGNORECASE)
    except re.error as error:
        raise ConfigError(f"{where}: [subjects] pattern is not a regular expression: {error}") from None
    if not {"kind", "scope"} & set(pattern.groupindex):
        raise ConfigError(f"{where}: [subjects] pattern needs a group (?P<kind>...) or (?P<scope>...)")
    aliases = table.get("aliases", {})
    if not isinstance(aliases, dict) or not all(isinstance(value, str) for value in aliases.values()):
        raise ConfigError(f"{where}: [subjects.aliases] must map spellings to the one they count as")
    return Subjects(pattern, {key.lower(): value.lower() for key, value in aliases.items()})


def _advisories(table: object, where: str) -> tuple[str, ...] | None:
    if table is None:
        return None
    sources = table.get("sources", []) if isinstance(table, dict) else None
    if not isinstance(sources, list) or not all(
        isinstance(source, str) and re.match(r"^[a-z0-9_]+$", source) for source in sources
    ):
        raise ConfigError(f"{where}: [advisories] sources must be a list of source names, such as \"cvelistv5\"")
    return tuple(sources)


def load_site(path: Path) -> list[str]:
    """The names of the projects a site publishes, in the order of its overview."""
    with path.open("rb") as handle:
        names = tomllib.load(handle).get("site", {}).get("projects")
    if not isinstance(names, list) or not names or not all(isinstance(name, str) for name in names):
        raise ConfigError(f"{path}: [site] projects must be a list of project names")
    if len(set(names)) != len(names):
        raise ConfigError(f"{path}: a project is listed twice")
    return names


# The fields of security.txt (RFC 9116) a site file may give; Expires and Canonical are
# written by the build.
SECURITY_FIELDS = ("Contact", "Encryption", "Acknowledgments", "Policy", "Hiring", "Preferred-Languages")


def load_address(path: Path) -> tuple[str, dict[str, str]]:
    """The public address of a site, or an empty string, and the fields of its
    security.txt, or none: both are optional."""
    with path.open("rb") as handle:
        site = tomllib.load(handle).get("site", {})
    url = site.get("url", "")
    if not isinstance(url, str) or (url and not re.match(r"^https://[^\s\"<>]+$", url)):
        raise ConfigError(f"{path}: [site] url must be an https address")
    fields = site.get("security", {})
    if not isinstance(fields, dict):
        raise ConfigError(f"{path}: [site.security] must be a table of security.txt fields")
    for key, value in fields.items():
        if key not in SECURITY_FIELDS:
            raise ConfigError(f"{path}: [site.security] {key} is not one of {', '.join(SECURITY_FIELDS)}")
        if not isinstance(value, str) or not value or any(char in value for char in "\r\n"):
            raise ConfigError(f"{path}: [site.security] {key} must be a line of text")
    if fields and "Contact" not in fields:
        raise ConfigError(f"{path}: [site.security] needs a Contact")
    return url.rstrip("/"), fields


def load_projects(directory: Path, site: Path | None = None) -> list[Project]:
    """Every project file of the directory, or only those a site file lists."""
    paths = sorted(directory.glob("*.toml"))
    if not paths:
        raise ConfigError(f"no project file (*.toml) in {directory}")
    if site is None:
        return [load_project(path) for path in paths]
    known = {path.stem: path for path in paths}
    names = load_site(site)
    unknown = [name for name in names if name not in known]
    if unknown:
        raise ConfigError(f"{site}: no project file in {directory} for {', '.join(unknown)}")
    return [load_project(known[name]) for name in names]
