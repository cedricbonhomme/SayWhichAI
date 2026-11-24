import pytest

from ai_disclosure.config import ConfigError, load_projects


def project(directory, name):
    (directory / f"{name}.toml").write_text(f'[project]\nrepository = "example/{name}"\n')


def test_every_project_without_a_site_file(tmp_path):
    for name in ("b", "a"):
        project(tmp_path, name)
    assert [found.slug for found in load_projects(tmp_path)] == ["a", "b"]


def test_a_site_file_selects_and_orders(tmp_path):
    for name in ("a", "b", "c"):
        project(tmp_path, name)
    site = tmp_path / "site.txt"
    site.write_text('[site]\nprojects = ["c", "a"]\n')
    assert [found.slug for found in load_projects(tmp_path, site)] == ["c", "a"]


def test_a_site_file_must_name_existing_projects(tmp_path):
    project(tmp_path, "a")
    site = tmp_path / "site.txt"
    site.write_text('[site]\nprojects = ["a", "missing"]\n')
    with pytest.raises(ConfigError, match="missing"):
        load_projects(tmp_path, site)


def test_a_project_names_its_logo(tmp_path):
    (tmp_path / "a.toml").write_text('[project]\nrepository = "example/a"\nlogo = "static/img/icon-192.png"\n')
    assert load_projects(tmp_path)[0].logo == "static/img/icon-192.png"


@pytest.mark.parametrize("logo", ["logo.html", "../logo.png", "/etc/logo.png", "-x.png", "https://example.org/a.png"])
def test_a_logo_is_an_image_of_the_repository(tmp_path, logo):
    (tmp_path / "a.toml").write_text(f'[project]\nrepository = "example/a"\nlogo = "{logo}"\n')
    with pytest.raises(ConfigError, match="logo"):
        load_projects(tmp_path)


CIRCL = r"^(?P<kind>[a-z]+)(?=:|\s*\[):?\s*(?:\[(?P<scope>[^\]]+)\])?"


def test_a_project_reads_its_commit_subjects(tmp_path):
    (tmp_path / "a.toml").write_text(
        '[project]\nrepository = "example/a"\n'
        f"[subjects]\npattern = '{CIRCL}'\naliases = {{ docs = \"doc\" }}\n"
    )
    subjects = load_projects(tmp_path)[0].subjects
    assert subjects.read("fix: [security] Escape the URL\n\nbody") == ("fix", "security")
    assert subjects.read("Fix [Docs] typo") == ("fix", "doc")
    assert subjects.read("chg: Updated dependencies.") == ("chg", "")
    assert subjects.read("Removed CLAUDE.md.") is None


@pytest.mark.parametrize("table", ["pattern = '(unclosed'", "pattern = '^fix:'", "aliases = {}"])
def test_a_subject_pattern_must_be_usable(tmp_path, table):
    (tmp_path / "a.toml").write_text(f'[project]\nrepository = "example/a"\n[subjects]\n{table}\n')
    with pytest.raises(ConfigError, match="subjects"):
        load_projects(tmp_path)


def test_a_project_asks_for_vulnerability_records(tmp_path):
    (tmp_path / "a.toml").write_text('[project]\nrepository = "example/a"\n[advisories]\n')
    (tmp_path / "b.toml").write_text('[project]\nrepository = "example/b"\n[advisories]\nsources = ["cvelistv5"]\n')
    (tmp_path / "c.toml").write_text('[project]\nrepository = "example/c"\n')
    assert [found.advisories for found in load_projects(tmp_path)] == [(), ("cvelistv5",), None]


def test_advisory_sources_are_names(tmp_path):
    (tmp_path / "a.toml").write_text('[project]\nrepository = "example/a"\n[advisories]\nsources = "cvelistv5&x=1"\n')
    with pytest.raises(ConfigError, match="advisories"):
        load_projects(tmp_path)
