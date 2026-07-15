"""Compact searchable entity picker with bestiary icon and hint."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable

from ..catalog import EntityCatalog
from ..models import EntityRecord
from .theme import BODY_FONT, COLORS, DISPLAY_FONT


HINT_PREFIXES = {
    "VeryMissable",
    "Missable",
    "G",
    "S",
    "A",
    "N",
    "D",
    "K",
    "KL",
    "KP",
}


def clean_hint(value: str) -> str:
    prefix, separator, remainder = value.partition("_")
    if separator and prefix in HINT_PREFIXES:
        return remainder
    return value


class EntityPanel(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        catalog: EntityCatalog,
        icons_directory: Path,
        on_assign: Callable[[], None],
    ) -> None:
        super().__init__(parent, style="Panel.TFrame", padding=(12, 10))
        self.catalog = catalog
        self.icons_directory = icons_directory
        self.on_assign = on_assign
        self.selected_name: str | None = None
        self._icon_image: tk.PhotoImage | None = None
        self._visible_entities: tuple[EntityRecord, ...] = ()

        ttk.Label(self, text="ENTITIES [▲ W | ▼ S]", style="Panel.TLabel", font=(DISPLAY_FONT, 13)).pack(anchor=tk.W)

        self.category = tk.StringVar(value="all")
        category_row = ttk.Frame(self, style="Panel.TFrame")
        category_row.pack(fill=tk.X, pady=(6, 6))
        for label, value in (("All", "all"), ("Spooky", "spooky"), ("Mundane", "mundane")):
            ttk.Radiobutton(
                category_row,
                text=label,
                value=value,
                variable=self.category,
                style="Segment.TRadiobutton",
                command=self.refresh_list,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.search_value = tk.StringVar()
        self.search_value.trace_add("write", lambda *_: self.refresh_list())
        ttk.Label(self, text="SEARCH [CTRL+F]", style="PanelMuted.TLabel", font=(BODY_FONT, 9)).pack(anchor=tk.W)
        self.search_entry = ttk.Entry(self, textvariable=self.search_value)
        self.search_entry.pack(fill=tk.X, pady=(2, 7))

        self.assign_button = ttk.Button(
            self,
            text="Assign [Space]",
            style="Accent.TButton",
            command=self.on_assign,
        )
        self.assign_button.pack(side=tk.BOTTOM, fill=tk.X, pady=(7, 0))

        detail = ttk.Frame(self, style="Panel.TFrame", height=100)
        detail.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))
        detail.grid_propagate(False)
        detail.columnconfigure(0, weight=1)
        detail.rowconfigure(1, weight=1)

        self.entity_name = tk.StringVar(value="Select an entity")
        self.entity_name_label = ttk.Label(
            detail,
            textvariable=self.entity_name,
            style="Panel.TLabel",
            font=(DISPLAY_FONT, 11),
            wraplength=280,
            justify=tk.CENTER,
            anchor=tk.CENTER,
        )
        self.entity_name_label.grid(row=0, column=0, sticky=tk.EW)

        content = ttk.Frame(detail, style="Panel.TFrame")
        content.grid(row=1, column=0, sticky=tk.NSEW, pady=(2, 0))
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        icon_slot = ttk.Frame(content, style="Panel.TFrame", width=49, height=49)
        icon_slot.grid(row=0, column=0, sticky=tk.NW, padx=(0, 9))
        icon_slot.pack_propagate(False)
        self.icon_label = ttk.Label(icon_slot, style="Panel.TLabel", anchor=tk.CENTER)
        self.icon_label.pack(fill=tk.BOTH, expand=True)

        self.hint_value = tk.StringVar(value="")
        self.hint_label = ttk.Label(
            content,
            textvariable=self.hint_value,
            style="PanelMuted.TLabel",
            font=(BODY_FONT, 10),
            wraplength=180,
            justify=tk.LEFT,
            anchor=tk.NW,
        )
        self.hint_label.grid(row=0, column=1, sticky=tk.NW)
        detail.bind("<Configure>", self._resize_detail)
        content.bind("<Configure>", self._resize_content)

        tree_frame = ttk.Frame(self, style="Panel.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree = ttk.Treeview(
            tree_frame,
            show="tree",
            selectmode="browse",
            yscrollcommand=scrollbar.set,
            height=8,
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.configure(command=self.tree.yview)
        self.tree.tag_configure("spooky", foreground=COLORS["spooky"])
        self.tree.tag_configure("mundane", foreground=COLORS["mundane"])
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.tree.bind("<Double-Button-1>", lambda _event: self.on_assign())

        self.refresh_list()

    @property
    def selected_entity(self) -> EntityRecord | None:
        return self.catalog.get(self.selected_name) if self.selected_name else None

    def set_category(self, category: str) -> None:
        self.category.set(category if category in ("all", "spooky", "mundane") else "all")
        self.refresh_list()

    def refresh_list(self) -> None:
        category = None if self.category.get() == "all" else self.category.get()
        self._visible_entities = self.catalog.search(self.search_value.get(), category)  # type: ignore[arg-type]
        self.tree.delete(*self.tree.get_children())
        for entity in self._visible_entities:
            self.tree.insert("", tk.END, iid=entity.name, text=entity.name, tags=(entity.category,))
        if self.selected_name and self.tree.exists(self.selected_name):
            self.tree.selection_set(self.selected_name)
            self.tree.see(self.selected_name)

    def select_entity(self, entity_name: str) -> None:
        entity = self.catalog.get(entity_name)
        if entity is None:
            return
        self.selected_name = entity_name
        if self.tree.exists(entity_name):
            self.tree.selection_set(entity_name)
            self.tree.see(entity_name)
        self._show_entity(entity)

    def move_selection(self, step: int) -> None:
        if not self._visible_entities:
            return
        names = [entity.name for entity in self._visible_entities]
        try:
            position = names.index(self.selected_name) if self.selected_name else -1
        except ValueError:
            position = -1
        position = min(max(position + step, 0), len(names) - 1)
        self.select_entity(names[position])

    def focus_search(self) -> None:
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, tk.END)

    def _selection_changed(self, _event: tk.Event | None = None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_name = selection[0]
        entity = self.catalog.get(self.selected_name)
        if entity:
            self._show_entity(entity)

    def _show_entity(self, entity: EntityRecord) -> None:
        self.entity_name.set(entity.name)
        self._show_icon(entity)
        self.hint_value.set(clean_hint(entity.hint_short) or "No hint available.")

    def _resize_detail(self, event: tk.Event) -> None:
        self.entity_name_label.configure(wraplength=max(80, event.width - 4))

    def _resize_content(self, event: tk.Event) -> None:
        self.hint_label.configure(wraplength=max(80, event.width - 58))

    def _show_icon(self, entity: EntityRecord) -> None:
        icon_path = self.icons_directory / entity.icon
        if icon_path.exists():
            self._icon_image = tk.PhotoImage(file=str(icon_path))
            self.icon_label.configure(image=self._icon_image, text="")
        else:
            initials = "".join(part[0] for part in entity.name.split()[:2]).upper() or "?"
            self._icon_image = None
            self.icon_label.configure(image="", text=initials)
