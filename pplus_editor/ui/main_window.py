"""Main V2 window coordinating user actions with the editor services."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from ..catalog import EntityCatalog
from ..models import PhotoArchive, ProgressState
from ..paths import (
    ENTITY_ICONS_DIRECTORY,
    PHOTOS_DIRECTORY,
    PROGRESS_PATH,
    SETTINGS_PATH,
    USER_DATA_DIRECTORY,
    VOTV_SAVE_DIRECTORY,
)
from ..services.photo_archive import extract_photo_archive
from ..services.pp_save import build_pp_save, load_pp_labels
from ..services.progress_store import load_progress, save_progress
from ..services.settings_store import load_settings, save_settings
from ..session import EditorSession
from .entity_panel import EntityPanel
from .photo_viewer import PhotoViewer
from .theme import BODY_FONT, COLORS, DISPLAY_FONT, apply_theme


class MainWindow:
    def __init__(self, root: tk.Tk, catalog: EntityCatalog) -> None:
        self.root = root
        self.catalog = catalog
        self.session = EditorSession(catalog)
        self.settings = load_settings(SETTINGS_PATH)
        self.busy = False

        self.root.title("Photography Plus Save Editor V2")
        self.root.geometry("1200x780")
        self.root.minsize(900, 600)
        apply_theme(root)

        self.main_save_value = tk.StringVar(value=str(self.settings.get("main_save", "")))
        self.pp_source_value = tk.StringVar(value=str(self.settings.get("pp_source", "")))
        self.photo_title = tk.StringVar(value="PHOTO --")
        self.photo_state = tk.StringVar(value="NO WORKSPACE")
        self.mapping_value = tk.StringVar(value="Unlabelled")
        self.status_value = tk.StringVar(value="Ready")
        self.autosave_value = tk.StringVar(value="● Autosave on")
        self.goto_value = tk.StringVar()
        self.include_deleted_value = tk.BooleanVar(value=bool(self.settings.get("include_deleted", False)))

        self._build_menu()
        self._build_layout()
        self._bind_shortcuts()
        self._refresh_all()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_menu(self) -> None:
        menu = tk.Menu(
            self.root,
            background=COLORS["surface"],
            foreground=COLORS["text"],
            activebackground=COLORS["accent"],
            activeforeground=COLORS["on_accent"],
            tearoff=False,
        )
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Select vanilla save", command=self.pick_main_save, accelerator="Ctrl+O")
        file_menu.add_command(label="Select PP source", command=self.pick_pp_source)
        file_menu.add_command(label="Load workspace", command=self.load_workspace, accelerator="Ctrl+L")
        file_menu.add_separator()
        file_menu.add_command(label="Import progress", command=self.import_progress)
        file_menu.add_command(label="Save progress", command=self.save_progress_now, accelerator="Ctrl+S")
        file_menu.add_command(label="Export PP save", command=self.export_save, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.close)
        menu.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menu, tearoff=False)
        edit_menu.add_command(label="Undo label", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo label", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_command(label="Clear current label", command=self.clear_label, accelerator="Backspace")
        menu.add_cascade(label="Edit", menu=edit_menu)
        self.root.configure(menu=menu)

    def _build_layout(self) -> None:
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(20, 12))
        header.pack(fill=tk.X)
        ttk.Label(header, text="Photography Plus Save Editor", style="Title.TLabel").pack(side=tk.LEFT)

        header_status = ttk.Frame(header, style="Header.TFrame")
        header_status.pack(side=tk.RIGHT)
        self.status_label = ttk.Label(
            header_status,
            textvariable=self.status_value,
            style="Header.TLabel",
            foreground=COLORS["muted"],
            font=(BODY_FONT, 9),
        )
        self.status_label.pack(side=tk.LEFT, padx=(0, 16))
        self.autosave_label = ttk.Label(
            header_status,
            textvariable=self.autosave_value,
            style="Header.TLabel",
            foreground=COLORS["success"],
            font=(BODY_FONT, 9),
        )
        self.autosave_label.pack(side=tk.LEFT)

        source_band = ttk.Frame(self.root, style="Band.TFrame", padding=(20, 10))
        source_band.pack(fill=tk.X)
        source_band.columnconfigure(1, weight=1)
        ttk.Label(source_band, text="VANILLA SAVE", style="BandMuted.TLabel", width=16).grid(row=0, column=0, sticky=tk.W)
        self.main_entry = ttk.Entry(source_band, textvariable=self.main_save_value, state="readonly")
        self.main_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 8))
        ttk.Button(source_band, text="Browse", command=self.pick_main_save).grid(row=0, column=2, padx=(0, 14))
        ttk.Label(source_band, text="PP SOURCE", style="BandMuted.TLabel", width=16).grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        self.pp_entry = ttk.Entry(source_band, textvariable=self.pp_source_value, state="readonly")
        self.pp_entry.grid(row=1, column=1, sticky=tk.EW, padx=(0, 8), pady=(8, 0))
        ttk.Button(source_band, text="Browse", command=self.pick_pp_source).grid(row=1, column=2, padx=(0, 14), pady=(8, 0))
        ttk.Button(source_band, text="Clear", style="Compact.TButton", command=self.clear_pp_source).grid(
            row=1, column=3, padx=(0, 14), pady=(8, 0)
        )
        self.load_button = ttk.Button(source_band, text="Load [Ctrl+L]", style="Accent.TButton", command=self.load_workspace)
        self.load_button.grid(row=0, column=4, rowspan=2, padx=(0, 8))
        self.export_button = ttk.Button(source_band, text="Export [Ctrl+E]", command=self.export_save)
        self.export_button.grid(row=0, column=5, rowspan=2)

        body = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=(10, 10))
        photo_area = ttk.Frame(body, padding=(4, 2, 12, 0))
        body.add(photo_area, weight=4)

        navigation = ttk.Frame(photo_area)
        navigation.pack(fill=tk.X, pady=(0, 8))
        self.previous_button = ttk.Button(navigation, text="Prev [A]", style="Compact.TButton", command=lambda: self.navigate(-1))
        self.previous_button.pack(side=tk.LEFT)
        self.next_button = ttk.Button(navigation, text="Next [D]", style="Compact.TButton", command=lambda: self.navigate(1))
        self.next_button.pack(side=tk.LEFT, padx=(4, 14))
        ttk.Label(navigation, textvariable=self.photo_title, font=(DISPLAY_FONT, 12)).pack(side=tk.LEFT)
        self.photo_state_label = ttk.Label(navigation, textvariable=self.photo_state, style="Muted.TLabel")
        self.photo_state_label.pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(
            navigation,
            text="Show deleted",
            variable=self.include_deleted_value,
            command=self.toggle_deleted,
        ).pack(side=tk.RIGHT)
        ttk.Button(navigation, text="Unlabelled [N]", command=self.next_unlabelled).pack(side=tk.RIGHT, padx=(6, 12))
        self.goto_entry = ttk.Entry(navigation, textvariable=self.goto_value, width=7)
        self.goto_entry.pack(side=tk.RIGHT)
        self.goto_entry.bind("<Return>", lambda _event: self.go_to_index())
        ttk.Label(navigation, text="Index", style="Muted.TLabel").pack(side=tk.RIGHT, padx=(0, 5))

        self.photo_viewer = PhotoViewer(photo_area)
        self.photo_viewer.pack(fill=tk.BOTH, expand=True)

        mapping_bar = ttk.Frame(photo_area, padding=(0, 10, 0, 0))
        mapping_bar.pack(fill=tk.X)
        ttk.Label(mapping_bar, text="MAPPING", style="Muted.TLabel").pack(side=tk.LEFT)
        self.mapping_label = ttk.Label(mapping_bar, textvariable=self.mapping_value, font=(DISPLAY_FONT, 10))
        self.mapping_label.pack(side=tk.LEFT, padx=10)
        self.clear_button = ttk.Button(mapping_bar, text="Clear [Backspace]", style="Compact.TButton", command=self.clear_label)
        self.clear_button.pack(side=tk.RIGHT)
        self.redo_button = ttk.Button(mapping_bar, text="Redo [Ctrl+Y]", style="Compact.TButton", command=self.redo)
        self.redo_button.pack(side=tk.RIGHT, padx=4)
        self.undo_button = ttk.Button(mapping_bar, text="Undo [Ctrl+Z]", style="Compact.TButton", command=self.undo)
        self.undo_button.pack(side=tk.RIGHT)

        self.entity_panel = EntityPanel(body, self.catalog, ENTITY_ICONS_DIRECTORY, self.assign_and_next)
        self.entity_panel.set_category(str(self.settings.get("entity_category", "all")))
        body.add(self.entity_panel, weight=2)

    def _bind_shortcuts(self) -> None:
        for widget_class in ("TButton", "TCheckbutton", "TRadiobutton"):
            self.root.bind_class(
                widget_class,
                "<ButtonRelease-1>",
                self._return_hotkey_focus,
                add="+",
            )
        self.root.bind("<Control-o>", lambda _event: self.pick_main_save())
        self.root.bind("<Control-l>", lambda _event: self.load_workspace())
        self.root.bind("<Control-s>", lambda _event: self.save_progress_now())
        self.root.bind("<Control-e>", lambda _event: self.export_save())
        self.root.bind("<Control-z>", lambda _event: self.undo())
        self.root.bind("<Control-y>", lambda _event: self.redo())
        self.root.bind("<Control-f>", lambda _event: self.entity_panel.focus_search())
        self.root.bind("<Left>", lambda event: self._shortcut(event, lambda: self.navigate(-1)))
        self.root.bind("<Right>", lambda event: self._shortcut(event, lambda: self.navigate(1)))
        self.root.bind("a", lambda event: self._shortcut(event, lambda: self.navigate(-1)))
        self.root.bind("d", lambda event: self._shortcut(event, lambda: self.navigate(1)))
        self.root.bind("n", lambda event: self._shortcut(event, self.next_unlabelled))
        self.root.bind("<space>", lambda event: self._shortcut(event, self.assign_and_next))
        self.root.bind("<BackSpace>", lambda event: self._shortcut(event, self.clear_label))
        self.root.bind("<Up>", lambda event: self._shortcut(event, lambda: self.entity_panel.move_selection(-1)))
        self.root.bind("<Down>", lambda event: self._shortcut(event, lambda: self.entity_panel.move_selection(1)))
        self.root.bind("w", lambda event: self._shortcut(event, lambda: self.entity_panel.move_selection(-1)))
        self.root.bind("s", lambda event: self._shortcut(event, lambda: self.entity_panel.move_selection(1)))

    def _return_hotkey_focus(self, _event: tk.Event) -> None:
        self.root.after_idle(self.root.focus_set)

    def _shortcut(self, event: tk.Event, action: Any) -> str | None:
        widget = event.widget
        if event.state & 0x0004:
            return None
        if isinstance(widget, (tk.Entry, tk.Text, ttk.Entry)):
            return None
        action()
        return "break"

    def pick_main_save(self) -> None:
        path = filedialog.askopenfilename(
            title="Select vanilla sub-save",
            filetypes=[("VotV save", "*.sav"), ("All files", "*.*")],
            initialdir=self._initial_directory(self.main_save_value.get()),
        )
        if path:
            self.main_save_value.set(path)
            self._save_settings()

    def pick_pp_source(self) -> None:
        path = filedialog.askopenfilename(
            title="Select PP save or online-editor JSON",
            filetypes=[("PP save", "*.sav"), ("Online-editor JSON", "*.json"), ("All files", "*.*")],
            initialdir=self._initial_directory(self.pp_source_value.get()),
        )
        if path:
            self.pp_source_value.set(path)
            self._save_settings()

    def clear_pp_source(self) -> None:
        self.pp_source_value.set("")
        self._save_settings()

    def load_workspace(self) -> None:
        if self.busy:
            return
        main_path = Path(self.main_save_value.get())
        if not main_path.is_file():
            messagebox.showwarning("Vanilla save required", "Select a valid vanilla s__SUB_*.sav file.")
            return
        pp_text = self.pp_source_value.get().strip()
        pp_path = Path(pp_text) if pp_text else None
        if pp_path and not pp_path.is_file():
            messagebox.showwarning("PP source not found", "The selected PP save or JSON file does not exist.")
            return

        self._set_busy(True, "Reading save and extracting indexed photos...")

        def worker() -> None:
            try:
                archive = extract_photo_archive(main_path, PHOTOS_DIRECTORY)
                labels = load_pp_labels(pp_path) if pp_path else {}
                self.root.after(0, lambda: self._finish_workspace_load(archive, labels))
            except Exception as error:
                self.root.after(0, lambda error=error: self._show_background_error("Load failed", error))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_workspace_load(self, archive: PhotoArchive, prelabels: dict[int, str]) -> None:
        self.session.set_archive(archive)
        self.session.include_deleted = self.include_deleted_value.get()
        labels = prelabels
        progress = self._resume_candidate(archive)
        if progress is not None:
            labels = progress.labels
        warnings = self.session.set_labels(labels)
        if warnings:
            messagebox.showwarning("Some labels were ignored", "\n".join(warnings[:8]))
        self._set_busy(False)
        self._refresh_all(sync_entity=True)
        self._set_status(
            f"Loaded {len(archive.photos)} slots: {archive.surviving_count} photos, "
            f"{archive.deleted_count} deleted, {len(self.session.labels)} labels"
        )

    def _resume_candidate(self, archive: PhotoArchive) -> ProgressState | None:
        if not PROGRESS_PATH.exists():
            return None
        try:
            progress = load_progress(PROGRESS_PATH)
        except Exception as error:
            messagebox.showwarning("Progress unavailable", str(error))
            return None
        match = progress.matches(archive)
        if match is True:
            return progress
        if match is False:
            prompt = "Saved progress belongs to a different vanilla save. Import it anyway?"
        else:
            prompt = f"Import {len(progress.labels)} saved labels?"
        return progress if messagebox.askyesno("Resume progress", prompt) else None

    def import_progress(self) -> None:
        if self.session.archive is None:
            messagebox.showwarning("No workspace", "Load a vanilla save before importing progress.")
            return
        path_text = filedialog.askopenfilename(
            title="Import progress",
            filetypes=[("JSON progress", "*.json"), ("All files", "*.*")],
            initialdir=str(USER_DATA_DIRECTORY),
        )
        if not path_text:
            return
        try:
            progress = load_progress(Path(path_text))
            if progress.matches(self.session.archive) is False and not messagebox.askyesno(
                "Different source save",
                "This progress belongs to a different vanilla save. Import it anyway?",
            ):
                return
            warnings = self.session.set_labels(progress.labels)
            self._autosave("Imported progress")
            self._refresh_all(sync_entity=True)
            if warnings:
                messagebox.showwarning("Some labels were ignored", "\n".join(warnings[:8]))
        except Exception as error:
            messagebox.showerror("Import failed", str(error))

    def save_progress_now(self) -> None:
        if self.session.archive is None:
            messagebox.showwarning("No workspace", "Load a vanilla save first.")
            return
        self._autosave("Progress saved")

    def export_save(self) -> None:
        archive = self.session.archive
        if archive is None:
            messagebox.showwarning("No workspace", "Load a vanilla save first.")
            return
        template_text = self.pp_source_value.get().strip()
        template_path = Path(template_text) if template_text else None
        if template_path is None or template_path.suffix.lower() != ".sav":
            selected = filedialog.askopenfilename(
                title="Select binary PP save template",
                filetypes=[("PP save", "*.sav"), ("All files", "*.*")],
                initialdir=self._initial_directory(template_text),
            )
            if not selected:
                return
            template_path = Path(selected)
        labelled, total = self.session.surviving_progress()
        if labelled < total and not messagebox.askyesno(
            "Unlabelled photos remain",
            f"{total - labelled} surviving photos are still unlabelled. Export current mappings anyway?",
        ):
            return
        output_text = filedialog.asksaveasfilename(
            title="Export corrected PP save",
            defaultextension=".sav",
            filetypes=[("PP save", "*.sav")],
            initialdir=str(template_path.parent),
            initialfile=f"{template_path.stem}_V2_FIXED.sav",
        )
        if not output_text:
            return
        output_path = Path(output_text)
        if output_path.resolve() == template_path.resolve():
            messagebox.showerror("Choose a new file", "The export cannot overwrite its template save.")
            return
        try:
            stats = build_pp_save(template_path, output_path, self.session.labels, archive, self.catalog)
            messagebox.showinfo(
                "Export complete",
                f"Saved {output_path.name}\n\n"
                f"Mundane mappings: {stats.mundane}\n"
                f"Spooky mappings: {stats.spooky}\n"
                f"Surviving bestiary mappings: {stats.bestiary_mundane + stats.bestiary_spooky}",
            )
            self._set_status(f"Exported and verified {output_path.name}")
        except Exception as error:
            messagebox.showerror("Export failed", str(error))

    def navigate(self, step: int) -> None:
        if self.session.navigate(step):
            self._refresh_all(sync_entity=True)

    def go_to_index(self) -> None:
        try:
            index = int(self.goto_value.get())
        except ValueError:
            messagebox.showwarning("Invalid index", "Enter a numeric photo index.")
            return
        if self.session.go_to(index) is None:
            messagebox.showwarning("Index out of range", "That photo index is not in the loaded save.")
            return
        self._refresh_all(sync_entity=True)

    def next_unlabelled(self) -> None:
        if self.session.next_unlabelled() is None:
            if self.session.archive is not None:
                messagebox.showinfo("Labelling complete", "Every visible photo has a mapping.")
            return
        self._refresh_all(sync_entity=False)

    def toggle_deleted(self) -> None:
        self.session.include_deleted = self.include_deleted_value.get()
        self._save_settings()
        current = self.session.current_photo
        if current and not current.has_image and not self.session.include_deleted:
            self.session.navigate(1)
        self._refresh_all(sync_entity=False)

    def assign_and_next(self) -> None:
        entity = self.entity_panel.selected_entity
        if entity is None or self.session.current_photo is None:
            return
        changed = self.session.assign(entity.name)
        if changed:
            self._autosave(f"Mapped photo {self.session.current_index} to {entity.name}")
        self.session.navigate(1)
        self._refresh_all(sync_entity=False)

    def clear_label(self) -> None:
        if self.session.assign(None):
            self._autosave(f"Cleared photo {self.session.current_index}")
            self._refresh_all(sync_entity=False)

    def undo(self) -> None:
        if self.session.undo():
            self._autosave("Undid label change")
            self._refresh_all(sync_entity=True)

    def redo(self) -> None:
        if self.session.redo():
            self._autosave("Redid label change")
            self._refresh_all(sync_entity=True)

    def _autosave(self, status: str) -> None:
        if self.session.archive is None:
            return
        try:
            save_progress(PROGRESS_PATH, self.session.labels, self.session.archive)
            self._set_autosave_state(True)
            self._set_status(f"{status} / autosaved {len(self.session.labels)} labels")
        except Exception as error:
            self._set_autosave_state(False)
            self._set_status(f"Autosave failed: {error}", "danger")

    def _refresh_all(self, sync_entity: bool = False) -> None:
        photo = self.session.current_photo
        has_workspace = self.session.archive is not None
        for button in (self.previous_button, self.next_button, self.clear_button):
            button.configure(state=tk.NORMAL if has_workspace else tk.DISABLED)
        self.export_button.configure(state=tk.NORMAL if has_workspace else tk.DISABLED)
        self.undo_button.configure(state=tk.NORMAL if self.session.can_undo else tk.DISABLED)
        self.redo_button.configure(state=tk.NORMAL if self.session.can_redo else tk.DISABLED)

        if photo is None:
            self.photo_title.set("PHOTO --")
            self.photo_state.set("NO WORKSPACE")
            self.mapping_value.set("Unlabelled")
            self.photo_viewer.show_empty()
            return

        visible = self.session.visible_photos()
        position = next((number for number, item in enumerate(visible, start=1) if item.index == photo.index), 0)
        self.photo_title.set(f"PHOTO {photo.index}")
        self.photo_state.set(f"{position} / {len(visible)}" + ("  DELETED" if not photo.has_image else ""))
        label = self.session.labels.get(photo.index)
        self.mapping_value.set(label or "Unlabelled")
        if photo.has_image:
            image_path = photo.image_path(PHOTOS_DIRECTORY)
            if image_path and image_path.exists():
                self.photo_viewer.show_image(image_path)
            else:
                self.photo_viewer.show_empty()
        else:
            self.photo_viewer.show_deleted(photo.index)
        if sync_entity and label:
            self.entity_panel.select_entity(label)

    def _set_busy(self, busy: bool, status: str | None = None) -> None:
        self.busy = busy
        self.load_button.configure(state=tk.DISABLED if busy else tk.NORMAL)
        self.root.configure(cursor="wait" if busy else "")
        if status:
            self._set_status(status)

    def _show_background_error(self, title: str, error: Exception) -> None:
        self._set_busy(False)
        messagebox.showerror(title, str(error))
        self._set_status(str(error), "danger")

    def _set_status(self, value: str, kind: str = "normal") -> None:
        self.status_value.set(value)
        color = COLORS["danger"] if kind == "danger" else COLORS["muted"]
        self.status_label.configure(foreground=color)

    def _set_autosave_state(self, enabled: bool) -> None:
        self.autosave_value.set("● Autosave on" if enabled else "× Autosave off")
        self.autosave_label.configure(
            foreground=COLORS["success"] if enabled else COLORS["danger"]
        )

    def _save_settings(self) -> None:
        self.settings.update(
            {
                "main_save": self.main_save_value.get(),
                "pp_source": self.pp_source_value.get(),
                "include_deleted": self.include_deleted_value.get(),
                "entity_category": self.entity_panel.category.get() if hasattr(self, "entity_panel") else "all",
            }
        )
        save_settings(SETTINGS_PATH, self.settings)

    @staticmethod
    def _initial_directory(path_text: str) -> str:
        path = Path(path_text) if path_text else VOTV_SAVE_DIRECTORY
        return str(path.parent if path.suffix else path)

    def close(self) -> None:
        self._save_settings()
        self.root.destroy()
