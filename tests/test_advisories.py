from urllib.parse import parse_qs, urlparse

from ai_disclosure.advisories import cited_commits, resolve


def record(cve, *urls, adp=()):
    return {
        "cveMetadata": {"cveId": cve},
        "containers": {
            "cna": {"references": [{"url": url} for url in urls]},
            "adp": [{"references": [{"url": url} for url in adp]}],
        },
    }


def test_cited_commits_are_read_from_the_references():
    pages = {
        1: [
            record("CVE-2026-1", "https://github.com/MISP/MISP/commit/ABCDEF1234567"),
            record("CVE-2026-2", "https://example.org", adp=["https://github.com/misp/misp/pull/12/commits/abcdef1234567"]),
            # Another repository whose name starts the same way, and a commit named in a description only.
            record("CVE-2026-3", "https://github.com/MISP/MISP-modules/commit/1234567"),
            {"cveMetadata": {"cveId": "CVE-2026-4"}, "containers": {"cna": {"descriptions": ["github.com/MISP/MISP/commit/7654321"]}}},
            record("<b>bad id</b>", "https://github.com/MISP/MISP/commit/1111111"),
        ] + [record("CVE-2026-9", "https://example.org")] * 95,
        # A page without the repository ends the reading.
        2: [record("CVE-2026-5", "https://example.org")] * 100,
        3: [record("CVE-2026-6", "https://github.com/MISP/MISP/commit/2222222")],
    }
    asked = []

    def fetch(url):
        query = parse_qs(urlparse(url).query)
        asked.append(query)
        return {"data": pages[int(query["page"][0])]}

    assert cited_commits("MISP/MISP", ("cvelistv5",), fetch) == {"abcdef1234567": ["CVE-2026-1", "CVE-2026-2"]}
    assert [query["page"] for query in asked] == [["1"], ["2"]]
    assert asked[0]["sources"] == ["cvelistv5"]


def test_short_ids_are_resolved_in_the_history():
    shas = ["abcdef" + "0" * 34, "abc999" + "0" * 34, "123456" + "0" * 34]
    cited = {"abcdef0": ["CVE-1"], "abc": ["CVE-2"], shas[2]: ["CVE-3"], "fedcba9": ["CVE-4"]}
    # "abc" matches two commits, "fedcba9" none: both are left out.
    assert resolve(cited, shas) == {shas[0]: ["CVE-1"], shas[2]: ["CVE-3"]}
