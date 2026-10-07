from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_launcher_is_registered_as_gui_not_console_script():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert project.get("gui-scripts", {}).get("botcapturar") == "botcapturar.__main__:main"
    assert "botcapturar" not in project.get("scripts", {})


def test_pyinstaller_spec_builds_windowed_executable_with_windows_keyring_backend():
    spec = (ROOT / "packaging" / "BotCapturar.spec").read_text(encoding="utf-8")

    assert 'name="BotCapturar"' in spec
    assert "console=False" in spec
    assert "keyring.backends.Windows" in spec
    assert "win32ctypes.pywin32" in spec
    assert "project_root = Path(SPECPATH).resolve().parent\n" in spec
    assert "BotCapturar.ico" in spec
    assert 'project_root / "assets" / "BotCapturar.ico"' in spec


def test_inno_setup_is_per_user_and_does_not_remove_credentials():
    installer = (ROOT / "packaging" / "BotCapturar.iss").read_text(encoding="utf-8")

    assert "PrivilegesRequired=lowest" in installer
    assert "{localappdata}\\Programs\\BotCapturar" in installer
    assert "ArchitecturesAllowed=x64compatible" in installer
    assert "{autoprograms}\\BotCapturar" in installer
    assert 'Source: "..\\dist\\{#AppExeName}"' in installer
    assert "CredentialStore" not in installer
    assert "SetupIconFile=..\\assets\\BotCapturar.ico" in installer


def test_release_guide_requires_each_recipient_to_configure_their_own_kick_app():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "cada usuário" in readme
    assert "própria kick app" in readme
    assert "client secret" in readme


def test_readme_has_wordmark_at_top_and_explains_setup_and_button_order():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    normalized = readme.lower()
    guide = normalized.split("## configurar e usar", 1)[1].split("\n##", 1)[0]
    button_order = [
        guide.index("salvar e verificar canal"),
        guide.index("autorizar na kick"),
        guide.index("iniciar"),
        guide.index("parar"),
    ]

    assert readme.lstrip().startswith("![")
    assert "logo%20com%20nome.png" in readme
    assert "kick.com/jukes" in guide and "digite: jukes" in guide
    assert "client id" in normalized and "client secret" in normalized
    assert "identifica sua kick app" in normalized
    assert "chave privada da sua kick app" in normalized
    assert "redirect url" in normalized and "chat:write" in normalized
    assert "escrever no feed do chat" in normalized
    assert button_order == sorted(button_order)


def test_app_icon_is_a_multi_resolution_windows_icon():
    icon = (ROOT / "assets" / "BotCapturar.ico").read_bytes()

    assert icon[:4] == b"\x00\x00\x01\x00"
    assert int.from_bytes(icon[4:6], "little") >= 5


def test_release_build_runs_tests_and_requires_both_artifacts():
    build_script = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

    assert "pytest -q" in build_script
    assert "BotCapturar.spec" in build_script
    assert "ISCC.exe" in build_script
    assert "Programs\\Inno Setup 6\\ISCC.exe" in build_script
    assert "BotCapturar-Setup.exe" in build_script
    assert "BotCapturar.exe" in build_script
    assert "Get-CimInstance Win32_Process" in build_script
    assert "close it before rebuilding" in build_script.lower()
