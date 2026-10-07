from __future__ import annotations

from types import SimpleNamespace

import pytest

import botcapturar.ui as ui
from botcapturar.ui import progress_fraction
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
        self.calls = []

    def grid(self, **kwargs) -> None:
        return None

    def pack(self, **kwargs) -> None:
        return None

    def place(self, **kwargs) -> None:
        return None

    def columnconfigure(self, column, **kwargs) -> None:
        return None

    def rowconfigure(self, row, **kwargs) -> None:
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

    def bind(self, event, callback) -> None:
        return None

    def create_window(self, *args, **kwargs):
        self.calls.append(("window", args, kwargs))
        return 1

    def create_line(self, *args, **kwargs):
        self.calls.append(("line", args, kwargs))
        return 1

    def create_rectangle(self, *args, **kwargs):
        self.calls.append(("rectangle", args, kwargs))
        return 1

    def create_text(self, *args, **kwargs):
        self.calls.append(("text", args, kwargs))
        return 1

    def create_polygon(self, *args, **kwargs):
        self.calls.append(("polygon", args, kwargs))
        return 1

    def create_image(self, *args, **kwargs):
        self.calls.append(("image", args, kwargs))
        return 1

    def coords(self, *args) -> None:
        return None

    def itemconfigure(self, *args, **kwargs) -> None:
        return None

    def subsample(self, x, y=None):
        return self


class FakeStyle:
    def __init__(self, root=None) -> None:
        self.configured = {}

    def theme_use(self, theme) -> None:
        return None

    def configure(self, name, **kwargs) -> None:
        self.configured[name] = kwargs

    def map(self, name, **kwargs) -> None:
        return None


class FakeRoot:
    def __init__(self) -> None:
        self.pending = []
        self.destroyed = False
        self.icons = []
        self.photo_files = []

    def title(self, title: str) -> None:
        self.window_title = title

    def iconbitmap(self, path: str) -> None:
        self.icons.append(path)

    def minsize(self, width: int, height: int) -> None:
        self.minimum_size = (width, height)

    def geometry(self, value: str) -> None:
        self.geometry_value = value

    def configure(self, **kwargs) -> None:
        self.options = kwargs

    def resizable(self, width: bool, height: bool) -> None:
        self.resizable_value = (width, height)

    def geometry(self, geometry: str) -> None:
        self.geometry_value = geometry

    def configure(self, **kwargs) -> None:
        self.options = kwargs

    def resizable(self, width: bool, height: bool) -> None:
        self.resizable_value = (width, height)

    def columnconfigure(self, column: int, **kwargs) -> None:
        return None

    def rowconfigure(self, row: int, **kwargs) -> None:
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

    def photo_image(master=None, **kwargs):
        if master is not None and hasattr(master, "photo_files"):
            master.photo_files.append(kwargs.get("file"))
        return FakeWidget(master, **kwargs)

    monkeypatch.setattr(ui.tk, "PhotoImage", photo_image)
    monkeypatch.setattr(ui.tk, "Frame", FakeWidget)
    monkeypatch.setattr(ui.tk, "Canvas", FakeWidget)
    monkeypatch.setattr(ui.tk, "END", "end")
    monkeypatch.setattr(ui.tk, "TclError", RuntimeError)
    monkeypatch.setattr(ui.ttk, "Style", FakeStyle)
    monkeypatch.setattr(ui.tk, "Label", FakeWidget)
    monkeypatch.setattr(ui.ttk, "Frame", FakeWidget)
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
    assert window.next_send_var.get() == "--:--"
    assert "Comando enviado" in window.activity_var.get()


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


def test_window_uses_capturix_control_room_layout_and_starts_stopped(make_window):
    root, window, controller = make_window()

    assert root.window_title == "BotCapturar — Capturix"
    assert window.connection_panel is not None
    assert window.capture_panel is not None
    assert window.activity_panel is not None
    assert window.bot_state_var.get() == "BOT PARADO"
    assert window.activity_log.entries == ()
    assert controller.start_calls == 0
    assert window.activity_var.get() == "Nenhuma atividade nesta sessão."
    assert {path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for path in root.photo_files} >= {
        "CapturixCapture.png",
        "INTERFACEWALLPAPER.png",
        "CapturixTop.png",
    }


def test_authorized_launch_stays_stopped_and_explains_start_action(make_window):
    controller = FakeController()
    controller.resolved = True
    controller.ready = True

    root, window, _ = make_window(controller)

    assert window.bot_state_var.get() == "BOT PARADO"
    assert window.status_var.get() == "Conta autorizada. Clique em Iniciar."
    assert window.start_button["state"] == "normal"
    assert window.stop_button["state"] == "disabled"


def test_capture_panel_reserves_more_height_than_recent_activity(make_window):
    root, window, controller = make_window()

    assert int(window.capture_panel.canvas.cget("height")) >= 430
    assert int(window.activity_panel.canvas.cget("height")) <= 190


def test_countdown_uses_large_display_type(make_window):
    root, window, controller = make_window()

    assert window._styles.configured["Timer.Panel.TLabel"]["font"] == ("Consolas", 44, "bold")


def test_capture_panel_uses_new_item_icon_not_application_logo(make_window):
    root, window, controller = make_window()

    image = window.capture_mascot_label.cget("image")

    assert image.kwargs["file"].replace("\\", "/").endswith("assets/CapturixCapture.png")


def test_header_uses_supplied_top_banner_and_wallpaper_assets(make_window):
    root, window, controller = make_window()

    window.header_canvas.calls.clear()
    window._draw_header_scene(SimpleNamespace(width=1400, height=180))

    kinds = [call[0] for call in window.header_canvas.calls]
    assert "image" in kinds
    header_image_calls = [call for call in window.header_canvas.calls if call[0] == "image"]
    assert header_image_calls[0][2]["image"].kwargs["file"].replace("\\", "/").endswith("assets/CapturixTop.png")
    loaded_paths = {path.replace("\\", "/") for path in root.photo_files}
    assert any(path.endswith("assets/INTERFACEWALLPAPER.png") for path in loaded_paths)


def test_wallpaper_canvas_uses_wallpaper_asset_centered(make_window):
    root, window, controller = make_window()

    window.background_canvas.calls.clear()
    window._draw_wallpaper(SimpleNamespace(width=1489, height=1000))

    image_call = next(call for call in window.background_canvas.calls if call[0] == "image")
    assert image_call[2]["image"].kwargs["file"].replace("\\", "/").endswith("assets/INTERFACEWALLPAPER.png")
    assert image_call[1] == (-24, -12)


def test_countdown_progress_fraction_tracks_elapsed_time_and_clamps():
    assert progress_fraction(1305, 1000, 305) == 0.0
    assert progress_fraction(1152.5, 1000, 305) == 0.5
    assert progress_fraction(995, 1000, 305) == 1.0
    assert progress_fraction(None, 1000, 305) == 0.0
