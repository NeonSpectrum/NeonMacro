from __future__ import annotations

import logging
import sys
from pathlib import Path

import winreg

logger = logging.getLogger(__name__)

_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE_NAME = "NeonMacro"


def sync_run_on_startup(enabled: bool, *, launch_silent: bool = False) -> None:
    command = _build_startup_command(launch_silent=launch_silent)
    if not command:
        logger.warning("Startup registration skipped: unable to determine launch command.")
        return
    if enabled:
        _set_run_key_value(command)
        return
    _remove_run_key_value()


def _build_startup_command(*, launch_silent: bool) -> str:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable)
        command = _quote(executable)
        if launch_silent:
            command = f"{command} --silent"
        return command
    executable = Path(sys.executable)
    app_entry = Path(__file__).resolve().parents[1] / "app.py"
    if not executable.exists() or not app_entry.exists():
        return ""
    command = f"{_quote(executable)} {_quote(app_entry)}"
    if launch_silent:
        command = f"{command} --silent"
    return command


def _set_run_key_value(command: str) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        _RUN_KEY_PATH,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, _RUN_VALUE_NAME, 0, winreg.REG_SZ, command)


def _remove_run_key_value() -> None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, _RUN_VALUE_NAME)
    except FileNotFoundError:
        return


def _quote(path: Path) -> str:
    return f'"{path}"'
