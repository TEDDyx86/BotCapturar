from pathlib import Path

import botcapturar.resources as resources


def test_resource_path_resolves_against_project_root_in_development():
    expected_root = Path(resources.__file__).resolve().parents[2]

    assert resources.resource_path("assets/BotCapturar.ico") == expected_root / "assets" / "BotCapturar.ico"
    assert resources.resource_path("assets/INTERFACEWALLPAPER.png") == expected_root / "assets" / "INTERFACEWALLPAPER.png"
    assert resources.resource_path("assets/CapturixTop.png") == expected_root / "assets" / "CapturixTop.png"
    assert resources.resource_path("assets/CapturixCapture.png") == expected_root / "assets" / "CapturixCapture.png"
    assert resources.resource_path("assets/INTERFACEWALLPAPER.png") == expected_root / "assets" / "INTERFACEWALLPAPER.png"
    assert resources.resource_path("assets/CapturixTop.png") == expected_root / "assets" / "CapturixTop.png"
    assert resources.resource_path("novalogobot.png") == expected_root / "novalogobot.png"
    assert resources.resource_path("novalogonome.png") == expected_root / "novalogonome.png"


def test_resource_path_resolves_against_pyinstaller_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(resources.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert resources.resource_path("assets/BotCapturar.ico") == tmp_path / "assets" / "BotCapturar.ico"
    assert resources.resource_path("assets/INTERFACEWALLPAPER.png") == tmp_path / "assets" / "INTERFACEWALLPAPER.png"
    assert resources.resource_path("assets/CapturixTop.png") == tmp_path / "assets" / "CapturixTop.png"
    assert resources.resource_path("assets/CapturixCapture.png") == tmp_path / "assets" / "CapturixCapture.png"
    assert resources.resource_path("assets/INTERFACEWALLPAPER.png") == tmp_path / "assets" / "INTERFACEWALLPAPER.png"
    assert resources.resource_path("assets/CapturixTop.png") == tmp_path / "assets" / "CapturixTop.png"
