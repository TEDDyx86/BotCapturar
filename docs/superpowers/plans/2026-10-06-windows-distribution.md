# BotCapturar Windows Executable and Installer Plan

> **For agentic workers:** Use this plan task-by-task; preserve the global constraints and validate each deliverable before proceeding.

**Goal:** Produce a no-console BotCapturar `.exe` and a per-user Windows installer that recipients can run without installing Python.

**Architecture:** Change the installed launcher to a Windows GUI script, build the app with PyInstaller as a windowed single-file executable, and wrap that executable in an Inno Setup installer. Each recipient creates and enters their own Kick App credentials; no secrets are packaged.

**Tech Stack:** Python 3.12, setuptools GUI scripts, PyInstaller 6.x, Inno Setup 6, PowerShell build script.

## Global Constraints

- Target Windows 10/11 x64.
- Do not include a Kick Client Secret, OAuth token, or per-user settings in build artifacts.
- Store each user's credentials in that Windows user's Credential Manager.
- Use PyInstaller windowed mode; application launch must not open a console.
- Installer is per-user and does not require administrator privileges.
- Uninstall removes program files and shortcuts but leaves the user's Credential Manager data intact.

---

## File Structure

- Modify `pyproject.toml` — replace the console script with a GUI script and add a build dependency group.
- Create `tests/test_packaging.py` — assert GUI entry-point metadata and absence of a console entry point.
- Create `packaging/BotCapturar.spec` — PyInstaller build graph with Windows GUI mode and keyring/Tk collection.
- Create `packaging/BotCapturar.iss` — per-user Inno Setup installer, shortcuts, and uninstall behavior.
- Create `assets/BotCapturar.ico` — multi-resolution app icon generated from root `logo bot.png`.
- Update `src/botcapturar/resources.py` and `src/botcapturar/ui.py` — locate the bundled icon and set the window icon.
- Create `scripts/build_windows.ps1` — deterministic tests, PyInstaller build, Inno compilation, and artifact checks.
- Update `README.md` — recipient setup, build prerequisites, artifact locations, and release steps.

## Task 1: Register a No-Console GUI Launcher

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/test_packaging.py`

**Interfaces:**
- Produces: GUI console-script metadata `botcapturar = "botcapturar.__main__:main"` under `[project.gui-scripts]`; no `botcapturar` entry under `[project.scripts]`.

- [x] Write a test loading `pyproject.toml` with `tomllib`; assert `project.gui-scripts.botcapturar` equals the exact entry point and `project.scripts` is absent or does not contain `botcapturar`.
- [x] Run `python -m pytest tests/test_packaging.py -q`; it failed first because current metadata registered a console script.
- [x] Move the entry point from `[project.scripts]` to `[project.gui-scripts]`.
- [x] Run `python -m pytest tests/test_packaging.py -q`; PASS.
- [x] Reinstall editable metadata in `.venv`; verify the generated Windows launcher has PE subsystem 2 (GUI).

## Task 2: Build a Portable Windowed Executable

**Files:**
- Modify: `pyproject.toml`
- Create: `packaging/BotCapturar.spec`
- Modify: `tests/test_packaging.py`

**Interfaces:**
- Produces: `dist/BotCapturar.exe`, built as one-file and windowed, with Python, Tcl/Tk, `httpx`, `keyring`, and the Windows Credential Manager backend bundled.

- [x] Add `pyinstaller>=6,<7` to the `build` optional dependency group.
- [x] Write a test asserting the PyInstaller spec exists and explicitly sets the executable to windowed mode (`console=False`).
- [x] Run the packaging test; it failed first because the spec did not exist.
- [x] Create the spec using `src/botcapturar/__main__.py` as entry script, `src` as import path, one-file EXE, `console=False`, the icon asset, and hidden imports/collection for `keyring.backends.Windows` and `win32ctypes.pywin32`.
- [x] Run the packaging tests; PASS.
- [x] Rebuild with PyInstaller after closing any running `dist\BotCapturar.exe`; confirm the root logo icon is present and `dist\BotCapturar.exe` is replaced.
- [x] Launch the rebuilt executable; confirm its window uses the bot icon and appears without a console.

## Task 3: Create the Per-User Installer

**Files:**
- Create: `packaging/BotCapturar.iss`
- Modify: `tests/test_packaging.py`

**Interfaces:**
- Produces: `dist/installer/BotCapturar-Setup.exe`.

- [x] Write tests verifying installer configuration uses `{localappdata}\Programs\BotCapturar`, `PrivilegesRequired=lowest`, the packaged executable, a Start Menu shortcut, and an uninstall entry.
- [x] Run packaging tests; they failed first because the installer definition did not exist.
- [x] Create the Inno Setup script with stable AppId, app name/version, app/setup icons, per-user install root, optional desktop shortcut, Start Menu shortcut, and uninstaller. No credential deletion commands are present.
- [x] Run packaging tests; PASS.
- [x] Recompile with `ISCC.exe packaging\BotCapturar.iss`; installer uses the bot icon and exists at `dist\installer\BotCapturar-Setup.exe`.
- [x] Install the rebuilt package in the current Windows user profile, verify icon/Start Menu shortcut and GUI launch, uninstall, and confirm a test Credential Manager entry survives.

## Task 4: Automate Release Build and Document Distribution

**Files:**
- Create: `scripts/build_windows.ps1`
- Modify: `README.md`
- Modify: `tests/test_packaging.py`

**Interfaces:**
- Produces: repeatable build command `powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1` and documented output locations.

- [x] Write a test asserting release documentation says each recipient configures their own Kick App and that no Client Secret is embedded in distributables.
- [x] Run packaging tests; they failed first until release instructions were updated.
- [x] Implement the build script to run the full test suite, build PyInstaller output, locate `ISCC.exe` (PATH and standard Inno Setup install paths), compile installer, and fail if either artifact is missing.
- [x] Update README with the wordmark at the top, a detailed Kick app/token/permission tutorial, ordered button instructions, channel slug example, build prerequisites, output paths, and security note that users enter their own credentials locally.
- [x] Run the build script; all 56 tests pass.
- [x] Run the PowerShell build script; both the standalone windowed `.exe` and installer were rebuilt with the logo icon.
- [x] Smoke-test the rebuilt portable and installed launch paths; verify the logo icon, no console, shortcut, uninstall, and credential preservation.

## Self-Review

- No terminal: Task 1 and PyInstaller `console=False` in Task 2.
- Standalone `.exe`: Task 2.
- Installer, per-user installation, shortcuts, uninstall: Task 3.
- Per-user OAuth and secret isolation: Global Constraints and Task 4 documentation.
- Build reproducibility and artifact existence: Task 4.
