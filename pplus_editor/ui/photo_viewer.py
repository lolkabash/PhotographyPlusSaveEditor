"""Zoomable, responsive photo canvas used by the main editor window."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk

from .theme import BODY_FONT, COLORS


class PhotoViewer(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self._source_image: Image.Image | None = None
        self._rendered_image: ImageTk.PhotoImage | None = None
        self._empty_message = "NO PHOTO LOADED"
        self._fit_to_window = True
        self._resize_job: str | None = None

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(toolbar, text="ZOOM", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Button(toolbar, text="-", width=3, style="Compact.TButton", command=lambda: self._nudge_zoom(-0.1)).pack(
            side=tk.LEFT, padx=(10, 2)
        )
        self.zoom_value = tk.DoubleVar(value=1.0)
        self.zoom_scale = ttk.Scale(
            toolbar,
            from_=0.25,
            to=2.0,
            variable=self.zoom_value,
            command=self._scale_changed,
            length=130,
        )
        self.zoom_scale.pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="+", width=3, style="Compact.TButton", command=lambda: self._nudge_zoom(0.1)).pack(
            side=tk.LEFT, padx=2
        )
        self.zoom_text = tk.StringVar(value="FIT")
        ttk.Label(toolbar, textvariable=self.zoom_text, style="Muted.TLabel", width=6).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Fit", style="Compact.TButton", command=self.fit).pack(side=tk.LEFT)

        self.canvas = tk.Canvas(
            self,
            background=COLORS["canvas"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            relief=tk.FLAT,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self._draw_empty()

    def show_image(self, path: Path) -> None:
        with Image.open(path) as image:
            image.load()
            self._source_image = image.convert("RGB")
        self._fit_to_window = True
        self.zoom_text.set("FIT")
        self._render()

    def show_deleted(self, index: int) -> None:
        self._source_image = None
        self._empty_message = f"PHOTO {index} / DELETED"
        self._draw_empty()

    def show_empty(self) -> None:
        self._source_image = None
        self._empty_message = "NO PHOTO LOADED"
        self._draw_empty()

    def fit(self) -> None:
        self._fit_to_window = True
        self.zoom_text.set("FIT")
        self._render()

    def _nudge_zoom(self, amount: float) -> None:
        value = min(2.0, max(0.25, self.zoom_value.get() + amount))
        self.zoom_value.set(value)
        self._fit_to_window = False
        self._render()

    def _scale_changed(self, _value: str) -> None:
        self._fit_to_window = False
        self._render()

    def _on_mouse_wheel(self, event: tk.Event) -> str:
        self._nudge_zoom(0.1 if event.delta > 0 else -0.1)
        return "break"

    def _on_resize(self, _event: tk.Event) -> None:
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(60, self._render)

    def _render(self) -> None:
        self._resize_job = None
        if self._source_image is None:
            self._draw_empty()
            return
        width = max(1, self.canvas.winfo_width() - 24)
        height = max(1, self.canvas.winfo_height() - 24)
        image = self._source_image.copy()
        if self._fit_to_window:
            image.thumbnail((width, height), Image.Resampling.LANCZOS)
            self.zoom_text.set("FIT")
        else:
            scale = self.zoom_value.get()
            image = image.resize(
                (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                Image.Resampling.LANCZOS,
            )
            self.zoom_text.set(f"{int(scale * 100)}%")
        self._rendered_image = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            image=self._rendered_image,
            anchor=tk.CENTER,
        )

    def _draw_empty(self) -> None:
        self.canvas.delete("all")
        self.canvas.create_text(
            max(1, self.canvas.winfo_width()) // 2,
            max(1, self.canvas.winfo_height()) // 2,
            text=self._empty_message,
            fill=COLORS["subtle"],
            font=(BODY_FONT, 13, "bold"),
        )
