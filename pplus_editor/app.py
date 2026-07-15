"""Application bootstrap for Photography Plus Save Editor V2."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from .catalog import CatalogError, EntityCatalog
from .paths import ENTITY_CATALOG_PATH
from .ui.main_window import MainWindow


def main() -> None:
    root = tk.Tk()
    try:
        catalog = EntityCatalog.load(ENTITY_CATALOG_PATH)
    except CatalogError as error:
        root.withdraw()
        messagebox.showerror("Catalog unavailable", str(error))
        root.destroy()
        return
    MainWindow(root, catalog)
    root.mainloop()


if __name__ == "__main__":
    main()
