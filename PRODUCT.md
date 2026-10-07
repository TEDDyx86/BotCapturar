# BotCapturar Product Context

<!-- impeccable:product-schema 1 -->

## Platform

Windows desktop application (Tkinter, Windows 10/11 x64). The current Impeccable platform enum has no desktop value; this record keeps the actual platform rather than mislabeling it as web or adaptive.

## Users

Kick live-chat moderators and other users who are authorized to send messages in a channel. The distributable is intended for people who may not be comfortable with APIs or OAuth configuration, so channel setup should accept a channel slug rather than require a numeric ID.

## Product Purpose

Send the fixed Kick chat command `$capturar` immediately when a user starts the automation, then every 305 seconds until the user stops it. Success means the user can leave the browser closed, see the send status/countdown, and stop the automation reliably.

## Positioning

A local Windows desktop tool that sends through Kick's official API using the user's own authorization; the user does not need a browser tab open while messages are being sent.

## Operating Context

- The recipient creates their own Kick Developer App and enters its Client ID and Client Secret locally.
- The user authorizes `chat:write` for their own Kick account.
- The user enters a channel slug such as `jukes`; the app resolves its numeric broadcaster ID through Kick's public API.
- OAuth secrets are stored in the current Windows user's Credential Manager.
- Recent activity is session-only and is discarded when the app closes.

## Capabilities and Constraints

- First message is sent immediately after Start; subsequent sends are separated by 305 seconds.
- Stop cancels future sends; the app does not auto-start sending when opened.
- The fixed message is `$capturar`; the initial release targets Kick and Windows 10/11 x64.
- The app uses Kick's official REST/OAuth APIs, channel slug resolution, and Windows Credential Manager.
- Each user configures their own Kick App; no user's Client Secret or OAuth token is embedded in shared executables or installers.
- The deliverable includes a portable no-console `.exe` and a per-user Windows installer.

## Brand Commitments

- Product name: **BotCapturar**; the visual identity is inspired by the user's retro-RPG project **Capturix**.
- Use the provided `novalogobot.png` as the bot/logo asset and `novalogonome.png` as the wordmark.
- Use `icone painel captura.png` as capture-panel art, `INFERFACEWALLPAPER.png` as the background source, and `INTERFACETOPO.png` as the top-banner source.
- Use `INTERFACE.png` as the user's approved visual reference for the desktop interface.
- The user authorizes generating additional visual assets if needed.

## Evidence on Hand

- `INTERFACE.png` — supplied desktop UI reference.
- `novalogobot.png` — supplied pixel-art bot logo.
- `novalogonome.png` — supplied BotCapturar wordmark.
- `icone painel captura.png` — supplied capture-panel item icon.
- `INFERFACEWALLPAPER.png` and `INTERFACETOPO.png` — supplied wallpaper and top-banner sources (the wallpaper source filename uses this spelling in the project folder).
- `README.md` — user setup, OAuth, channel slug, button sequence, and build instructions.

## Product Principles

1. Keep sending explicit: no message is sent until the user clicks Start.
2. Make Kick setup approachable: ask for the channel slug and explain each credential in the UI/docs.
3. Keep account secrets local to each Windows user and never include them in shared builds.
4. Keep operation visible: show connection/authorization state, recent session activity, and the next-send countdown.

## Accessibility & Inclusion

Keep all important states and actions understandable from text labels and status messages as well as color or imagery; controls must remain readable at standard Windows display scaling.
