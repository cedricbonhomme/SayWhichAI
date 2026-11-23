"""What the site tells search engines and link previews: the meta tags of each page,
robots.txt, sitemap.xml and .well-known/security.txt.

The address of the site is known only from its site file: without it, a page keeps
no absolute link and no sitemap is written, so that another site built with the tool
never points to this one.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from html import escape
from urllib.parse import quote

# Where a page of ai_disclosure/site/ receives the tags that need the address of the site.
MARK = "<!-- site meta -->"
NAME = "AI transparency for Open Source projects"
IMAGE = "og.png"
# security.txt must expire within a year (RFC 9116): the site is rebuilt every day.
VALIDITY = timedelta(days=90)

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
DESCRIPTION_RE = re.compile(r'<meta name="description" content="(.*?)">', re.DOTALL)


def page_url(url: str, page: str) -> str:
    """The public address of a page; the front page is the root of the site."""
    return f"{url}/" if page == "index.html" else f"{url}/{page}"


def page_meta(html: str, url: str, page: str) -> str:
    """The page with its canonical address and Open Graph tags, or without the mark when
    the address of the site is not known. Title and description are those of the page."""
    if not url:
        return html.replace(MARK + "\n", "")
    title = TITLE_RE.search(html).group(1)
    description = DESCRIPTION_RE.search(html).group(1)
    address = escape(page_url(url, page))
    tags = [
        f'<link rel="canonical" href="{address}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{escape(NAME)}">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{description}">',
        f'<meta property="og:url" content="{address}">',
        f'<meta property="og:image" content="{escape(url)}/{IMAGE}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    return html.replace(MARK, "\n".join(tags))


def robots(url: str) -> str:
    """Every crawler is welcome: the site only shows what is already public."""
    lines = ["User-agent: *", "Allow: /"]
    if url:
        lines.append(f"Sitemap: {url}/sitemap.xml")
    return "\n".join(lines) + "\n"


def sitemap(url: str, pages: list[str], slugs: list[str]) -> str:
    """The pages of the site, then the page of each project."""
    addresses = [page_url(url, page) for page in pages]
    addresses += [f"{url}/projects.html?project={quote(slug)}" for slug in slugs]
    entries = "".join(f"  <url><loc>{escape(address)}</loc></url>\n" for address in addresses)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}</urlset>\n"
    )


def security(fields: dict[str, str], url: str, now: datetime) -> str:
    """Where and how to report a vulnerability: the fields of the site file, in their
    order, with an expiry date and the canonical address."""
    expires = (now + VALIDITY).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [f"{key}: {value}" for key, value in fields.items()]
    lines.insert(1, f"Expires: {expires}")
    if url:
        lines.append(f"Canonical: {url}/.well-known/security.txt")
    return "\n".join(lines) + "\n"
