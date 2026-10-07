---
version: 1
slug: "src-botcapturar-ui-py"
primary_target: "src/botcapturar/ui.py"
related_targets: ["src/botcapturar/controller.py","src/botcapturar/scheduler.py"]
---

# BotCapturar Main Window

**Mode:** Operate. The user is configuring a local automation and monitoring whether it is sending the fixed Kick chat command.

**Audience and job:** A Kick moderator or other user authorized to chat. They must create a Kick App, verify a channel from its slug, authorize `chat:write`, start the automation, and stop it when needed.

**Success:** A first-time user can follow the panel sequence without opening developer documentation mid-flow; an active user can recognize the state and next-send countdown at a glance.

**First viewport:** The supplied Capturix pixel-art top banner over the supplied night-sky wallpaper, followed by a two-column console. Left: Kick channel/app configuration, save-and-verify, authorization, and text status. Right: active/stopped badge, the supplied capture-item icon, large 5:05 countdown, progress bar, fixed command/channel summary, and Start/Stop. Recent activity (last five session events) occupies a lower panel.

**Signature interaction:** Start immediately sends `$capturar`, switches the status to active, fills a 5:05 countdown/progress cycle, and logs the send. Stop cancels the next scheduled send. The app always opens stopped; recent activity is memory-only and clears on close.

**Constraints:** Match `INTERFACE.png`'s Capturix retro-RPG pixel-art world with `novalogobot.png` and `novalogonome.png`. Keep native editable inputs, keyboard focus, and text status accessible. No client secret is shown after saving, persisted activity log, auto-start, or invented stream/game controls.
