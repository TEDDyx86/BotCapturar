"""Small pixel-framed Tk surfaces used by the Capturix control room."""

from __future__ import annotations

import tkinter as tk

from botcapturar.theme import COLORS, FONTS


class PixelPanel:
    """Gold-framed panel that keeps its content in ordinary Tk widgets."""

    def __init__(self, master, *, title: str, canvas_height: int = 300) -> None:
        self.widget = tk.Frame(master, background=COLORS["gold"], padx=2, pady=2)
        self.canvas = tk.Canvas(
            self.widget,
            background=COLORS["panel"],
            height=canvas_height,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, background=COLORS["panel"])
        self._body_window = self.canvas.create_window(12, 48, anchor="nw", window=self.body)
        self._title = title
        self.canvas.bind("<Configure>", self._redraw_frame)

    def _redraw_frame(self, event) -> None:
        width = max(1, int(event.width))
        height = max(1, int(event.height))
        gold = COLORS["gold"]
        muted = COLORS["gold_muted"]
        self.canvas.delete("frame")

        # Short stepped corners give each panel a pixel-cut frame.
        self.canvas.create_line(12, 3, width - 12, 3, fill=gold, width=2, tags="frame")
        self.canvas.create_line(12, height - 3, width - 12, height - 3, fill=gold, width=2, tags="frame")
        self.canvas.create_line(3, 12, 3, height - 12, fill=gold, width=2, tags="frame")
        self.canvas.create_line(width - 3, 12, width - 3, height - 12, fill=gold, width=2, tags="frame")
        self.canvas.create_line(3, 12, 8, 12, fill=gold, width=2, tags="frame")
        self.canvas.create_line(12, 3, 12, 8, fill=gold, width=2, tags="frame")
        self.canvas.create_line(width - 8, 12, width - 3, 12, fill=gold, width=2, tags="frame")
        self.canvas.create_line(width - 12, 3, width - 12, 8, fill=gold, width=2, tags="frame")
        self.canvas.create_line(3, height - 12, 8, height - 12, fill=gold, width=2, tags="frame")
        self.canvas.create_line(12, height - 8, 12, height - 3, fill=gold, width=2, tags="frame")
        self.canvas.create_line(width - 8, height - 12, width - 3, height - 12, fill=gold, width=2, tags="frame")
        self.canvas.create_line(width - 12, height - 8, width - 12, height - 3, fill=gold, width=2, tags="frame")
        self.canvas.create_text(
            20,
            24,
            anchor="w",
            text=self._title,
            fill=COLORS["gold"],
            font=FONTS["panel-title"],
            tags="frame",
        )
        self.canvas.create_line(12, 42, width - 12, 42, fill=muted, width=1, tags="frame")
        self.canvas.coords(self._body_window, 12, 50)
        self.canvas.itemconfigure(
            self._body_window,
            width=max(1, width - 24),
            height=max(1, height - 60),
        )


class SegmentedProgressBar:
    """A gold-framed segmented bar filled as the next-send timer elapses."""

    def __init__(
        self,
        master,
        *,
        segments: int = 36,
        width: int = 640,
        height: int = 28,
    ) -> None:
        if segments < 1:
            raise ValueError("segments must be at least one")
        self.segments = segments
        self.width = width
        self.height = height
        self.fraction = 0.0
        self.canvas = tk.Canvas(
            master,
            background=COLORS["panel"],
            width=width,
            height=height,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.bind("<Configure>", self._draw)
        self._draw()

    def set_fraction(self, fraction: float) -> None:
        self.fraction = min(1.0, max(0.0, float(fraction)))
        self._draw()

    def _draw(self, event=None) -> None:
        width = int(getattr(event, "width", self.width) or self.width)
        height = int(getattr(event, "height", self.height) or self.height)
        pad = 3
        gap = 3
        usable_width = max(1, width - 2 * pad)
        segment_width = max(1, (usable_width - gap * (self.segments - 1)) // self.segments)
        filled = round(self.fraction * self.segments)
        self.canvas.delete("all")
        self.canvas.create_rectangle(
            1,
            1,
            width - 1,
            height - 1,
            outline=COLORS["gold"],
            width=2,
        )
        for index in range(self.segments):
            x1 = pad + index * (segment_width + gap)
            self.canvas.create_rectangle(
                x1,
                pad,
                x1 + segment_width,
                height - pad,
                fill=COLORS["success"] if index < filled else COLORS["inset"],
                outline=COLORS["gold_muted"],
                width=1,
            )
