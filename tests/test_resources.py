from pathlib import Path

import botcapturar.resources as resources


def test_resource_path_resolves_against_project_root_in_development():
    expected_root = Path(resources.__file__).resolve().parents[2]

    assert resources.resource_path("assets/BotCapturar.ico") == expected_root / "assets" / "BotCapturar.ico"


def test_resource_path_resolves_against_pyinstaller_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(resources.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert resources.resource_path("assets/BotCapturar.ico") == tmp_path / "assets" / "BotCapturar.ico"
