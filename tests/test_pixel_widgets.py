from __future__ import annotations

import botcapturar.pixel_widgets as pixel_widgets


class FakeWidget:
    def __init__(self, master=None, **kwargs) -> None:
        self.master = master
        self.kwargs = kwargs
        self.options = {}
        self.calls = []

    def pack(self, **kwargs) -> None:
        self.calls.append(("pack", kwargs))

    def grid(self, **kwargs) -> None:
        self.calls.append(("grid", kwargs))

    def bind(self, event, callback) -> None:
        self.calls.append(("bind", event))

    def create_window(self, *args, **kwargs):
        self.calls.append(("window", args, kwargs))
        return len(self.calls)

    def create_line(self, *args, **kwargs):
        self.calls.append(("line", args, kwargs))

    def create_rectangle(self, *args, **kwargs):
        self.calls.append(("rectangle", args, kwargs))

    def create_text(self, *args, **kwargs):
        self.calls.append(("text", args, kwargs))

    def coords(self, *args) -> None:
        self.calls.append(("coords", args))

    def itemconfigure(self, *args, **kwargs) -> None:
        self.calls.append(("itemconfigure", args, kwargs))

    def delete(self, tag) -> None:
        self.calls.append(("delete", tag))

    def configure(self, **kwargs) -> None:
        self.options.update(kwargs)


class FakeEvent:
    width = 400
    height = 240


def test_pixel_panel_exposes_body_and_draws_a_gold_frame(monkeypatch):
    monkeypatch.setattr(pixel_widgets.tk, "Frame", FakeWidget)
    monkeypatch.setattr(pixel_widgets.tk, "Canvas", FakeWidget)

    panel = pixel_widgets.PixelPanel(object(), title="Conexão com a Kick")

    panel.canvas.calls.clear()
    panel._redraw_frame(FakeEvent())

    assert panel.body is not None
    assert any(call[0] == "line" for call in panel.canvas.calls)
    assert any(call[0] == "text" and call[2].get("text") == "Conexão com a Kick" for call in panel.canvas.calls)


def test_segmented_progress_clamps_fraction_and_redraws(monkeypatch):
    monkeypatch.setattr(pixel_widgets.tk, "Canvas", FakeWidget)

    progress = pixel_widgets.SegmentedProgressBar(object(), segments=10)
    progress.set_fraction(0.5)
    assert progress.fraction == 0.5
    assert len([call for call in progress.canvas.calls if call[0] == "rectangle"]) >= 10

    progress.set_fraction(3)
    assert progress.fraction == 1
    progress.set_fraction(-1)
    assert progress.fraction == 0
