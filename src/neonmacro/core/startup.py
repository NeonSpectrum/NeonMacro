from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import winreg

from .runtime import is_packaged_runtime

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


def read_run_on_startup_state() -> tuple[bool, bool]:
    command = _read_run_key_value()
    if not command:
        return False, False
    return True, _command_has_silent_flag(command)


def _build_startup_command(*, launch_silent: bool) -> str:
    if is_packaged_runtime():
        executable = _resolve_runtime_executable()
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
    with winreg.CreateKeyEx(
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


def _read_run_key_value() -> str:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_KEY_PATH,
            0,
            winreg.KEY_READ,
        ) as key:
            value, _value_type = winreg.QueryValueEx(key, _RUN_VALUE_NAME)
            return str(value).strip()
    except FileNotFoundError:
        return ""


def _command_has_silent_flag(command: str) -> bool:
    return re.search(r"(^|\s)--silent(\s|$)", command, flags=re.IGNORECASE) is not None


def _resolve_runtime_executable() -> Path:
    # For compiled onefile runtimes, sys.executable can point at a transient
    # extracted payload. Prefer argv[0], which usually preserves the launcher path.
    candidate_paths: list[Path] = []
    if sys.argv:
        candidate_paths.append(Path(sys.argv[0]))
    candidate_paths.append(Path(sys.executable))

    for candidate in candidate_paths:
        normalized = candidate.expanduser().resolve(strict=False)
        if normalized.suffix.lower() != ".exe":
            continue
        if normalized.exists():
            return normalized

    fallback = Path(sys.argv[0]) if sys.argv else Path(sys.executable)
    return fallback.expanduser().resolve(strict=False)


def _quote(path: Path) -> str:
    return f'"{path}"'
