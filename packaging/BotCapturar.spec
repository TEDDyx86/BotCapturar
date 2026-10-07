# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata


project_root = Path(SPECPATH).resolve().parent
keyring_datas, keyring_binaries, keyring_hiddenimports = collect_all("keyring")

a = Analysis(
    [str(project_root / "src" / "botcapturar" / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=keyring_binaries,
    datas=keyring_datas
    + copy_metadata("keyring")
    + copy_metadata("pywin32-ctypes")
    + [(str(project_root / "assets" / "BotCapturar.ico"), "assets")],
    hiddenimports=keyring_hiddenimports + [
        "keyring.backends.Windows",
        "win32ctypes.pywin32",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BotCapturar",
    icon=str(project_root / "assets" / "BotCapturar.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
