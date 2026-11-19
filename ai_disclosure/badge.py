"""A small image a project can show in its README: what its commits declare.

It says the same as the first figure of the project's page, in one line. The
colour is the same whatever the figure: a high share is not a merit and a low
one is not a fault.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

LABEL = "AI use"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
CHARACTER = 6.2  # mean width of a character of the badge, in pixels


def _day(iso: str) -> str:
    year, month, day = iso.split("-")
    return f"{int(day)} {MONTHS[int(month) - 1]} {year}"


def _percent(part: int, whole: int) -> str:
    value = 100 * part / whole
    return "<1%" if 0 < value < 1 else f"{round(value)}%"


def message(report: dict) -> str:
    """The sentence of the badge, read after "AI use:"."""
    totals = report["totals"]
    since = report["project"]["trailer_since"]
    if since:
        if not totals["since_commits"]:
            return f"declared since {_day(since)}"
        share = _percent(totals["since_ai_commits"], totals["since_commits"])
        return f"declared in {share} of commits since {_day(since)}"
    if not totals["human_commits"]:
        return "no commit yet"
    return f"declared in {_percent(totals['ai_commits'], totals['human_commits'])} of commits"


def badge(report: dict) -> str:
    """The badge of a project, as an SVG image."""
    text = message(report)
    # The length of each text is set, so that it fits whatever font the reader has.
    label, value = round(len(LABEL) * CHARACTER), round(len(text) * CHARACTER)
    left, right = label + 12, value + 12
    width = left + right
    title = escape(f"{LABEL}: {text}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{title}">'
        f"<title>{title}</title>"
        f'<clipPath id="r"><rect width="{width}" height="20" rx="3"/></clipPath>'
        f'<g clip-path="url(#r)"><rect width="{left}" height="20" fill="#52514e"/>'
        f'<rect x="{left}" width="{right}" height="20" fill="#1c5cab"/></g>'
        '<g fill="#fff" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
        f'<text x="{left / 2:g}" y="14" textLength="{label}">{escape(LABEL)}</text>'
        f'<text x="{left + right / 2:g}" y="14" textLength="{value}">{escape(text)}</text>'
        "</g></svg>\n"
    )
