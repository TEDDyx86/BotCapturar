# BotCapturar Windows Distribution Design

**Date:** 2026-10-06
**Status:** Approved by the user

## Goal

Provide a Windows executable and installer for BotCapturar so recipients can launch the GUI without opening a terminal or installing Python.

## Distribution model

- Each recipient creates their own Kick Developer App and enters its Client ID and Client Secret directly in BotCapturar.
- No Client ID/Client Secret, OAuth token, or channel-specific credential is embedded in the executable or installer.
- OAuth tokens and app secrets remain in that Windows account's Credential Manager.
- Recipients authorize their own Kick account with `chat:write`.

## Packaging

- Register the application as a Windows GUI script so Python does not open an associated console window.
- Build a portable single-file GUI executable with PyInstaller (`console=False` / `--windowed`) for 64-bit Windows 10/11.
- Generate a multi-resolution square `.ico` from the root `logo bot.png` and use it for the Tk window, executable, installer, and shortcuts.
- Show the root `logo com nome.png` wordmark at the top of the README.
- Build a per-user installer with Inno Setup, installing under the user's LocalAppData Programs directory without administrator rights.
- Installer creates a Start Menu shortcut, offers an optional desktop shortcut, and supports normal uninstall.
- Installer does not delete user secrets from Windows Credential Manager during uninstall.

## Validation

1. Verify project metadata exposes a GUI entry point and no console entry point for the main application.
2. Build and launch the `.exe`; confirm the GUI opens without a terminal and Python is not required on the target machine.
3. Build and install the Inno Setup package as a non-admin user; verify Start Menu launch and uninstall.
4. Confirm the package contains no developer Client Secret or OAuth token.
5. Confirm each user must configure their own Kick App in the GUI before OAuth authorization.
6. Confirm the README logo, app icon, and installer icon all come from the requested root images.

## Constraints

- Build artifacts are Windows-specific and must be built on Windows.
- The packaged build must include Tcl/Tk and the Windows keyring backend.
- Unsigned artifacts may trigger Windows publisher warnings; signing is outside this initial scope.
