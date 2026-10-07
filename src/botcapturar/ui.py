"""Tkinter interface for BotCapturar."""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import ttk

from botcapturar.controller import ApplicationController, ConfigurationError
from botcapturar.credentials import CredentialStore, CredentialStoreError
from botcapturar.oauth import OAuthError
from botcapturar.resources import resource_path
from botcapturar.scheduler import SchedulerStatus


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
        if controller is None:
            if credential_store is None:
                raise ValueError("credential_store or controller is required")
            controller = ApplicationController(
                credential_store,
                on_status=self._handle_scheduler_status,
            )
        self.controller = controller

        root.title("BotCapturar — Kick")
        root.iconbitmap(str(resource_path("assets/BotCapturar.ico")))
        root.minsize(500, 370)
        root.columnconfigure(1, weight=1)

        self.status_var = tk.StringVar(master=root, value="Configure sua aplicação Kick para começar.")
        self.next_send_var = tk.StringVar(master=root, value="Próximo envio: —")

        self._create_widgets()
        self._load_saved_settings()
        self.refresh_controls()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._countdown_after_id = root.after(1000, self._update_countdown)

    def _create_widgets(self) -> None:
        padding = {"padx": 12, "pady": 5}
        ttk.Label(self.root, text="Nome do canal na Kick (slug, ex.: jukes)").grid(
            row=0, column=0, sticky="w", **padding
        )
        self.channel_entry = ttk.Entry(self.root)
        self.channel_entry.grid(row=0, column=1, sticky="ew", **padding)

        ttk.Label(self.root, text="Kick App Client ID").grid(row=1, column=0, sticky="w", **padding)
        self.client_id_entry = ttk.Entry(self.root)
        self.client_id_entry.grid(row=1, column=1, sticky="ew", **padding)

        ttk.Label(self.root, text="Kick App Client Secret").grid(row=2, column=0, sticky="w", **padding)
        self.client_secret_entry = ttk.Entry(self.root, show="*")
        self.client_secret_entry.grid(row=2, column=1, sticky="ew", **padding)

        self.save_button = ttk.Button(self.root, text="Salvar e verificar canal", command=self._save_settings)
        self.save_button.grid(row=3, column=0, sticky="ew", **padding)
        self.authorize_button = ttk.Button(self.root, text="Autorizar na Kick", command=self._authorize)
        self.authorize_button.grid(row=3, column=1, sticky="ew", **padding)

        self.start_button = ttk.Button(self.root, text="Iniciar", command=self._start)
        self.start_button.grid(row=4, column=0, sticky="ew", **padding)
        self.stop_button = ttk.Button(self.root, text="Parar", command=self._stop)
        self.stop_button.grid(row=4, column=1, sticky="ew", **padding)

        ttk.Separator(self.root).grid(row=5, column=0, columnspan=2, sticky="ew", padx=12, pady=10)
        ttk.Label(self.root, textvariable=self.status_var, wraplength=420).grid(
            row=6, column=0, columnspan=2, sticky="w", padx=12, pady=4
        )
        ttk.Label(self.root, textvariable=self.next_send_var).grid(
            row=7, column=0, columnspan=2, sticky="w", padx=12, pady=4
        )
        ttk.Label(
            self.root,
            text="Envia $capturar imediatamente e repete a cada 5:05 enquanto estiver ligado.",
            wraplength=420,
        ).grid(row=8, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6))

    def _load_saved_settings(self) -> None:
        client_id, _client_secret, channel_slug = self.controller.load_settings()
        self.client_id_entry.insert(0, client_id)
        self.channel_entry.insert(0, channel_slug)

    def _save_settings(self) -> None:
        try:
            self.controller.save_settings(
                self.client_id_entry.get(),
                self.client_secret_entry.get(),
                self.channel_entry.get(),
            )
        except (ConfigurationError, CredentialStoreError, ValueError) as error:
            self.status_var.set(str(error))
            return
        self.client_secret_entry.delete(0, tk.END)
        self._resolving_channel = True
        self.save_button.configure(state="disabled")
        self.status_var.set("Consultando esse canal na Kick…")
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
            self.status_var.set(f"Não foi possível localizar o canal: {error}")
        else:
            self.status_var.set(f"Canal encontrado: {slug}.")
        self.refresh_controls()

    def _authorize(self) -> None:
        if self._resolving_channel:
            self.status_var.set("Aguarde a verificação do canal antes de autorizar.")
            return
        if not self.controller.has_configuration():
            self.status_var.set("Salve e verifique o nome do canal antes de autorizar.")
            return
        self.authorize_button.configure(state="disabled")
        self.status_var.set("Aguardando autorização da Kick no navegador do sistema…")

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
            self.status_var.set(f"Autorização não concluída: {error}")
        else:
            self.status_var.set("Conta autorizada para usar o chat da Kick.")
        self.authorize_button.configure(state="normal")
        self.refresh_controls()

    def _start(self) -> None:
        try:
            self.controller.start()
        except (ConfigurationError, CredentialStoreError, OAuthError, ValueError) as error:
            self.status_var.set(str(error))
        self.refresh_controls()

    def _stop(self) -> None:
        self.controller.stop()
        self.status_var.set("Envios parados.")
        self.next_send_var.set("Próximo envio: —")
        self.refresh_controls()

    def refresh_controls(self) -> None:
        authorized = self.controller.can_start()
        running = self.controller.is_running
        self.save_button.configure(state="disabled" if self._resolving_channel else "normal")
        self.start_button.configure(state="normal" if authorized and not running else "disabled")
        self.stop_button.configure(state="normal" if running else "disabled")
        can_authorize = self.controller.has_configuration() and not self._resolving_channel
        self.authorize_button.configure(state="normal" if can_authorize else "disabled")

    def _handle_scheduler_status(self, status: SchedulerStatus) -> None:
        self._post_to_ui(lambda: self._render_scheduler_status(status))

    def _render_scheduler_status(self, status: SchedulerStatus) -> None:
        self.status_var.set(status.message)
        if status.next_send_at is None:
            self.next_send_var.set("Próximo envio: —")
        else:
            self.next_send_var.set("Próximo envio: calculando…")
        self.refresh_controls()

    def _update_countdown(self) -> None:
        if self._closed:
            return
        next_send_at = self.controller.next_send_at
        if next_send_at is not None:
            remaining = max(0, int(next_send_at - time.monotonic()))
            minutes, seconds = divmod(remaining, 60)
            self.next_send_var.set(f"Próximo envio em: {minutes}:{seconds:02d}")
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
