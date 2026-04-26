from __future__ import annotations

import ctypes
from pathlib import Path

import customtkinter as ctk

from .logging_setup import configure_logging
from .ui.main_window import MainWindow


def config_path() -> Path:
    base = Path.home() / "AppData" / "Local" / "NeonFtool"
    return base / "config.json"


def _set_windows_app_user_model_id() -> None:
    # Helps Windows taskbar use this app identity/icon instead of fallback defaults.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "NeonSpectrum.NeonFtool"
        )
    except (AttributeError, OSError):
        pass


def main() -> None:
    configure_logging(config_path().parent / "debug.log")
    _set_windows_app_user_model_id()
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    window = MainWindow(config_path=config_path())
    try:
        window.mainloop()
    except KeyboardInterrupt:
        # Let Ctrl+C in terminal follow the same graceful shutdown path.
        try:
            window._on_exit()
        except Exception:
            pass


if __name__ == "__main__":
    main()

