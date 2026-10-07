# Capturix RPG Interface Redesign Plan

> **For agentic workers:** Use this plan task-by-task; preserve its global constraints and verify each testable deliverable before proceeding.

**Goal:** Replace the plain BotCapturar window with the user-approved Capturix retro-RPG control room while preserving the Kick automation behavior.

**Architecture:** Keep Tkinter, `ApplicationController`, OAuth, and `MessageScheduler`. Add reusable theme/pixel-panel/progress components and a bounded in-memory activity model, then rebuild the window around the approved two-column layout. Use `novalogobot.png` as the bundled runtime bot asset; keep `novalogonome.png` as the README wordmark and regenerate the Windows icon from the new bot art.

**Tech Stack:** Python 3.12, Tkinter/ttk/Canvas, `collections.deque`, Pillow for one-off ICO conversion, PyInstaller, Inno Setup, pytest.

## Global Constraints

- Match `INTERFACE.png` as the composition reference and the Capturix retro-RPG pixel-art identity.
- Use `novalogobot.png` for the app/taskbar icon, header mark, and capture mascot; use `novalogonome.png` for the README wordmark.
- Rebuild real, responsive Tkinter controls; do not use the full screenshot as a flattened background.
- Preserve the exact channel lookup, Client ID/Secret, OAuth `chat:write`, Start/Stop, and current scheduler workflow.
- The app opens stopped and sends nothing until the user clicks **Iniciar**.
- First `$capturar` remains immediate; subsequent accepted sends remain 305 seconds apart.
- Recent activity is session-only, newest first, limited to five events, and is discarded on close.
- Keep field labels, status messages, keyboard focus, countdown, and Stop readable without relying only on color/art.
- Never package user credentials or OAuth tokens.

---

## File Structure

- Create `src/botcapturar/theme.py` — Capturix palette, type roles, spacing, and named state colors.
- Create `src/botcapturar/activity.py` — `ActivityEntry` and a five-event session-only log.
- Create `src/botcapturar/pixel_widgets.py` — gold-framed `PixelPanel` and a segmented countdown progress bar.
- Update `src/botcapturar/resources.py` — source and PyInstaller paths for the wallpaper, top banner, capture icon, and `.ico`.
- Replace `src/botcapturar/ui.py` — header, connection panel, capture dashboard, activity history, countdown, and button states.
- Update `tests/test_activity.py`, `tests/test_resources.py`, `tests/test_ui.py`; create `tests/test_theme.py` and `tests/test_pixel_widgets.py`.
- Regenerate `assets/BotCapturar.ico` from `novalogobot.png` at 16, 24, 32, 48, 64, 128, and 256 pixels.
- Bundle `assets/INTERFACEWALLPAPER.png`, `assets/CapturixTop.png`, and `assets/CapturixCapture.png` in `packaging/BotCapturar.spec` and set the executable icon.
- Update `packaging/BotCapturar.iss` to use the new Capturix icon.
- Update `README.md` to show `novalogonome.png` and preserve the step-by-step Kick setup guide.

## Task 1: Theme, Assets, and Session Activity Model

**Interfaces:**
- `theme.COLORS`, `theme.SPACING`, and `theme.FONTS` match `DESIGN.md` values.
- `resource_path(relative_path: str) -> Path` resolves from the source project or PyInstaller `_MEIPASS`.
- `SessionActivityLog(max_entries=5, clock=datetime.now)` exposes `add(message, state)` and immutable newest-first `entries`.

- [x] Write tests for palette/state colors, logo resource paths in source and `_MEIPASS`, and activity timestamp/order/retention/session reset.
- [x] Run `python -m pytest tests/test_theme.py tests/test_resources.py tests/test_activity.py -q`; verify red before implementation.
- [x] Add the theme constants and in-memory activity model.
- [x] Extend the PyInstaller data list to bundle the wallpaper, top banner, capture icon, and ICO under `assets`.
- [x] Generate the new ICO from `novalogobot.png` with transparent padding and standard Windows sizes, then verify all seven sizes are present.
- [x] Run the targeted tests; all pass.

## Task 2: Pixel-Art Panels and Countdown Bar

**Interfaces:**
- `PixelPanel(parent, title, ...)` exposes a Tk frame named `body` for ordinary widgets.
- `SegmentedProgressBar(parent, segments=36)` exposes `set_fraction(value: float)` clamped to `[0, 1]`.

- [x] Write tests with a fake Canvas for panel title/border drawing and for progress fractions at 0, 0.5, 1, and out-of-range values.
- [x] Run `python -m pytest tests/test_pixel_widgets.py -q`; verify red before implementation.
- [x] Implement stepped gold panel borders with dark-purple content surfaces; keep all interactive controls as normal Tk widgets inside `PixelPanel.body`.
- [x] Implement the progress Canvas with a gold frame, dark track, and green filled segments.
- [x] Run the targeted tests; all pass.

## Task 3: Rebuild the Main Window

**Files:** `src/botcapturar/ui.py`, `tests/test_ui.py`, `tests/test_controller.py` if callback wiring needs a regression assertion.

- [x] Extend tests to assert the header/mascot load the new assets, the titlebar uses the Capturix ICO, channel/credential buttons remain wired, startup is stopped, and no send happens before Start.
- [x] Add UI tests for `BOT PARADO`/`BOT ATIVO`, next-send countdown and progress, and session events for channel verification, authorization, successful send, error/retry, Start, and Stop.
- [x] Run the affected tests; verify red before implementation.
- [x] Build the resizable main window: Capturix bot-mark header, left Kick connection panel, right capture dashboard, lower recent-activity panel, and footer note.
- [x] Show the supplied capture-item icon beside the countdown; show `$capturar`, `5 min 05 s`, and the resolved channel as compact facts.
- [x] Keep channel resolution and OAuth authorization asynchronous; update status and activity on the Tk UI thread using `root.after()`.
- [x] Connect scheduler status to a five-entry session log; discard entries after closing the app.
- [x] Keep Start disabled until channel verification and OAuth readiness; keep Stop active only while sending is active; preserve no-autostart behavior.
- [x] Run the affected tests and full suite; all 71 tests passed.

## Task 4: Branding, Packaging, and Visual Verification

- [x] Replace the packaged ICO source with `novalogobot.png`; include the wallpaper, top-banner, capture-panel images, and ICO in the PyInstaller spec and use `assets/BotCapturar.ico` in the EXE and Inno Setup.
- [x] Place `novalogonome.png` at the top of README and document the redesigned layout and button sequence without altering verified Kick instructions.
- [x] Run `python -m pytest -q`; all 71 tests pass.
- [x] Close previous `dist/BotCapturar.exe` processes and run `powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1`.
- [x] Verify PE subsystem 2, embedded icon resources, portable launch, installed launch, Start Menu shortcut, uninstall, and preservation of Credential Manager data.
- [x] Compare the launched window with `INTERFACE.png`: hierarchy, wallpaper/top art, capture icon, panel geometry, countdown, activity log, and readable controls.
