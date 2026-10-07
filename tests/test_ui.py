from __future__ import annotations

from types import SimpleNamespace

import pytest

import botcapturar.ui as ui
from botcapturar.scheduler import SchedulerState, SchedulerStatus


class FakeStringVar:
    def __init__(self, *, master=None, value="") -> None:
        self.value = value

    def set(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


class FakeWidget:
    def __init__(self, master=None, **kwargs) -> None:
        self.master = master
        self.kwargs = kwargs
        self.command = kwargs.get("command")
        self.options = {"state": "normal", "show": kwargs.get("show", "")}
        self.value = ""

    def grid(self, **kwargs) -> None:
        return None

    def configure(self, **kwargs) -> None:
        self.options.update(kwargs)

    def cget(self, key: str):
        return self.options.get(key, self.kwargs.get(key, ""))

    def __getitem__(self, key: str):
        return self.options.get(key, "")

    def delete(self, start, end=None) -> None:
        self.value = ""

    def insert(self, index, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def invoke(self) -> None:
        if self.options.get("state") != "disabled" and self.command:
            self.command()


class FakeRoot:
    def __init__(self) -> None:
        self.pending = []
        self.destroyed = False
        self.icons = []

    def title(self, title: str) -> None:
        self.window_title = title

    def iconbitmap(self, path: str) -> None:
        self.icons.append(path)

    def minsize(self, width: int, height: int) -> None:
        self.minimum_size = (width, height)

    def columnconfigure(self, column: int, **kwargs) -> None:
        return None

    def protocol(self, name: str, callback) -> None:
        self.close_callback = callback

    def after(self, delay: int, callback):
        self.pending.append(callback)
        return len(self.pending)

    def after_cancel(self, callback_id) -> None:
        return None

    def destroy(self) -> None:
        self.destroyed = True

    def run_pending(self) -> None:
        pending, self.pending = self.pending, []
        for callback in pending:
            callback()


class FakeController:
    def __init__(self) -> None:
        self.settings = ("client-id", "stored-secret", "jukes")
        self.ready = False
        self.resolved = False
        self.running = False
        self.saved = []
        self.resolve_calls = 0
        self.authorize_calls = 0
        self.start_calls = 0
        self.stop_calls = 0
        self.close_calls = 0

    def load_settings(self):
        return self.settings

    def has_configuration(self) -> bool:
        return self.resolved and bool(self.settings[0] and self.settings[1] and self.settings[2])

    def can_start(self) -> bool:
        return self.ready

    def save_settings(self, client_id, client_secret, channel_slug):
        self.saved.append((client_id, client_secret, channel_slug))
        self.settings = (client_id, client_secret, channel_slug)
        self.resolved = False

    def resolve_channel(self):
        self.resolve_calls += 1
        self.resolved = True
        return SimpleNamespace(slug=self.settings[2], broadcaster_user_id=54321)

    def authorize(self):
        self.authorize_calls += 1

    def start(self):
        self.start_calls += 1
        self.running = True
        return True

    def stop(self):
        self.stop_calls += 1
        self.running = False

    def close(self):
        self.close_calls += 1

    @property
    def is_running(self):
        return self.running

    @property
    def next_send_at(self):
        return None


@pytest.fixture
def make_window(monkeypatch):
    monkeypatch.setattr(ui.tk, "StringVar", FakeStringVar)
    monkeypatch.setattr(ui.tk, "END", "end")
    monkeypatch.setattr(ui.tk, "TclError", RuntimeError)
    monkeypatch.setattr(
        ui.ttk,
        "Label",
        FakeWidget,
    )
    monkeypatch.setattr(ui.ttk, "Entry", FakeWidget)
    monkeypatch.setattr(ui.ttk, "Button", FakeWidget)
    monkeypatch.setattr(ui.ttk, "Separator", FakeWidget)
    roots = []

    def create(controller=None):
        root = FakeRoot()
        roots.append(root)
        fake_controller = controller or FakeController()
        window = ui.BotCapturarWindow(root, controller=fake_controller)
        return root, window, fake_controller

    return create


def test_start_is_disabled_until_oauth_is_ready(make_window):
    root, window, controller = make_window()

    assert controller.start_calls == 0
    assert window.start_button["state"] == "disabled"

    controller.ready = True
    controller.resolved = True
    window.refresh_controls()

    assert window.start_button["state"] == "normal"
    assert window.stop_button["state"] == "disabled"


def test_start_and_stop_buttons_delegate_to_controller(make_window):
    root, window, controller = make_window()
    controller.ready = True
    controller.resolved = True
    window.refresh_controls()

    window.start_button.invoke()
    assert controller.start_calls == 1
    assert window.stop_button["state"] == "normal"

    window.stop_button.invoke()
    assert controller.stop_calls == 1


def test_client_secret_is_masked_and_cleared_after_secure_save(make_window):
    root, window, controller = make_window()
    window.client_id_entry.delete(0, "end")
    window.client_id_entry.insert(0, "new-client-id")
    window.client_secret_entry.insert(0, "new-client-secret")
    window.channel_entry.delete(0, "end")
    window.channel_entry.insert(0, "jukes")

    assert window.client_secret_entry.cget("show") == "*"
    window.save_button.invoke()
    window._resolve_thread.join(timeout=1)
    root.run_pending()

    assert controller.saved == [("new-client-id", "new-client-secret", "jukes")]
    assert window.client_secret_entry.get() == ""


def test_authorize_button_runs_authorization_action_in_background(make_window):
    root, window, controller = make_window()
    controller.resolved = True
    window.refresh_controls()
    window.authorize_button.invoke()
    window._auth_thread.join(timeout=1)
    root.run_pending()

    assert controller.authorize_calls == 1


def test_window_close_closes_controller_and_root(make_window):
    root, window, controller = make_window()

    window.on_close()

    assert controller.close_calls == 1
    assert root.destroyed is True


def test_window_uses_bot_icon_from_project_assets(make_window):
    root, window, controller = make_window()

    assert len(root.icons) == 1
    assert root.icons[0].replace("\\", "/").endswith("assets/BotCapturar.ico")


def test_scheduler_status_updates_status_and_controls(make_window):
    root, window, controller = make_window()
    status = SchedulerStatus(SchedulerState.WAITING, "Message sent", next_send_at=1000)

    window._handle_scheduler_status(status)
    root.run_pending()

    assert window.status_var.get() == "Message sent"
    assert window.next_send_var.get() == "Próximo envio: calculando…"


def test_saving_slug_resolves_channel_asynchronously_and_does_not_ask_for_numeric_id(make_window):
    root, window, controller = make_window()
    window.client_id_entry.delete(0, "end")
    window.client_id_entry.insert(0, "new-client-id")
    window.client_secret_entry.insert(0, "new-client-secret")
    window.channel_entry.delete(0, "end")
    window.channel_entry.insert(0, "jukes")

    window.save_button.invoke()
    window._resolve_thread.join(timeout=1)
    root.run_pending()

    assert controller.saved == [("new-client-id", "new-client-secret", "jukes")]
    assert controller.resolve_calls == 1
    assert window.status_var.get() == "Canal encontrado: jukes."
    assert window.client_secret_entry.get() == ""
    assert window.start_button["state"] == "disabled"
