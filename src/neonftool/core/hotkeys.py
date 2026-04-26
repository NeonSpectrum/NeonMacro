from __future__ import annotations

import ctypes
from collections.abc import Callable

import keyboard

from ..models import SpamProfile
from .keycodes import HOTKEY_VK_BY_TOKEN

SYMBOL_ALIASES: dict[str, str] = {
    "backtick": "`",
    "grave": "`",
    "graveaccent": "`",
    "tilde": "~",
    "minus": "-",
    "dash": "-",
    "equals": "=",
    "equal": "=",
    "plus": "+",
    "comma": ",",
    "period": ".",
    "dot": ".",
    "slash": "/",
    "backslash": "\\",
    "semicolon": ";",
    "quote": "'",
    "apostrophe": "'",
    "openbracket": "[",
    "leftbracket": "[",
    "closebracket": "]",
    "rightbracket": "]",
}

SHORTHAND_MODIFIERS: dict[str, str] = {
    "!": "alt",
    "^": "ctrl",
    "+": "shift",
    "#": "win",
}

RESERVED_HOTKEYS: set[str] = {
    "alt+tab",
    "alt+f4",
    "alt+esc",
    "ctrl+alt+delete",
    "ctrl+shift+esc",
    "win+d",
    "win+l",
    "win+r",
    "win+tab",
}

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_MOD_ALT = 0x0001
_MOD_CONTROL = 0x0002
_MOD_SHIFT = 0x0004
_MOD_WIN = 0x0008


class HotkeyManager:
    def __init__(
        self,
        on_profile_hotkey: Callable[[str], None],
        on_auto_stop_hotkey: Callable[[], None],
    ) -> None:
        self._on_profile_hotkey = on_profile_hotkey
        self._on_auto_stop_hotkey = on_auto_stop_hotkey
        self._registered_ids: list[int] = []
        self._registered_auto_stop_ids: list[int] = []
        self._probe_hotkey_id = 0xA000

    def apply_profile_hotkeys(self, profiles: list[SpamProfile]) -> None:
        self._clear_profile_hotkeys()
        seen: dict[str, str] = {}
        for profile in profiles:
            normalized = self._normalize_hotkey(profile.select_hotkey)
            if not normalized:
                continue
            if normalized in RESERVED_HOTKEYS:
                raise ValueError(
                    f"Hotkey '{profile.select_hotkey}' is reserved by Windows."
                )
            owner = seen.get(normalized)
            if owner is not None:
                raise ValueError(
                    f"Hotkey conflict in app: '{profile.select_hotkey}' is already used by '{owner}'."
                )
            if not self._can_bind_hotkey(normalized):
                raise ValueError(
                    f"Hotkey '{profile.select_hotkey}' cannot be bound. It may be invalid or already in use by Windows/another app."
                )
            hotkey_id = keyboard.add_hotkey(
                normalized,
                lambda profile_name=profile.name: self._on_profile_hotkey(profile_name),
                suppress=False,
            )
            self._registered_ids.append(hotkey_id)
            seen[normalized] = profile.name

    def normalize_hotkey(self, hotkey: str) -> str:
        return self._normalize_hotkey(hotkey)

    def apply_auto_stop_hotkeys(self, enabled: bool, stop_keys: list[str]) -> None:
        self._clear_auto_stop_hotkeys()
        if not enabled:
            return
        seen: set[str] = set()
        for stop_key in stop_keys:
            normalized = self._normalize_hotkey(stop_key)
            if not normalized or normalized in RESERVED_HOTKEYS:
                continue
            if normalized in seen:
                continue
            hotkey_id = keyboard.add_hotkey(
                normalized,
                self._on_auto_stop_hotkey,
                suppress=False,
            )
            self._registered_auto_stop_ids.append(hotkey_id)
            seen.add(normalized)

    def can_bind_hotkey(self, hotkey: str) -> bool:
        normalized = self._normalize_hotkey(hotkey)
        if not normalized:
            return False
        if normalized in RESERVED_HOTKEYS:
            return False
        return self._can_bind_hotkey(normalized)

    def _normalize_hotkey(self, hotkey: str) -> str:
        raw = hotkey.strip().lower()
        if not raw:
            return ""
        expanded: list[str] = []
        current = raw
        while current and current[0] in SHORTHAND_MODIFIERS:
            expanded.append(SHORTHAND_MODIFIERS[current[0]])
            current = current[1:].strip()
        if current:
            expanded.append(current)
        normalized_input = "+".join(expanded) if expanded else raw
        parts = [part.strip().lower() for part in normalized_input.split("+") if part.strip()]
        if not parts:
            return ""
        normalized_parts: list[str] = []
        for part in parts:
            compact = part.replace(" ", "")
            normalized_parts.append(SYMBOL_ALIASES.get(compact, part))
        return "+".join(normalized_parts)

    def _can_bind_hotkey(self, normalized_hotkey: str) -> bool:
        parsed = self._parse_for_register_hotkey(normalized_hotkey)
        if parsed is None:
            return False
        modifiers, vk = parsed
        test_id = self._next_probe_hotkey_id()
        ok = bool(_USER32.RegisterHotKey(None, test_id, modifiers, vk))
        if ok:
            _USER32.UnregisterHotKey(None, test_id)
        return ok

    def _next_probe_hotkey_id(self) -> int:
        self._probe_hotkey_id += 1
        if self._probe_hotkey_id > 0xBFFF:
            self._probe_hotkey_id = 0xA000
        return self._probe_hotkey_id

    def _parse_for_register_hotkey(self, normalized_hotkey: str) -> tuple[int, int] | None:
        parts = [part.strip().upper() for part in normalized_hotkey.split("+") if part.strip()]
        if not parts:
            return None
        modifiers = 0
        key_token: str | None = None
        for part in parts:
            if part == "CTRL":
                modifiers |= _MOD_CONTROL
            elif part == "ALT":
                modifiers |= _MOD_ALT
            elif part == "SHIFT":
                modifiers |= _MOD_SHIFT
            elif part == "WIN":
                modifiers |= _MOD_WIN
            else:
                if key_token is not None:
                    return None
                key_token = part
        if key_token is None:
            return None
        vk = HOTKEY_VK_BY_TOKEN.get(key_token)
        if vk is None:
            return None
        return modifiers, vk

    def shutdown(self) -> None:
        self._clear_profile_hotkeys()
        self._clear_auto_stop_hotkeys()

    def _clear_profile_hotkeys(self) -> None:
        for hotkey_id in self._registered_ids:
            try:
                keyboard.remove_hotkey(hotkey_id)
            except KeyError:
                continue
        self._registered_ids.clear()

    def _clear_auto_stop_hotkeys(self) -> None:
        for hotkey_id in self._registered_auto_stop_ids:
            try:
                keyboard.remove_hotkey(hotkey_id)
            except KeyError:
                continue
        self._registered_auto_stop_ids.clear()
