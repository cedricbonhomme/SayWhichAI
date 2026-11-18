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
