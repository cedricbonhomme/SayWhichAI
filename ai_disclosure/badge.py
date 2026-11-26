"""Small images a project can show in its README.

The first says what its commits declare, the same as the first figure of the
project's page, in one line. The second says what its ai-policy.yaml file states:
the stance on code and the disclosure asked. The colour is the same whatever they
say: a high share is not a merit and a low one is not a fault, and no policy is
better than another.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

LABEL = "AI use"
POLICY_LABEL = "AI policy"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
CHARACTER = 6.2  # mean width of a character of the badge, in pixels

# The image carries its two sets of colours, the ones of the site: where it is shown
# as a picture (a README), it follows the theme of the reader's system.
STYLE = (
    ".l{fill:#52514e}.v{fill:#1c5cab}.lt,.vt{fill:#fff}"
    "@media (prefers-color-scheme:dark){.l{fill:#383835}.v{fill:#86b6ef}.lt{fill:#f0efec}.vt{fill:#0d0d0d}}"
)


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


# What the ai-policy.yaml file states, in a few words read after "AI policy:".
STANCE = {
    "generated": "generated code accepted",
    "assisted": "assistance accepted",
    "disallowed": "AI contributions not accepted",
}
DISCLOSURE = {"required": "declare it", "encouraged": "declaring encouraged", "prohibited": "leave AI notes out"}
STATUS = {"draft": "draft", "under-discussion": "under discussion"}


def policy_message(stated: dict | None) -> str:
    """The sentence of the policy badge, read after "AI policy:".

    stated is what the project's ai-policy.yaml file says, as read by policy.py, or
    None when the repository has no such file. The badge is written in every case,
    so that an image a README shows keeps saying what is true.
    """
    if stated is None:
        return "no ai-policy.yaml found"
    if not stated["readable"]:
        return f"{stated['file']} not understood"
    parts = [STANCE.get(stated["stance"]), DISCLOSURE.get(stated["disclosure"])]
    if stated["summary"] == "neutral":
        parts = ["ordinary rules apply"]
    text = " · ".join(part for part in parts if part) or "no rule for code stated"
    if stated["status"] in STATUS:
        text += f" ({STATUS[stated['status']]})"
    return text


def badge(report: dict) -> str:
    """The badge of what the commits of a project declare, as an SVG image."""
    return _image(LABEL, message(report))


def policy_badge(stated: dict | None) -> str:
    """The badge of what the ai-policy.yaml file of a project states, as an SVG image."""
    return _image(POLICY_LABEL, policy_message(stated))


def _image(name: str, text: str) -> str:
    # The length of each text is set, so that it fits whatever font the reader has.
    label, value = round(len(name) * CHARACTER), round(len(text) * CHARACTER)
    left, right = label + 12, value + 12
    width = left + right
    title = escape(f"{name}: {text}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{title}">'
        f"<title>{title}</title><style>{STYLE}</style>"
        f'<clipPath id="r"><rect width="{width}" height="20" rx="3"/></clipPath>'
        f'<g clip-path="url(#r)"><rect class="l" width="{left}" height="20"/>'
        f'<rect class="v" x="{left}" width="{right}" height="20"/></g>'
        '<g font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
        f'<text class="lt" x="{left / 2:g}" y="14" textLength="{label}">{escape(name)}</text>'
        f'<text class="vt" x="{left + right / 2:g}" y="14" textLength="{value}">{escape(text)}</text>'
        "</g></svg>\n"
    )
