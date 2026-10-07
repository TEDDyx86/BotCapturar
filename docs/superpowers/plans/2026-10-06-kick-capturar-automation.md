# Local Kick `$capturar` Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Windows desktop application that sends `$capturar` immediately when started and then every 305 seconds while enabled, without an open browser window.

**Architecture:** A small Python desktop app separates scheduling, OAuth, Kick REST requests, credential storage, and UI. The scheduler owns start/stop and timing; the Kick client owns token refresh and `POST /public/v1/chat`. Each request is independent, so the UI reports API/authentication/send state rather than a persistent chat connection. The initial OAuth authorization may open a browser, but sending messages does not require an open browser.

**Tech Stack:** Python 3.12, Tkinter/ttk for the native local UI, `httpx` for Kick HTTPS requests, `keyring` for Windows Credential Manager secrets, and pytest for tests.

## Global Constraints

- Target Windows; application operates locally and requires the computer and network to remain available.
- Send the fixed message `$capturar` immediately on Start, then every 305 seconds.
- Send only while the user has explicitly started the application; Stop cancels future sends.
- Do not require a browser window to remain open.
- Use an account authorized to send messages in the channel.
- Do not log credentials or store them in plaintext.
- Do not send catch-up bursts after a transient API failure; schedule the next normal message 305 seconds after a successful send.
- Use the official Kick REST API `POST /public/v1/chat` and OAuth user authorization with `chat:write`.
- Never embed the Kick Client Secret in source code; collect it during local setup and store it in Windows Credential Manager.

---

## File Structure

- Create `pyproject.toml` — Python package metadata, runtime dependencies, and pytest configuration.
- Create `src/botcapturar/__init__.py` — package marker and application version.
- Create `src/botcapturar/kick_api.py` — official REST message-send client and typed API results/errors.
- Create `src/botcapturar/oauth.py` — PKCE authorization URL, loopback callback, code exchange, and token refresh.
- Create `src/botcapturar/scheduler.py` — start/stop lifecycle and 305-second send/retry scheduling.
- Create `src/botcapturar/credentials.py` — secure save/load/delete of Client Secret and OAuth access/refresh tokens via Windows Credential Manager.
- Create `src/botcapturar/controller.py` — settings, OAuth/API wiring, fixed message sender, and scheduler lifecycle.
- Create `src/botcapturar/ui.py` — Tkinter window, configuration fields, controls, and API/auth/next-send status.
- Create `src/botcapturar/__main__.py` — application entry point and dependency wiring.
- Create `tests/test_scheduler.py` — deterministic timing, immediate first send, stop, and transient failure behavior.
- Create `tests/test_credentials.py` — secure credential store behavior with a mocked keyring backend.
- Create `tests/test_controller.py` — settings, authorization, immediate fixed-message start, and stop behavior.
- Create `tests/test_ui.py` — UI-to-scheduler interactions with a mocked API; no live Kick account required.
- Create `tests/test_app_smoke.py` — entry-point launch wiring and no automatic send at startup.
- Create `README.md` — installation, configuration, start/stop behavior, and Windows launch instructions.

## Task 1: Verify the Official Kick REST/OAuth Contract

**Files:**
- Create: `docs/superpowers/research/kick-chat-transport.md`

**Interfaces:**
- Produces: a decision record documenting the official chat endpoint, OAuth requirements, message-send result, error behavior, and rate-limit handling.

- [x] Consult official Kick chat, channels, OAuth, app-setup, and FAQ documentation; sources and findings are recorded in `docs/superpowers/research/kick-chat-transport.md`.
- [x] Verify `POST /public/v1/chat`, `chat:write`, `broadcaster_user_id`, success response `data.is_sent`, and documented HTTP errors.
- [x] Verify OAuth app registration, authorization-code flow with PKCE, refresh-token exchange, use of a local redirect URI, and app access tokens for public channel lookup.
- [x] User created the Kick app, authorized `chat:write`, and confirmed the controlled live send worked.

**Validation:** The decision record includes sources, authentication requirements, and a clear GO/STOP conclusion.

## Task 2: Scaffold the Python App and Define the Kick REST Client

**Files:**
- Create: `pyproject.toml`
- Create: `src/botcapturar/__init__.py`
- Create: `src/botcapturar/kick_api.py`
- Create: `tests/test_kick_api.py`

**Interfaces:**
- Produces: `KickApiClient.send_chat_message(access_token: str, broadcaster_user_id: int, content: str) -> SendResult`, where `SendResult` includes `is_sent: bool` and `message_id: str`.
- Also produces: `KickApiClient.get_channel_by_slug(app_access_token: str, slug: str) -> ChannelInfo`, where `ChannelInfo` includes `slug: str` and `broadcaster_user_id: int`.
- Consumes: Task 1's verified endpoint and request/response fields.

- [x] Add package metadata for Python `>=3.12`, `httpx` runtime dependency, pytest configuration, and test dependency group in `pyproject.toml`.
- [x] Define typed request/result models and API error types in `src/botcapturar/kick_api.py`.
- [x] Write HTTP-mocked tests for channel lookup by slug, App Access Token bearer auth, channel-not-found response, message endpoint/body, successful `data.is_sent`, and API errors.
- [x] Run `python -m pytest tests/test_kick_api.py -q`; all client contract tests pass without network access.

## Task 3: Implement the Scheduling Lifecycle

**Files:**
- Create: `src/botcapturar/scheduler.py`
- Create: `tests/test_scheduler.py`

**Interfaces:**
- Consumes: a sender callback with signature `Callable[[], SendResult]`, allowing scheduler tests without HTTP or OAuth.
- Produces: `MessageScheduler(sender, interval_seconds=305, on_status=callback, clock=monotonic_clock, wait=interruptible_wait)` with `start()`, `stop()`, `is_running`, and `next_send_at`.

- [x] Use an injected monotonic clock and interruptible wait function so tests can advance time without sleeping in real time.
- [x] Write failing tests proving the first `$capturar` is sent as part of `start()` and a second send is scheduled after 305 seconds.
- [x] Write failing tests proving `stop()` interrupts the scheduled wait and prevents any later send.
- [x] Write failing tests proving transient API failures retry with bounded backoff and do not create catch-up bursts; after a successful send, the next send is scheduled 305 seconds later.
- [x] Write failing tests proving 401/403 errors stop automatic sends and report that reauthorization is required; verify HTTP 429 honors `Retry-After`.
- [x] Implement the scheduler loop with a stop signal that interrupts waits and prevents work after Stop.
- [x] Run `python -m pytest tests/test_scheduler.py -q`; all scheduler tests pass without real network access or multi-minute sleeps.

## Task 4: Implement OAuth and the Kick REST Client

**Files:**
- Create: `src/botcapturar/oauth.py`
- Create: `tests/test_oauth.py`

**Interfaces:**
- Implements: OAuth Authorization Code + PKCE with a local callback, user token refresh, and App Access Token request using `client_credentials` for public channel lookup.
- Consumes: Task 1's exact endpoints, `chat:write` scope, and token request/response fields.

- [x] Write mocked tests for PKCE/state generation, OAuth callback state validation, code exchange, refresh-token exchange, and token-expiry handling.
- [x] Implement a fixed local callback at `http://localhost:8765/callback`; open the system browser only for user authorization, validate OAuth `state`, then close the callback server after success or cancellation.
- [x] Implement user token exchange/refresh and App Access Token requests; classify invalid grants without logging token or Client Secret values.
- [x] Run `python -m pytest tests/test_oauth.py -q`; all OAuth tests pass with mocked HTTP and no live account.
- [x] User completed the controlled live test after OAuth authorization and confirmed the message appeared as expected.

## Task 5: Store Credentials Securely

**Files:**
- Create: `src/botcapturar/credentials.py`
- Create: `tests/test_credentials.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `CredentialStore.save(key: str, secret: str) -> None`, `load(key: str) -> str | None`, and `delete(key: str) -> None` for the developer Client Secret and OAuth access/refresh tokens.

- [x] Add `keyring` as a runtime dependency.
- [x] Write tests with a mocked keyring backend proving save/load/delete behavior and that errors do not include secret values.
- [x] Implement namespaced Credential Manager entries for this application; never write secrets into app config, logs, or README examples.
- [x] Run `python -m pytest tests/test_credentials.py -q`; all credential tests pass with the system keyring mocked.

## Task 6: Build the Window and Wire the Application

**Files:**
- Create: `src/botcapturar/ui.py`
- Create: `src/botcapturar/__main__.py`
- Create: `src/botcapturar/controller.py`
- Create: `tests/test_controller.py`
- Create: `tests/test_ui.py`

**Interfaces:**
- Consumes: `MessageScheduler`, `CredentialStore`, OAuth authorization controller, and `KickApiClient`.
- Produces: a window with broadcaster ID/account configuration, developer app setup, Start/Stop controls, API/auth status, and next-send countdown/time.

- [x] Write controller tests with fake scheduler/API proving slug resolution, fixed `$capturar` message, resolved broadcaster ID, OAuth token refresh, and Stop behavior.
- [x] Write UI interaction tests with fake controller proving that slug lookup is asynchronous, Start invokes the scheduler once, Stop cancels it, the secret is masked/cleared, and controls follow lookup/auth/run state.
- [x] Implement the Tkinter/ttk window; keep network/scheduler work off the Tk event loop and marshal status updates onto the UI thread with `after()`.
- [x] Disable Start until the slug resolves and OAuth tokens exist; provide Save/lookup and Authorize actions and clear/mask the Client Secret after saving.
- [x] Wire the entry point to load saved credentials, build OAuth/API/scheduler dependencies, and start `mainloop()`.
- [x] Run `python -m pytest tests/test_ui.py -q`; UI tests pass without calling the real Kick API.
- [x] Launch the app with Python 3.12/Tkinter; the real local UI opened and remained running.

## Task 7: Package, Document, and Verify the Windows App

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Modify: `pyproject.toml`
- Create: `tests/test_app_smoke.py`

**Interfaces:**
- Consumes: completed application entry point and user-visible behaviors from Tasks 1–6.

- [x] Document Python setup, dependency installation, Kick developer app/OAuth setup, secure credential handling, immediate send behavior, 305-second interval, API/retry status, and Stop behavior.
- [x] Add an application smoke test that constructs the app with a fake API client and confirms startup does not send until the user explicitly clicks Start.
- [x] Run `python -m pytest -q`; all 46 tests pass.
- [x] Run `python -m compileall src`; no syntax errors.
- [x] User manually tested the Windows UI and confirmed sending worked; packaged portable and installed executables also opened without a console.

## Self-Review

- Immediate send and repeating 305-second interval: Task 3, verified by deterministic tests.
- Explicit Start/Stop and no background sends before Start: Tasks 3, 6, and 7.
- Browser-independent sends: Task 1 official API findings and Task 4 REST implementation; OAuth browser use is limited to explicit authorization.
- API/authentication state and visible failures: Tasks 3, 4, and 6.
- Retry handling without catch-up bursts: Tasks 3 and 4.
- Credential safety: Task 5.
- Windows local UI and operation: Tasks 6 and 7.
- No unsupported Kick API/protocol assumption: Task 1 records official docs and Task 4 uses only the documented REST/OAuth contract.
