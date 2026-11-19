"""Add up the reports of the projects into the figures of the statistics page.

The page says which models are named, all projects together. It names no project
and no person, so that it cannot be read as a ranking.

A commit is counted once, under the first model it names, as in the report of a
project. The list of the models counts a commit for every model it names.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from .report import MAX_FAMILIES, OTHER


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
    model_family: dict[str, str] = {}
    by_month: dict[str, Counter] = {}
    models: dict[str, dict] = {}
    people: set[str] = set()
    lines = with_lines = several = 0
    last = ""

    for report in reports:
        named = report["named"]
        several += named["several"]
        last = max(last, report["totals"]["last"])
        for family, facts in named["families"].items():
            family_vendor[family] = facts["vendor"]
            for label in facts["models"]:
                model_family[label] = family
        for month, families in named["months"].items():
            by_month.setdefault(month, Counter()).update(families)
            family_commits.update(families)
        for model in report["models"]:
            entry = models.setdefault(
                model["label"],
                {"label": model["label"], "vendor": model["vendor"], "commits": 0, "lines": 0,
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
                people.add(person["login"].lower() or "name:" + person["name"].lower())
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

    families = [{"id": family, "vendor": family_vendor[family], "commits": family_commits[family]} for family in kept]
    if folded:
        families.append({"id": OTHER, "vendor": "", "commits": sum(family_commits[family] for family in folded)})

    vendors: dict[str, dict] = {}
    for family, commits in family_commits.items():
        vendor = vendors.setdefault(family_vendor[family], {"name": family_vendor[family], "commits": 0, "models": 0})
        vendor["commits"] += commits
    for model in models.values():
        model["family"] = OTHER if model_family[model["label"]] in folded else model_family[model["label"]]
        if model["vendor"] in vendors:
            vendors[model["vendor"]]["models"] += 1

    first = min(by_month, default="")
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
            "models": len(models),
            "families": len(family_commits),
            "vendors": len(vendors),
            "first": min((model["first"] for model in models.values()), default=""),
            "last": last,
        },
        "families": families,
        "months": [
            {"month": month, "families": fold(by_month.get(month, Counter()))}
            for month in (_months(first, max(last[:7], max(by_month))) if first else [])
        ],
        "models": sorted(models.values(), key=lambda model: (-model["commits"], model["label"])),
        "vendors": sorted(vendors.values(), key=lambda vendor: (-vendor["commits"], vendor["name"])),
    }
