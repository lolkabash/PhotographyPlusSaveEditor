"""Visual tokens and ttk styles for the editor's compact desktop interface."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    "background": "#0D1117",
    "surface": "#161B22",
    "surface_raised": "#21262D",
    "surface_hover": "#30363D",
    "border": "#30363D",
    "text": "#E6EDF3",
    "muted": "#8B949E",
    "subtle": "#6E7681",
    "accent": "#1F6FEB",
    "accent_hover": "#388BFD",
    "teal": "#39C5CF",
    "success": "#3FB950",
    "warning": "#D29922",
    "danger": "#F85149",
    "spooky": "#FF7B72",
    "mundane": "#56D364",
    "on_accent": "#FFFFFF",
    "on_signal": "#0D1117",
    "canvas": "#010409",
}

DISPLAY_FONT = "Bahnschrift SemiBold"
BODY_FONT = "Segoe UI Variable Text"


def apply_theme(root: tk.Tk) -> ttk.Style:
    root.configure(background=COLORS["background"])
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        ".",
        background=COLORS["background"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["surface_raised"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        font=(BODY_FONT, 11),
    )
    style.configure("TFrame", background=COLORS["background"])
    style.configure("Header.TFrame", background=COLORS["surface"])
    style.configure("Band.TFrame", background=COLORS["surface_raised"])
    style.configure("Panel.TFrame", background=COLORS["surface"])
    style.configure("TLabel", background=COLORS["background"], foreground=COLORS["text"])
    style.configure("Header.TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Band.TLabel", background=COLORS["surface_raised"], foreground=COLORS["text"])
    style.configure("Panel.TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Title.TLabel", font=(DISPLAY_FONT, 19), background=COLORS["surface"])
    style.configure(
        "Eyebrow.TLabel",
        font=(DISPLAY_FONT, 9),
        foreground=COLORS["accent"],
        background=COLORS["surface"],
    )
    style.configure("Heading.TLabel", font=(DISPLAY_FONT, 12))
    style.configure("Muted.TLabel", foreground=COLORS["muted"])
    style.configure("BandMuted.TLabel", background=COLORS["surface_raised"], foreground=COLORS["muted"])
    style.configure("PanelMuted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
    style.configure("Success.TLabel", foreground=COLORS["success"])
    style.configure("Warning.TLabel", foreground=COLORS["warning"])
    style.configure("Danger.TLabel", foreground=COLORS["danger"])

    style.configure(
        "TButton",
        background=COLORS["surface_raised"],
        foreground=COLORS["text"],
        borderwidth=1,
        relief="flat",
        padding=(12, 7),
        focuscolor=COLORS["accent"],
        font=(BODY_FONT, 10),
    )
    style.map(
        "TButton",
        background=[("active", COLORS["surface_hover"]), ("disabled", COLORS["surface"])],
        foreground=[("disabled", COLORS["subtle"])],
    )
    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["on_accent"],
        font=(DISPLAY_FONT, 10),
        borderwidth=0,
        padding=(16, 8),
    )
    style.map(
        "Accent.TButton",
        background=[("active", COLORS["accent_hover"]), ("disabled", COLORS["surface_hover"])],
        foreground=[("disabled", COLORS["subtle"])],
    )
    style.configure("Compact.TButton", padding=(8, 5))

    style.configure(
        "Horizontal.TScale",
        background=COLORS["background"],
        troughcolor=COLORS["surface_hover"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["muted"],
        darkcolor=COLORS["muted"],
    )
    style.map(
        "Horizontal.TScale",
        background=[("active", COLORS["accent"])],
    )

    style.configure(
        "TEntry",
        fieldbackground=COLORS["surface_raised"],
        foreground=COLORS["text"],
        insertcolor=COLORS["text"],
        borderwidth=1,
        padding=6,
    )
    style.map(
        "TEntry",
        fieldbackground=[("readonly", COLORS["surface"]), ("disabled", COLORS["surface"])],
        foreground=[("readonly", COLORS["muted"]), ("disabled", COLORS["subtle"])],
    )
    style.configure(
        "Segment.TRadiobutton",
        background=COLORS["surface"],
        foreground=COLORS["muted"],
        indicatorcolor=COLORS["surface"],
        padding=(8, 5),
        borderwidth=1,
        relief="flat",
        indicatorbackground=COLORS["surface"],
    )
    style.map(
        "Segment.TRadiobutton",
        background=[("selected", COLORS["teal"]), ("active", COLORS["surface_hover"])],
        foreground=[("selected", COLORS["on_signal"]), ("active", COLORS["text"])],
        indicatorbackground=[("selected", COLORS["on_signal"]), ("active", COLORS["muted"])],
        indicatorcolor=[("selected", COLORS["on_signal"]), ("active", COLORS["muted"])],
    )
    style.configure(
        "TCheckbutton",
        background=COLORS["background"],
        foreground=COLORS["muted"],
        indicatorcolor=COLORS["surface_raised"],
        indicatorbackground=COLORS["surface_raised"],
        padding=4,
    )
    style.map(
        "TCheckbutton",
        background=[("active", COLORS["background"])],
        foreground=[("active", COLORS["text"])],
        indicatorbackground=[("selected", COLORS["teal"]), ("active", COLORS["surface_hover"])],
        indicatorcolor=[("selected", COLORS["teal"]), ("active", COLORS["surface_hover"])],
    )
    style.configure(
        "Treeview",
        background=COLORS["surface"],
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        borderwidth=0,
        rowheight=30,
        font=(BODY_FONT, 11),
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["accent"])],
        foreground=[("selected", COLORS["on_accent"])],
    )
    style.configure(
        "Vertical.TScrollbar",
        background=COLORS["surface_raised"],
        troughcolor=COLORS["surface"],
        bordercolor=COLORS["surface"],
        lightcolor=COLORS["surface_raised"],
        darkcolor=COLORS["surface_raised"],
        arrowcolor=COLORS["muted"],
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", COLORS["surface_hover"]), ("pressed", COLORS["accent"])],
        arrowcolor=[("active", COLORS["text"])],
    )
    style.configure("TPanedwindow", background=COLORS["border"])
    style.configure("Sash", sashthickness=5)
    return style
