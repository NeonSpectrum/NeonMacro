from __future__ import annotations

import ctypes
import sys
from pathlib import Path

import customtkinter as ctk
import win32con
import win32gui

from .core.logging_setup import configure_logging
from .ui.main_window import MainWindow

_ERROR_ALREADY_EXISTS = 183
_SINGLE_INSTANCE_MUTEX_NAME = "Local\\NeonSpectrum.NeonMacro.SingleInstance"
_MAIN_WINDOW_TITLE = "NeonMacro"


def config_path() -> Path:
    base = Path.home() / "AppData" / "Local" / "NeonMacro"
    return base / "config.json"


def _set_windows_app_user_model_id() -> None:
    # Helps Windows taskbar use this app identity/icon instead of fallback defaults.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "NeonSpectrum.NeonMacro"
        )
    except (AttributeError, OSError):
        pass


def _acquire_single_instance_mutex() -> int | None:
    try:
        handle = ctypes.windll.kernel32.CreateMutexW(
            None,
            False,
            _SINGLE_INSTANCE_MUTEX_NAME,
        )
    except (AttributeError, OSError):
        return None
    if not handle:
        return None
    if ctypes.GetLastError() == _ERROR_ALREADY_EXISTS:
        ctypes.windll.kernel32.CloseHandle(handle)
        return None
    return int(handle)


def _focus_existing_instance() -> None:
    hwnd = win32gui.FindWindow(None, _MAIN_WINDOW_TITLE)
    if not hwnd:
        return
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(hwnd)
    except win32gui.error:
        # If focus-stealing restrictions block activation, fail silently.
        return


def main() -> None:
    launch_silent = "--silent" in sys.argv[1:]
    mutex_handle = _acquire_single_instance_mutex()
    if mutex_handle is None:
        _focus_existing_instance()
        return
    configure_logging(config_path().parent / "debug.log")
    _set_windows_app_user_model_id()
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    window = MainWindow(config_path=config_path(), launch_silent=launch_silent)
    try:
        window.mainloop()
    except KeyboardInterrupt:
        # Let Ctrl+C in terminal follow the same graceful shutdown path.
        try:
            window._on_exit()
        except Exception:
            pass
    finally:
        ctypes.windll.kernel32.CloseHandle(mutex_handle)


if __name__ == "__main__":
    main()

