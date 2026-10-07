<!--
THESIS: Turn a repetitive Kick command into a readable Capturix RPG control room, not a plain settings dialog.
OWN-WORLD: A deep violet pixel-art night scene with stepped gold panel frames, cream labels, green ready/success states, and crimson Stop; the supplied Capturix bot art is the mascot.
STORY: Configure the Kick app and channel once, authorize, start one immediate capture, then monitor the countdown and session events until Stop.
FIRST VIEWPORT: A branded pixel-art header spans two columns: Kick connection on the left; capture state, mascot, large countdown, progress, command details, and Start/Stop on the right; recent activity sits below.
FORM: Windows desktop Operate surface, built with functional Tkinter controls and Canvas-drawn pixel frames. Follows the user-pinned INTERFACE.png composition while preserving native keyboard/focus behavior and the no-autostart rule.
-->
---
name: BotCapturar — Capturix Control Room
description: Retro-RPG Windows control panel for the Kick $capturar automation.
colors:
  night-void: "#110C22"
  panel-deep: "#1D1032"
  panel-inset: "#150E29"
  text-cream: "#F5E8D7"
  text-muted: "#B9AAC7"
  frame-gold: "#F2BF4C"
  frame-gold-muted: "#9D7137"
  accent-purple: "#A54BE8"
  status-green: "#72EC4A"
  action-crimson: "#951440"
typography:
  display:
    fontFamily: "Consolas, Courier New, monospace"
    fontSize: "32px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "normal"
  title:
    fontFamily: "Consolas, Courier New, monospace"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "normal"
  body:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.35
    letterSpacing: "normal"
  label:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "normal"
rounded:
  none: "0px"
  pixel-cut: "4px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-start:
    backgroundColor: "{colors.status-green}"
    textColor: "{colors.night-void}"
    rounded: "{rounded.none}"
    padding: "12px 18px"
  button-stop:
    backgroundColor: "{colors.action-crimson}"
    textColor: "{colors.text-cream}"
    rounded: "{rounded.none}"
    padding: "12px 18px"
  input-channel:
    backgroundColor: "{colors.panel-inset}"
    textColor: "{colors.text-cream}"
    rounded: "{rounded.none}"
    padding: "10px 12px"
---

# Design System: BotCapturar — Capturix Control Room

## Overview

**Creative North Star: “A Capturix RPG Control Room.”**

The user-supplied `INTERFACE.png` is the composition reference: a violet night-sky console, sturdy pixel-cut gold frames, a clear two-column control layout, a large capture countdown, and a session log. The runtime background is `assets/INTERFACEWALLPAPER.png`; the top banner is a pixel-preserving crop of `INTERFACETOPO.png` in `assets/CapturixTop.png`. `novalogobot.png` is the app/taskbar identity, `icone painel captura.png` is the capture-panel item art, and `novalogonome.png` is the README wordmark. These supplied assets carry the Capturix-inspired retro-RPG identity; the UI screenshot remains a layout reference, not a static application background.

This is an Operate interface. The retro treatment must not hide the setup sequence or bot state. Editable fields, keyboard focus, visible labels, and familiar Start/Stop behavior remain intact. The app opens stopped; the first message is sent only after the user presses Start.

**Key Characteristics:**
- Deep-violet wallpaper with pixel-art framing and warm-gold hierarchy.
- Large, unmistakable countdown and a visually distinct active/stopped state.
- Capturix bot identity in the header and the supplied capture-item art in the capture panel.
- Session-only activity list; no durable activity history is written.

## Colors

The palette follows the supplied reference: night-violet surfaces, gold framing, cream text, and semantic green/crimson actions.

### Primary
- **Frame Gold** (`#F2BF4C`): stepped panel outlines, section titles, progress frame, and the primary save action.
- **Capturix Purple** (`#A54BE8`): OAuth action and secondary emphasis.

### Neutral
- **Night Void** (`#110C22`): root background and deep canvas regions.
- **Panel Deep** (`#1D1032`): card interiors.
- **Panel Inset** (`#150E29`): input and nested-detail backgrounds.
- **Cream Text** (`#F5E8D7`): primary text on dark surfaces.
- **Muted Lilac** (`#B9AAC7`): supporting labels and secondary text.

### Semantic
- **Ready Green** (`#72EC4A`): authorized, active, and successful states.
- **Stop Crimson** (`#951440`): the Stop action only.

**The State Color Rule.** Gold carries structure, not success; green means ready/active/sent, and crimson is reserved for Stop.

## Typography

**Display Font:** Consolas (fallback Courier New, monospace)
**Body Font:** Segoe UI (fallback Arial, sans-serif)
**Label/Mono Font:** Segoe UI for form labels; Consolas for the countdown and numeric status.

**Character:** Blocky RPG-console numerals and section titles sit over readable everyday labels and instructions. The supplied top-banner art provides the expressive lettering; body labels remain highly legible.

### Hierarchy
- **Display** (bold, 32px, 1.1): the next-send countdown.
- **Headline** (bold, 22px, 1.15): the app title and primary console title.
- **Title** (bold, 18px, 1.2): panel headings.
- **Body** (regular, 14px, 1.35): status descriptions and activity events.
- **Label** (semibold, 13px, 1.2): field labels and command/interval details.

## Layout

The default window is a landscape control room. A branded header spans the top; beneath it, a narrower Kick connection panel sits left of a wider capture panel. The capture panel holds the state badge, mascot, countdown, progress, command/interval/channel summary, and Start/Stop controls. A session activity panel sits below the capture panel, with a short instructional footer across the bottom.

Use 24px outer rhythm, 16px panel gutters, and 8px spacing within controls. Target the supplied 1489×1056 reference proportions; keep the window resizable with a practical minimum near 1080×760. At narrower sizes, preserve both task regions and prioritize the countdown and actions over decoration.

## Elevation & Depth

Depth is conveyed by nested violet tones, the supplied pixel-art assets, and stepped gold outlines rather than diffuse shadows. Avoid glass effects and soft blurred card elevation; panel boundaries should feel like crafted game-console frames.

## Shapes

Panels and controls use square corners with small stepped pixel cuts at frame corners. Borders are deliberate, high-contrast gold or muted violet. Inputs remain conventional, rectangular, and clearly focused; decorative framing never reduces editability.

## Components

### Header
- Use the supplied `INTERFACETOPO.png` crop as the branded top banner, with the night wallpaper visible at its sides.
- Keep the header height bounded; it introduces Capturix identity but does not displace operational controls.

### Connection Panel
- Holds channel slug, Client ID, masked Client Secret, **Salvar e verificar canal**, and **Autorizar na Kick**.
- Show lookup progress, channel-found status, authorization status, and errors in text as well as color.
- Keep Start disabled until the channel resolves and OAuth authorization is available.

### Capture Panel
- Use `icone painel captura.png` in place of the bot logo beside the capture timer.
- State badge reads **BOT PARADO**/ready until explicit Start; active state is green.
- Countdown is the most prominent live value. Progress fills from zero to 5:05 after each successful send.
- **Iniciar** sends immediately; **Parar** interrupts the scheduled cycle.
- Command, interval, and resolved channel stay visible as compact facts.

### Recent Activity
- Show the latest five current-session events: bot started/stopped, command sent, retry, or error.
- Discard the list when the app closes.

## Do's and Don'ts

### Do:
- **Do** preserve the user-approved two-column composition and retro-RPG violet/gold world.
- **Do** keep the first-run sequence visible: verify channel, authorize Kick, then start.
- **Do** preserve text labels, keyboard navigation, and visible focus on every input/action.
- **Do** make the initial state stopped and say the first capture sends immediately on Start.

### Don't:
- **Don't** use `INTERFACE.png` as a flattened static background with fake controls.
- **Don't** start sending on app launch or persist the recent-activity list.
- **Don't** let ornament, glow, or pixel styling obscure labels, status, countdown, or Stop.
- **Don't** add unsupplied gameplay functions or imply the app controls the stream itself.
