"""Add up the reports of the projects into the figures of the statistics page.

The page says which models are named, all projects together. It names no project
and no person, so that it cannot be read as a ranking.

A commit is counted once, under the first model it names, as in the report of a
project. The list of the models counts a commit for every model it names.

Some trailers name a tool that does not say which model it runs on (GitHub
Copilot, for instance). Their commits declare the use of AI and are counted, but
the tool is not counted as a model.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from .report import MAX_FAMILIES, OTHER

MOST_MODELS = 5


def _months(first: str, last: str) -> list[str]:
    """Every month from first to last, both given as YYYY-MM."""
    year, month = int(first[:4]), int(first[5:7])
    months = []
    while f"{year:04d}-{month:02d}" <= last:
        months.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def build_stats(reports: list[dict]) -> dict:
    family_commits: Counter = Counter()
    family_vendor: dict[str, str] = {}
    tools: set[str] = set()  # families that are tools whose model is not named
    model_family: dict[str, str] = {}
    by_month: dict[str, Counter] = {}
    models: dict[str, dict] = {}
    people: dict[str, dict] = {}  # person -> month of the first commit naming a model, models named
    project_first: list[str] = []  # for each project, the month of its first commit naming a model
    days: Counter = Counter()
    lines = with_lines = several = 0
    last = ""

    for report in reports:
        named = report["named"]
        several += named["several"]
        days.update(named["days"])
        if named["months"]:
            project_first.append(min(named["months"]))
        is_tool = {model["label"]: model["tool"] for model in report["models"]}
        last = max(last, report["totals"]["last"])
        for family, facts in named["families"].items():
            family_vendor[family] = facts["vendor"]
            if facts["tool"]:
                tools.add(family)
            for label in facts["models"]:
                model_family[label] = family
        for month, families in named["months"].items():
            by_month.setdefault(month, Counter()).update(families)
            family_commits.update(families)
        for model in report["models"]:
            entry = models.setdefault(
                model["label"],
                {"label": model["label"], "vendor": model["vendor"], "tool": model["tool"], "commits": 0, "lines": 0,
                 "first": model["first"], "last": model["last"]},
            )
            entry["commits"] += model["commits"]
            entry["lines"] += model["lines"]
            entry["first"] = min(entry["first"], model["first"])
            entry["last"] = max(entry["last"], model["last"])
        # One person in several projects counts once: by GitHub account, or by name
        # when no account is known.
        for person in report["contributors"]:
            if person["ai_commits"]:
                known = people.setdefault(
                    person["login"].lower() or "name:" + person["name"].lower(), {"first": "9999", "models": set()}
                )
                known["first"] = min(known["first"], person["ai_first"][:7])
                known["models"].update(m["label"] for m in person["models"] if not is_tool[m["label"]])
        if report["lines"] is not None:
            with_lines += 1
            lines += sum(sum(month["lines"]["families"].values()) for month in report["months"])

    # Colours follow the families, as in the report of a project: most named first,
    # and the tail folded into one.
    ranked = [family for family, _ in sorted(family_commits.items(), key=lambda item: (-item[1], item[0]))]
    kept = ranked if len(ranked) <= MAX_FAMILIES + 1 else ranked[:MAX_FAMILIES]
    folded = set(ranked) - set(kept)

    def fold(counter: Counter) -> dict[str, int]:
        result: Counter = Counter()
        for family, count in counter.items():
            result[OTHER if family in folded else family] += count
        return dict(result)

    families = [
        {"id": family, "vendor": family_vendor[family], "commits": family_commits[family], "tool": family in tools}
        for family in kept
    ]
    if folded:
        families.append(
            {"id": OTHER, "vendor": "", "commits": sum(family_commits[family] for family in folded), "tool": False}
        )

    vendors: dict[str, dict] = {}
    for family, commits in family_commits.items():
        vendor = vendors.setdefault(
            family_vendor[family], {"name": family_vendor[family], "commits": 0, "models": 0, "tools": 0}
        )
        vendor["commits"] += commits
    for model in models.values():
        model["family"] = OTHER if model_family[model["label"]] in folded else model_family[model["label"]]
        if model["vendor"] in vendors:
            vendors[model["vendor"]]["tools" if model["tool"] else "models"] += 1

    first = min(by_month, default="")
    months = _months(first, max(last[:7], max(by_month))) if first else []

    # How many models a person named, tools left out. Five stands for five or more.
    counts = Counter(min(len(person["models"]), MOST_MODELS) for person in people.values())
    per_person = [{"models": size, "people": counts[size]} for size in range(1, max(counts, default=0) + 1)]

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "projects": len(reports),
        "totals": {
            "commits": sum(family_commits.values()),
            "several": several,
            # None when no project was read with GitHub access; else the lines of
            # the projects that were.
            "lines": lines if with_lines else None,
            "lines_projects": with_lines,
            "people": len(people),
            # Models, their families and their vendors: tools whose model is not
            # named are counted apart.
            "models": sum(1 for model in models.values() if not model["tool"]),
            "families": sum(1 for family in family_commits if family not in tools),
            "vendors": len({family_vendor[family] for family in family_commits if family not in tools}),
            "tools": sum(1 for model in models.values() if model["tool"]),
            "first": min((model["first"] for model in models.values()), default=""),
            "last": last,
        },
        "families": families,
        "months": [{"month": month, "families": fold(by_month.get(month, Counter()))} for month in months],
        # Month by month, the projects and the people with at least one commit
        # naming a model so far.
        "spread": [
            {
                "month": month,
                "projects": sum(1 for start in project_first if start <= month),
                "people": sum(1 for person in people.values() if person["first"] <= month),
            }
            for month in months
        ],
        "per_person": per_person,
        "tool_only_people": counts[0],
        "days": dict(sorted(days.items())),
        "models": sorted(models.values(), key=lambda model: (-model["commits"], model["label"])),
        "vendors": sorted(vendors.values(), key=lambda vendor: (-vendor["commits"], vendor["name"])),
    }
