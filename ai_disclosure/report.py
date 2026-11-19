"""Turn commits and pull requests into the figures the site draws.

Wording matters here. A commit without a trailer naming a model is a commit
with "no AI declared": nothing proves that no AI tool was used.

E-mail addresses are used to recognise people and never written to the report.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .config import Checkbox, Project
from .gitlog import Commit
from .models import TOOLS, Model, co_authors, identify

NOREPLY_RE = re.compile(r"^(?:\d+\+)?(?P<login>[^@]+)@users\.noreply\.github\.com$", re.I)
CHECKBOX_RE = re.compile(r"^\s*[-*+]\s*\[(?P<mark>[ xX])\]\s*(?P<text>.*)$", re.M)
MAX_FAMILIES = 7
HEAVIEST = 5
OTHER = "Other models"


@dataclass
class Person:
    """Someone (or something) commits are credited to."""

    kind: str  # "human", "agent" (an AI agent with no human co-author) or "bot"
    name: str
    login: str = ""
    commits: int = 0
    ai_commits: int = 0
    since_commits: int = 0
    since_ai_commits: int = 0
    lines: int = 0
    ai_lines: int = 0
    since_lines: int = 0
    since_ai_lines: int = 0
    first: str = ""
    last: str = ""
    ai_first: str = ""  # day of the first commit naming a model
    families: Counter = field(default_factory=Counter)
    models: Counter = field(default_factory=Counter)


@dataclass(frozen=True)
class Credit:
    key: str
    kind: str
    name: str
    login: str
    models: tuple[Model, ...]


class Identities:
    """Who a name and an e-mail address are, with the help of GitHub accounts."""

    def __init__(self, project: Project, commits: list[Commit], logins: dict[str, str]):
        self.project = project
        self.by_email: dict[str, str] = {}
        names: dict[str, set[str]] = {}
        for commit in commits:
            login = logins.get(commit.sha)
            if login:
                self.by_email.setdefault(commit.author_email.lower(), login)
                names.setdefault(commit.author_name.lower(), set()).add(login)
        # A name that belongs to one account only also covers the commits of that
        # person made with an address GitHub does not know.
        self.by_name = {name: next(iter(found)) for name, found in names.items() if len(found) == 1}

    def login(self, email: str, name: str = "") -> str:
        email = email.lower()
        if email in self.by_email:
            return self.by_email[email]
        found = NOREPLY_RE.match(email)
        if found and "[bot]" not in email:
            return found.group("login")
        return self.by_name.get(name.lower(), "")

    def is_bot(self, name: str, login: str = "") -> bool:
        return (
            name.lower().endswith("[bot]")
            or name.lower() in self.project.bots
            or (login.lower() in self.project.bots if login else False)
        )

    def key(self, name: str, email: str, login: str) -> str:
        if login:
            return f"login:{login.lower()}"
        return f"email:{email.lower()}" if email else f"name:{name.lower()}"

    def credit(self, name: str, email: str, message: str, login: str = "") -> Credit:
        """Who a commit is credited to, and the models it declares."""
        rules = list(self.project.model_rules)
        trailers = co_authors(message, rules)
        models = [trailer.model for trailer in trailers if trailer.model]
        login = login or self.login(email, name)

        agent = identify(name, email, rules)
        if agent:
            # An AI agent authored the commit. The person it worked for is named as
            # co-author; without one the commit stays under the agent's own name.
            models = _unique([agent, *models])
            for trailer in trailers:
                if trailer.model or self.is_bot(trailer.name):
                    continue
                human_login = self.login(trailer.email, trailer.name)
                return Credit(
                    self.key(trailer.name, trailer.email, human_login),
                    "human",
                    trailer.name,
                    human_login,
                    tuple(models),
                )
            return Credit(f"agent:{agent.family.lower()}", "agent", agent.family, "", tuple(models))

        kind = "bot" if self.is_bot(name, login) else "human"
        return Credit(self.key(name, email, login), kind, name, login, tuple(_unique(models)))


def _unique(models: list[Model]) -> list[Model]:
    return list(dict.fromkeys(models))


def build_report(
    project: Project,
    commits: list[Commit],
    logins: dict[str, str] | None,
    pulls: list[dict] | None,
    lines: dict[str, list[int]] | None = None,
) -> dict:
    """The whole report of a project. logins, pulls and lines are None without GitHub access.

    lines gives the lines each commit adds and deletes. They are the lines changed
    by a commit that names a model or not, never the lines "written by" a model.
    """
    identities = Identities(project, commits, logins or {})
    since = project.trailer_since

    people: dict[str, Person] = {}
    months: dict[str, dict] = {}
    model_stats: dict[Model, dict] = {}
    family_commits: Counter = Counter()
    family_vendor: dict[str, str] = {}
    weights: list[tuple[int, Commit, str]] = []  # lines changed, commit, family named
    unknown = 0  # commits GitHub gave no figure for
    several = 0  # commits naming more than one model
    days: Counter = Counter()  # commits naming a model, day by day

    for commit in commits:
        credit = identities.credit(
            commit.author_name, commit.author_email, commit.message, (logins or {}).get(commit.sha, "")
        )
        day = commit.date[:10]
        in_policy = bool(since) and day >= since

        person = people.get(credit.key)
        if person is None:
            person = people[credit.key] = Person(credit.kind, credit.name, credit.login)
        person.login = person.login or credit.login
        person.commits += 1
        person.since_commits += in_policy
        person.first = min(person.first or day, day)
        person.last = max(person.last, day)
        changed = sum((lines or {}).get(commit.sha, ())[:2])
        unknown += lines is not None and commit.sha not in lines
        person.lines += changed
        person.since_lines += changed * in_policy

        month = months.setdefault(
            day[:7],
            {"none": 0, "bots": 0, "families": Counter(), "lines_none": 0, "lines_families": Counter()},
        )
        if credit.kind == "bot" and not credit.models:
            month["bots"] += 1
            continue
        weights.append((changed, commit, credit.models[0].family if credit.models else ""))
        if not credit.models:
            month["none"] += 1
            month["lines_none"] += changed
            continue

        person.ai_commits += 1
        person.since_ai_commits += in_policy
        person.ai_first = min(person.ai_first or day, day)
        days[day] += 1
        person.ai_lines += changed
        person.since_ai_lines += changed * in_policy
        # A commit that names two models counts once in the totals, under the first one.
        primary = credit.models[0].family
        several += len(credit.models) > 1
        month["families"][primary] += 1
        month["lines_families"][primary] += changed
        family_commits[primary] += 1
        person.families[primary] += 1
        for model in credit.models:
            family_vendor[model.family] = model.vendor
            person.models[model.label] += 1
            stats = model_stats.setdefault(
                model, {"commits": 0, "lines": 0, "first": day, "last": day, "people": set()}
            )
            stats["commits"] += 1
            stats["lines"] += changed
            stats["first"] = min(stats["first"], day)
            stats["last"] = max(stats["last"], day)
            if credit.kind == "human":
                stats["people"].add(credit.key)

    # Colours follow the families: keep the order stable, most used first, and fold the tail.
    ranked = [family for family, _ in family_commits.most_common()]
    kept = ranked if len(ranked) <= MAX_FAMILIES + 1 else ranked[:MAX_FAMILIES]
    folded = set(ranked) - set(kept)

    def fold(counter: Counter) -> dict[str, int]:
        result: Counter = Counter()
        for family, count in counter.items():
            result[OTHER if family in folded else family] += count
        return dict(result)

    families = [
        {
            "id": family,
            "vendor": family_vendor.get(family, ""),
            "commits": family_commits[family],
            "tool": family in TOOLS,
        }
        for family in kept
    ]
    if folded:
        families.append(
            {"id": OTHER, "vendor": "", "commits": sum(family_commits[family] for family in folded), "tool": False}
        )

    humans = [person for person in people.values() if person.kind == "human"]
    human_commits = sum(person.commits for person in humans)
    human_ai = sum(person.ai_commits for person in humans)

    report = {
        "project": {
            "slug": project.slug,
            "name": project.name,
            "repository": project.repository,
            "url": project.url,
            "policy_url": project.policy_url,
            "trailer_since": since,
        },
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "github": logins is not None,
        "totals": {
            "commits": sum(person.commits for person in people.values()),
            "human_commits": human_commits,
            "ai_commits": human_ai,
            "since_commits": sum(person.since_commits for person in humans),
            "since_ai_commits": sum(person.since_ai_commits for person in humans),
            "humans": len(humans),
            "humans_with_ai": sum(1 for person in humans if person.ai_commits),
            # A tool that does not say which model it runs on is not counted as a model.
            "models": sum(1 for model in model_stats if not model.tool),
            "tools": sum(1 for model in model_stats if model.tool),
            "first": commits[0].date[:10] if commits else "",
            "last": max((commit.date[:10] for commit in commits), default=""),
        },
        "families": families,
        "months": [
            {
                "month": month,
                "none": values["none"],
                "bots": values["bots"],
                "families": fold(values["families"]),
                **(
                    {"lines": {"none": values["lines_none"], "families": fold(values["lines_families"])}}
                    if lines is not None
                    else {}
                ),
            }
            for month, values in sorted(months.items())
        ],
        "models": [
            {
                "label": model.label,
                "vendor": model.vendor,
                "family": OTHER if model.family in folded else model.family,
                "tool": model.tool,
                "commits": stats["commits"],
                "lines": stats["lines"],
                "first": stats["first"],
                "last": stats["last"],
                "people": len(stats["people"]),
            }
            for model, stats in sorted(
                model_stats.items(), key=lambda item: (-item[1]["commits"], item[0].label)
            )
        ],
        "contributors": [_person(person, fold) for person in _ranked(humans)],
        "others": [
            _person(person, fold)
            for person in _ranked([person for person in people.values() if person.kind != "human"])
        ],
        # The same counts before the smaller families are folded into one: what the
        # statistics of all the projects are added up from.
        "named": {
            "families": {
                family: {
                    "vendor": family_vendor.get(family, ""),
                    "tool": family in TOOLS,
                    "models": sorted(model.label for model in model_stats if model.family == family),
                }
                for family in sorted(family_vendor)
            },
            "months": {
                month: dict(values["families"]) for month, values in sorted(months.items()) if values["families"]
            },
            "several": several,
            "days": dict(sorted(days.items())),
        },
        "pulls": None,
        "lines": None,
    }
    if lines is not None:
        weights.sort(key=lambda item: (-item[0], item[1].sha))
        report["lines"] = {
            "changed": sum(person.lines for person in humans),
            "named": sum(person.ai_lines for person in humans),
            "since_changed": sum(person.since_lines for person in humans),
            "since_named": sum(person.since_ai_lines for person in humans),
            # Every commit that is not a bot's, with or without a human behind it:
            # what the months add up to.
            "charted": sum(changed for changed, _, _ in weights),
            "unknown_commits": unknown,
            "heaviest": [
                {
                    "sha": commit.sha,
                    "title": commit.message.strip().split("\n", 1)[0][:120],
                    "date": commit.date[:10],
                    "lines": changed,
                    "family": OTHER if family in folded else family,
                }
                for changed, commit, family in weights[:HEAVIEST]
                if changed
            ],
        }
    if pulls is not None and project.checkboxes:
        report["pulls"] = pull_report(project, identities, pulls)
    return report


def recent_months(report: dict, count: int = 24) -> dict:
    """The last months of a report, up to the month it was built: commits, and those naming a model.

    For the small chart of the overview. Commits by bots are left out, as in the
    chart of the project.
    """
    year, month = int(report["generated_at"][:4]), int(report["generated_at"][5:7])
    wanted = []
    for _ in range(count):
        wanted.append(f"{year:04d}-{month:02d}")
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    wanted.reverse()
    known = {entry["month"]: entry for entry in report["months"]}
    named = [sum(known[key]["families"].values()) if key in known else 0 for key in wanted]
    commits = [known[key]["none"] + count if key in known else 0 for key, count in zip(wanted, named)]
    return {"from": wanted[0], "commits": commits, "named": named}


def _ranked(people: list[Person]) -> list[Person]:
    return sorted(people, key=lambda person: (-person.commits, person.name.lower()))


def _person(person: Person, fold) -> dict:
    return {
        "kind": person.kind,
        "name": person.name,
        "login": person.login,
        "commits": person.commits,
        "ai_commits": person.ai_commits,
        "since_commits": person.since_commits,
        "since_ai_commits": person.since_ai_commits,
        "lines": person.lines,
        "ai_lines": person.ai_lines,
        "first": person.first,
        "last": person.last,
        "ai_first": person.ai_first,
        "families": fold(person.families),
        "models": [
            {"label": label, "commits": count}
            for label, count in sorted(person.models.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


def checkbox_state(body: str, checkbox: Checkbox) -> str:
    """"ticked", "unticked", or "missing" when the box is not in the description."""
    state = "missing"
    for found in CHECKBOX_RE.finditer(body or ""):
        text = found.group("text").lower()
        if any(match in text for match in checkbox.match):
            if found.group("mark") != " ":
                return "ticked"
            state = "unticked"
    return state


def pull_report(project: Project, identities: Identities, pulls: list[dict]) -> dict:
    """Compare what each pull request says (its boxes) with what its commits say (their trailers)."""
    ai_box = next((box for box in project.checkboxes if box.id == "ai"), None)
    items = []
    skipped_bots = 0
    for pull in pulls:
        author = pull.get("author") or {}
        login = author.get("login", "")
        if author.get("__typename") == "Bot" or identities.is_bot(login, login):
            skipped_bots += 1
            continue
        opened = pull["createdAt"][:10]

        models: Counter = Counter()
        model_commits = 0
        nodes = pull["commits"]["nodes"]
        for node in nodes:
            commit = node["commit"]
            commit_author = commit.get("author") or {}
            credit = identities.credit(
                commit_author.get("name") or "",
                commit_author.get("email") or "",
                commit["message"],
                ((commit_author.get("user") or {}).get("login")) or "",
            )
            if credit.models:
                model_commits += 1
                for model in credit.models:
                    models[model.label] += 1

        boxes = {
            box.id: checkbox_state(pull.get("body") or "", box) if opened >= box.since else "not-yet"
            for box in project.checkboxes
        }
        items.append(
            {
                "number": pull["number"],
                "title": pull["title"],
                "url": pull["url"],
                "author": login,
                "opened": opened,
                "state": "draft" if pull.get("isDraft") and pull["state"] == "OPEN" else pull["state"].lower(),
                "commits": pull["commits"]["totalCount"],
                "commits_read": len(nodes),
                "model_commits": model_commits,
                "models": [label for label, _ in models.most_common()],
                "boxes": boxes,
                "disclosure": _disclosure(boxes.get(ai_box.id) if ai_box else None, model_commits),
            }
        )

    return {
        "since": min((box.since for box in project.checkboxes if box.since), default=""),
        "checkboxes": [
            {"id": box.id, "label": box.label, "since": box.since} for box in project.checkboxes
        ],
        "skipped_bots": skipped_bots,
        "items": items,
    }


def _disclosure(ai_box: str | None, model_commits: int) -> str:
    """Do the AI box of the pull request and the trailers of its commits tell the same story?"""
    if ai_box in (None, "not-yet"):
        return "trailers" if model_commits else "none"
    if ai_box == "ticked":
        return "consistent-ai" if model_commits else "box-without-trailer"
    if model_commits:
        return "trailer-without-box"
    return "consistent-none" if ai_box == "unticked" else "template-missing"
