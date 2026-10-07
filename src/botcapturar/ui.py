"""Capturix-themed Tkinter control room for BotCapturar.

THESIS: Make the recurring Kick command feel like a clear Capturix control room, not a generic settings dialog.
OWN-WORLD: Violet pixel-art surfaces, stepped gold frames, cream labels, green active/success, and crimson Stop.
STORY: Verify the channel, authorize Kick, start one immediate capture, then follow the timer and session events until Stop.
FIRST VIEWPORT: Brand header; left connection panel; right capture dashboard with mascot, countdown, progress, facts, and actions; recent activity below.
FORM: Functional Tkinter fields and controls framed with Canvas pixel details; preserve keyboard focus and no-autostart behavior.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import ttk

from botcapturar.activity import SessionActivityLog
from botcapturar.controller import ApplicationController, ConfigurationError
from botcapturar.credentials import CredentialStore, CredentialStoreError
from botcapturar.oauth import OAuthError
from botcapturar.pixel_widgets import PixelPanel, SegmentedProgressBar
from botcapturar.resources import resource_path
from botcapturar.scheduler import SchedulerState, SchedulerStatus
from botcapturar.theme import COLORS, FONTS, SPACING


def progress_fraction(
    next_send_at: float | None,
    now: float,
    interval_seconds: float = 305,
) -> float:
    """Return elapsed progress for the current fixed send interval."""
    if next_send_at is None or interval_seconds <= 0:
        return 0.0
    remaining = min(interval_seconds, max(0.0, next_send_at - now))
    return (interval_seconds - remaining) / interval_seconds


class BotCapturarWindow:
    def __init__(
        self,
        root: tk.Tk,
        *,
        credential_store: CredentialStore | None = None,
        controller: ApplicationController | None = None,
    ) -> None:
        self.root = root
        self._closed = False
        self._auth_thread: threading.Thread | None = None
        self._resolve_thread: threading.Thread | None = None
        self._resolving_channel = False
        self.activity_log = SessionActivityLog(max_entries=5)
        self._wordmark_image = None
        self._activity_widgets: list[tk.Widget] = []

        if controller is None:
            if credential_store is None:
                raise ValueError("credential_store or controller is required")
            controller = ApplicationController(
                credential_store,
                on_status=self._handle_scheduler_status,
            )
        self.controller = controller

        root.title("BotCapturar — Capturix")
        root.iconbitmap(str(resource_path("assets/BotCapturar.ico")))
        root.geometry("1489x1000")
        root.minsize(1180, 900)
        root.configure(background=COLORS["background"])
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        self.status_var = tk.StringVar(master=root, value="Configure a Kick App para começar.")
        self.next_send_var = tk.StringVar(master=root, value="--:--")
        self.bot_state_var = tk.StringVar(master=root, value="BOT PARADO")
        self.channel_value_var = tk.StringVar(master=root, value="—")
        self.activity_var = tk.StringVar(master=root, value="Nenhuma atividade nesta sessão.")

        self._configure_styles()
        self._load_brand_images()
        self._create_background()
        self._create_widgets()
        self._load_saved_settings()
        self.refresh_controls()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._countdown_after_id = root.after(1000, self._update_countdown)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        self._styles = style
        style.theme_use("clam")
        style.configure("TFrame", background=COLORS["background"])
        style.configure(
            "Panel.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["cream"],
            font=FONTS["body"],
        )
        style.configure(
            "Muted.Panel.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=FONTS["body"],
        )
        style.configure(
            "Label.Panel.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["cream"],
            font=FONTS["label"],
        )
        style.configure(
            "Timer.Panel.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["cream"],
            font=FONTS["timer"],
        )
        style.configure(
            "Brand.TLabel",
            background=COLORS["background"],
            foreground=COLORS["gold"],
            font=FONTS["display"],
        )
        style.configure(
            "Connection.TEntry",
            fieldbackground=COLORS["inset"],
            foreground=COLORS["cream"],
            bordercolor=COLORS["gold_muted"],
            padding=(10, 9),
            font=FONTS["body"],
        )
        style.map(
            "Connection.TEntry",
            fieldbackground=[("focus", COLORS["panel"])],
            bordercolor=[("focus", COLORS["gold"])],
        )
        style.configure(
            "Gold.TButton",
            background=COLORS["gold"],
            foreground=COLORS["background"],
            font=FONTS["label"],
            padding=(12, 10),
            borderwidth=0,
        )
        style.map(
            "Gold.TButton",
            background=[("active", "#FFD978"), ("disabled", COLORS["gold_muted"])],
            foreground=[("disabled", COLORS["panel"])],
        )
        style.configure(
            "Purple.TButton",
            background=COLORS["purple"],
            foreground=COLORS["cream"],
            font=FONTS["label"],
            padding=(12, 10),
            borderwidth=0,
        )
        style.map(
            "Purple.TButton",
            background=[("active", "#BC75F3"), ("disabled", COLORS["gold_muted"])],
        )
        style.configure(
            "Start.TButton",
            background=COLORS["success"],
            foreground=COLORS["background"],
            font=FONTS["heading"],
            padding=(18, 13),
            borderwidth=0,
        )
        style.map(
            "Start.TButton",
            background=[("active", "#9BFF73"), ("disabled", "#403A4C")],
            foreground=[("disabled", COLORS["muted"])],
        )
        style.configure(
            "Stop.TButton",
            background=COLORS["danger"],
            foreground=COLORS["cream"],
            font=FONTS["heading"],
            padding=(18, 13),
            borderwidth=0,
        )
        style.map("Stop.TButton", background=[("active", "#BD2857"), ("disabled", "#392433")])
        style.configure(
            "Footer.TLabel",
            background=COLORS["background"],
            foreground=COLORS["cream"],
            font=FONTS["body"],
        )

    def _load_brand_images(self) -> None:
        capture_icon = tk.PhotoImage(
            master=self.root,
            file=str(resource_path("assets/CapturixCapture.png")),
        )
        self._capture_icon = capture_icon.subsample(6, 6)
        self._wallpaper_image = tk.PhotoImage(
            master=self.root,
            file=str(resource_path("assets/INTERFACEWALLPAPER.png")),
        )
        self._top_banner_image = tk.PhotoImage(
            master=self.root,
            file=str(resource_path("assets/CapturixTop.png")),
        )

    def _create_background(self) -> None:
        self.background_canvas = tk.Canvas(
            self.root,
            background=COLORS["background"],
            highlightthickness=0,
            borderwidth=0,
        )
        self.background_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.background_canvas.bind("<Configure>", self._draw_wallpaper)

    def _draw_wallpaper(self, event) -> None:
        width = max(1, int(event.width))
        height = max(1, int(event.height))
        x = (width - 1536) // 2
        y = (height - 1024) // 2
        self.background_canvas.delete("wallpaper")
        self.background_canvas.create_image(
            x,
            y,
            anchor="nw",
            image=self._wallpaper_image,
            tags="wallpaper",
        )

    def _create_widgets(self) -> None:
        self._create_header()
        self._create_workspace()
        self._create_footer()

    def _create_header(self) -> None:
        self.header_canvas = tk.Canvas(
            self.root,
            background=COLORS["background"],
            height=242,
            highlightthickness=0,
            borderwidth=0,
        )
        self.header_canvas.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=SPACING["lg"],
            pady=(SPACING["md"], SPACING["sm"]),
        )
        self.header_canvas.bind("<Configure>", self._draw_header_scene)

    def _draw_header_scene(self, event) -> None:
        canvas = self.header_canvas
        width = max(1, int(event.width))
        height = max(1, int(event.height))
        canvas.delete("all")
        canvas.create_image(
            (width - 1086) // 2,
            (height - 242) // 2,
            anchor="nw",
            image=self._top_banner_image,
        )

    def _create_workspace(self) -> None:
        workspace = tk.Frame(self.root, background=COLORS["background"])
        workspace.grid(row=1, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["sm"])
        workspace.columnconfigure(0, weight=0, minsize=390)
        workspace.columnconfigure(1, weight=1, minsize=620)
        workspace.rowconfigure(0, weight=4, minsize=440)
        workspace.rowconfigure(1, weight=1, minsize=180)

        self.connection_panel = PixelPanel(workspace, title="Conexão com a Kick", canvas_height=650)
        self.connection_panel.widget.grid(
            row=0,
            column=0,
            rowspan=2,
            sticky="nsew",
            padx=(0, SPACING["md"]),
        )
        self.capture_panel = PixelPanel(workspace, title="Painel de captura", canvas_height=440)
        self.capture_panel.widget.grid(row=0, column=1, sticky="nsew", pady=(0, SPACING["md"]))
        self.activity_panel = PixelPanel(workspace, title="Atividade recente", canvas_height=180)
        self.activity_panel.widget.grid(row=1, column=1, sticky="nsew")

        self._create_connection_controls()
        self._create_capture_controls()
        self._create_activity_view()

    def _create_connection_controls(self) -> None:
        body = self.connection_panel.body
        body.columnconfigure(0, weight=1)

        ttk.Label(body, text="Nome do canal na Kick (slug)", style="Label.Panel.TLabel").grid(
            row=0, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["md"], SPACING["xs"])
        )
        self.channel_entry = ttk.Entry(body, style="Connection.TEntry")
        self.channel_entry.grid(row=1, column=0, sticky="ew", padx=SPACING["md"])
        ttk.Label(
            body,
            text="Para kick.com/jukes, digite jukes",
            style="Muted.Panel.TLabel",
        ).grid(row=2, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["xs"], SPACING["sm"]))

        ttk.Label(body, text="Kick App Client ID", style="Label.Panel.TLabel").grid(
            row=3, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["sm"], SPACING["xs"])
        )
        self.client_id_entry = ttk.Entry(body, style="Connection.TEntry")
        self.client_id_entry.grid(row=4, column=0, sticky="ew", padx=SPACING["md"])

        ttk.Label(body, text="Kick App Client Secret", style="Label.Panel.TLabel").grid(
            row=5, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["sm"], SPACING["xs"])
        )
        self.client_secret_entry = ttk.Entry(body, style="Connection.TEntry", show="*")
        self.client_secret_entry.grid(row=6, column=0, sticky="ew", padx=SPACING["md"])
        ttk.Label(
            body,
            text="Credenciais protegidas no Windows",
            style="Muted.Panel.TLabel",
        ).grid(row=7, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["xs"], SPACING["sm"]))

        self.save_button = ttk.Button(
            body,
            text="Salvar e verificar canal",
            style="Gold.TButton",
            command=self._save_settings,
        )
        self.save_button.grid(row=8, column=0, sticky="ew", padx=SPACING["md"], pady=(SPACING["sm"], SPACING["xs"]))
        self.authorize_button = ttk.Button(
            body,
            text="Autorizar na Kick",
            style="Purple.TButton",
            command=self._authorize,
        )
        self.authorize_button.grid(row=9, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["xs"])

        self.connection_status_label = tk.Label(
            body,
            textvariable=self.status_var,
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=FONTS["body"],
            justify="left",
            wraplength=340,
            anchor="w",
        )
        self.connection_status_label.grid(
            row=10,
            column=0,
            sticky="ew",
            padx=SPACING["md"],
            pady=(SPACING["md"], SPACING["md"]),
        )

    def _create_capture_controls(self) -> None:
        body = self.capture_panel.body
        body.columnconfigure(0, weight=0, minsize=230)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        self.state_badge = tk.Label(
            body,
            textvariable=self.bot_state_var,
            background=COLORS["inset"],
            foreground=COLORS["muted"],
            font=FONTS["label"],
            padx=12,
            pady=6,
        )
        self.state_badge.grid(row=0, column=0, columnspan=2, sticky="e", padx=SPACING["md"], pady=(SPACING["sm"], 0))

        self.capture_mascot_label = tk.Label(
            body,
            image=self._capture_icon,
            background=COLORS["panel"],
            borderwidth=0,
        )
        self.capture_mascot_label.grid(
            row=1,
            column=0,
            rowspan=5,
            sticky="nsew",
            padx=SPACING["md"],
            pady=SPACING["sm"],
        )

        ttk.Label(
            body,
            text="Próxima captura em",
            style="Panel.TLabel",
            anchor="center",
        ).grid(row=1, column=1, sticky="ew", padx=SPACING["md"], pady=(SPACING["sm"], 0))
        self.countdown_label = ttk.Label(
            body,
            textvariable=self.next_send_var,
            style="Timer.Panel.TLabel",
            anchor="center",
        )
        self.countdown_label.grid(row=2, column=1, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["sm"]))

        self.progress_bar = SegmentedProgressBar(body, segments=36, width=640, height=28)
        self.progress_bar.canvas.grid(row=3, column=1, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))

        facts = tk.Frame(body, background=COLORS["inset"], padx=SPACING["md"], pady=SPACING["sm"])
        facts.grid(row=4, column=1, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        facts.columnconfigure(1, weight=1)
        for row, (name, value) in enumerate(
            (
                ("Comando", "$capturar"),
                ("Intervalo", "5 min 05 s"),
                ("Canal", None),
            )
        ):
            ttk.Label(facts, text=name, style="Muted.Panel.TLabel").grid(
                row=row, column=0, sticky="w", pady=SPACING["xs"]
            )
            if name == "Canal":
                value_label = ttk.Label(facts, textvariable=self.channel_value_var, style="Label.Panel.TLabel")
            else:
                value_label = ttk.Label(facts, text=value, style="Label.Panel.TLabel")
            value_label.grid(row=row, column=1, sticky="w", padx=(SPACING["lg"], 0), pady=SPACING["xs"])

        actions = tk.Frame(body, background=COLORS["panel"])
        actions.grid(row=5, column=1, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        self.start_button = ttk.Button(actions, text="▶  Iniciar", style="Start.TButton", command=self._start)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        self.stop_button = ttk.Button(actions, text="■  Parar", style="Stop.TButton", command=self._stop)
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(SPACING["sm"], 0))

    def _create_activity_view(self) -> None:
        body = self.activity_panel.body
        body.columnconfigure(0, weight=1)
        self.activity_label = ttk.Label(
            body,
            textvariable=self.activity_var,
            style="Panel.TLabel",
            anchor="nw",
            justify="left",
            wraplength=820,
        )
        self.activity_label.grid(row=0, column=0, sticky="nsew", padx=SPACING["md"], pady=SPACING["sm"])

    def _create_footer(self) -> None:
        footer = tk.Frame(self.root, background=COLORS["background"])
        footer.grid(row=2, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["md"]))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(2, weight=1)
        tk.Frame(footer, background=COLORS["gold_muted"], height=2).grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        ttk.Label(
            footer,
            text="A primeira captura é enviada ao iniciar.",
            style="Footer.TLabel",
        ).grid(row=0, column=1, sticky="ew", padx=SPACING["sm"])
        tk.Frame(footer, background=COLORS["gold_muted"], height=2).grid(row=0, column=2, sticky="ew", padx=(SPACING["sm"], 0))

    def _load_saved_settings(self) -> None:
        client_id, _client_secret, channel_slug = self.controller.load_settings()
        self.client_id_entry.insert(0, client_id)
        self.channel_entry.insert(0, channel_slug)
        self.channel_value_var.set(channel_slug or "—")
        if self.controller.can_start():
            self._set_connection_status("Conta autorizada. Clique em Iniciar.", "success")
        elif self.controller.has_configuration():
            self._set_connection_status("Canal verificado. Clique em Autorizar na Kick.", "info")

    def _save_settings(self) -> None:
        try:
            self.controller.save_settings(
                self.client_id_entry.get(),
                self.client_secret_entry.get(),
                self.channel_entry.get(),
            )
        except (ConfigurationError, CredentialStoreError, ValueError) as error:
            self._set_connection_status(str(error), "error")
            return
        self.client_secret_entry.delete(0, tk.END)
        self._resolving_channel = True
        self.save_button.configure(state="disabled")
        self._set_connection_status("Consultando esse canal na Kick…", "info")
        self.refresh_controls()

        def resolve_in_background() -> None:
            try:
                channel = self.controller.resolve_channel()
            except Exception as error:
                self._post_to_ui(lambda: self._channel_resolution_finished(None, str(error)))
            else:
                self._post_to_ui(lambda: self._channel_resolution_finished(channel.slug, None))

        self._resolve_thread = threading.Thread(
            target=resolve_in_background,
            name="botcapturar-channel-lookup",
            daemon=True,
        )
        self._resolve_thread.start()

    def _channel_resolution_finished(self, slug: str | None, error: str | None) -> None:
        self._resolving_channel = False
        if error:
            message = f"Não foi possível localizar o canal: {error}"
            self._set_connection_status(message, "error")
            self._record_activity("Falha ao verificar o canal", "error")
        else:
            self.channel_value_var.set(slug or "—")
            self._set_connection_status(f"Canal encontrado: {slug}.", "success")
            self._record_activity(f"Canal verificado: {slug}", "success")
        self.refresh_controls()

    def _authorize(self) -> None:
        if self._resolving_channel:
            self._set_connection_status("Aguarde a verificação do canal antes de autorizar.", "warning")
            return
        if not self.controller.has_configuration():
            self._set_connection_status("Salve e verifique o nome do canal antes de autorizar.", "warning")
            return
        self.authorize_button.configure(state="disabled")
        self._set_connection_status("Aguardando autorização da Kick no navegador…", "info")
        self._record_activity("Autorização da Kick iniciada", "info")

        def authorize_in_background() -> None:
            try:
                self.controller.authorize()
            except Exception as error:
                self._post_to_ui(lambda: self._authorization_finished(str(error)))
            else:
                self._post_to_ui(lambda: self._authorization_finished(None))

        self._auth_thread = threading.Thread(
            target=authorize_in_background,
            name="botcapturar-oauth",
            daemon=True,
        )
        self._auth_thread.start()

    def _authorization_finished(self, error: str | None) -> None:
        if error:
            self._set_connection_status(f"Autorização não concluída: {error}", "error")
            self._record_activity("Autorização não concluída", "error")
        else:
            self._set_connection_status("Conta autorizada para usar o chat da Kick.", "success")
            self._record_activity("Conta autorizada", "success")
        self.authorize_button.configure(state="normal")
        self.refresh_controls()

    def _start(self) -> None:
        try:
            started = self.controller.start()
        except (ConfigurationError, CredentialStoreError, OAuthError, ValueError) as error:
            self._set_connection_status(str(error), "error")
            return
        if started:
            self._record_activity("Bot iniciado", "success")
            self._set_connection_status("Bot ativo. A primeira captura está sendo enviada.", "success")
        self.refresh_controls()

    def _stop(self) -> None:
        self.controller.stop()
        self._record_activity("Bot parado", "warning")
        self._set_connection_status("Envios parados.", "info")
        self.next_send_var.set("--:--")
        self.progress_bar.set_fraction(0)
        self.refresh_controls()

    def refresh_controls(self) -> None:
        authorized = self.controller.can_start()
        running = self.controller.is_running
        has_configuration = self.controller.has_configuration()
        self.save_button.configure(state="disabled" if self._resolving_channel else "normal")
        self.start_button.configure(state="normal" if authorized and not running else "disabled")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.authorize_button.configure(
            state="normal" if has_configuration and not self._resolving_channel else "disabled"
        )
        if running:
            self._set_bot_state("BOT ATIVO", COLORS["success"])
        elif authorized:
            self._set_bot_state("BOT PARADO", COLORS["gold"])
        else:
            self._set_bot_state("BOT PARADO", COLORS["muted"])

    def _set_bot_state(self, text: str, foreground: str) -> None:
        self.bot_state_var.set(text)
        self.state_badge.configure(foreground=foreground)

    def _set_connection_status(self, message: str, state: str) -> None:
        colors = {
            "success": COLORS["success"],
            "error": "#FF7891",
            "warning": COLORS["gold"],
            "info": COLORS["muted"],
        }
        self.status_var.set(message)
        self.connection_status_label.configure(foreground=colors.get(state, COLORS["muted"]))

    def _record_activity(self, message: str, state: str = "info") -> None:
        self.activity_log.add(message, state)
        self._render_activity()

    def _render_activity(self) -> None:
        if not self.activity_log.entries:
            self.activity_var.set("Nenhuma atividade nesta sessão.")
            return
        markers = {"success": "●", "error": "◆", "warning": "!", "info": "•"}
        self.activity_var.set(
            "\n".join(
                f"{markers.get(entry.state, '•')}  {entry.time_text}     {entry.message}"
                for entry in self.activity_log.entries
            )
        )

    def _handle_scheduler_status(self, status: SchedulerStatus) -> None:
        self._post_to_ui(lambda: self._render_scheduler_status(status))

    def _render_scheduler_status(self, status: SchedulerStatus) -> None:
        self._set_connection_status(status.message, "error" if status.state is SchedulerState.ERROR else "info")
        event_messages = {
            SchedulerState.SENDING: ("Enviando $capturar", "info"),
            SchedulerState.WAITING: ("Comando enviado", "success"),
            SchedulerState.RETRYING: ("Tentando enviar novamente", "warning"),
            SchedulerState.AUTH_REQUIRED: ("Autorização necessária", "error"),
            SchedulerState.ERROR: (status.message, "error"),
        }
        if status.state in event_messages:
            message, state = event_messages[status.state]
            self._record_activity(message, state)
        self._update_countdown()
        self.refresh_controls()

    def _update_countdown(self) -> None:
        if self._closed:
            return
        next_send_at = self.controller.next_send_at
        fraction = progress_fraction(next_send_at, time.monotonic(), 305)
        self.progress_bar.set_fraction(fraction)
        if next_send_at is None:
            self.next_send_var.set("--:--")
        else:
            remaining = max(0, int(next_send_at - time.monotonic()))
            minutes, seconds = divmod(remaining, 60)
            self.next_send_var.set(f"{minutes:02d}:{seconds:02d}")
        self._countdown_after_id = self.root.after(1000, self._update_countdown)

    def _post_to_ui(self, callback) -> None:
        if self._closed:
            return
        try:
            self.root.after(0, callback)
        except tk.TclError:
            pass

    def on_close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.controller.close()
        try:
            self.root.after_cancel(self._countdown_after_id)
        except tk.TclError:
            pass
        self.root.destroy()
