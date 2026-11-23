from datetime import datetime, timezone
from importlib import resources

import pytest

from ai_disclosure.config import ConfigError, load_address
from ai_disclosure.meta import MARK, page_meta, robots, security, sitemap

URL = "https://example.org"
PAGE = f"""<head>
<title>Policies · A &amp; B</title>
<meta name="description" content="What a project states.">
{MARK}
<link rel="stylesheet" href="style.css">
</head>"""


def test_every_page_of_the_site_has_the_mark():
    for page in (resources.files("ai_disclosure") / "site").iterdir():
        if page.name.endswith(".html"):
            html = page.read_text(encoding="utf-8")
            assert html.count(MARK) == 1, page.name
            assert "<title>" in html and '<meta name="description" content="' in html, page.name


def test_the_meta_tags_repeat_the_title_and_the_description():
    html = page_meta(PAGE, URL, "policies.html")
    assert '<link rel="canonical" href="https://example.org/policies.html">' in html
    assert '<meta property="og:title" content="Policies · A &amp; B">' in html
    assert '<meta property="og:description" content="What a project states.">' in html
    assert '<meta property="og:image" content="https://example.org/og.png">' in html
    assert MARK not in html


def test_the_front_page_is_the_root_of_the_site():
    assert f'<link rel="canonical" href="{URL}/">' in page_meta(PAGE, URL, "index.html")


def test_without_an_address_no_absolute_link_is_written():
    html = page_meta(PAGE, "", "policies.html")
    assert MARK not in html and "canonical" not in html and "og:" not in html


def test_robots_welcome_every_crawler():
    assert robots(URL) == f"User-agent: *\nAllow: /\nSitemap: {URL}/sitemap.xml\n"
    assert "Sitemap" not in robots("")


def test_the_sitemap_lists_the_pages_and_the_projects():
    xml = sitemap(URL, ["index.html", "stats.html"], ["a&b"])
    assert f"<loc>{URL}/</loc>" in xml
    assert f"<loc>{URL}/stats.html</loc>" in xml
    assert f"<loc>{URL}/projects.html?project=a%26b</loc>" in xml


def test_security_txt_expires_and_publishes_no_mail():
    text = security("https://example.org/report", URL, datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert "Contact: https://example.org/report\n" in text
    assert "Expires: 2026-04-01T00:00:00Z\n" in text
    assert f"Canonical: {URL}/.well-known/security.txt\n" in text
    assert "@" not in text


def test_the_address_of_a_site_is_optional(tmp_path):
    site = tmp_path / "site.toml"
    site.write_text('[site]\nprojects = ["a"]\n')
    assert load_address(site) == ("", "")
    site.write_text('[site]\nprojects = ["a"]\nurl = "https://example.org/"\nsecurity = "https://example.org/s"\n')
    assert load_address(site) == ("https://example.org", "https://example.org/s")


@pytest.mark.parametrize("value", ['"http://example.org"', '"mailto:a@example.org"', "1", '"https://a b"'])
def test_the_address_of_a_site_must_be_https(tmp_path, value):
    site = tmp_path / "site.toml"
    site.write_text(f'[site]\nprojects = ["a"]\nurl = {value}\n')
    with pytest.raises(ConfigError):
        load_address(site)
