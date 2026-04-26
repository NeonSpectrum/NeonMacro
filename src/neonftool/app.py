from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from .logging_setup import configure_logging
from .ui.main_window import MainWindow


def config_path() -> Path:
    base = Path.home() / "AppData" / "Local" / "NeonFtool"
    return base / "config.json"


def main() -> None:
    configure_logging(config_path().parent / "neonftool.log")
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    window = MainWindow(config_path=config_path())
    window.mainloop()


if __name__ == "__main__":
    main()

