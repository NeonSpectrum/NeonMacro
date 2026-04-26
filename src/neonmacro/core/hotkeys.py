from __future__ import annotations

import ctypes
import re
from collections.abc import Callable
from dataclasses import dataclass

import keyboard
import mouse

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

MODIFIER_TOKENS: set[str] = {
    "CTRL",
    "RCTRL",
    "ALT",
    "RALT",
    "SHIFT",
    "RSHIFT",
    "LWIN",
    "RWIN",
    "APPS",
}

MODIFIER_ORDER: list[str] = [
    "CTRL",
    "RCTRL",
    "ALT",
    "RALT",
    "SHIFT",
    "RSHIFT",
    "LWIN",
    "RWIN",
    "APPS",
]

MOUSE_BUTTON_ALIASES: dict[str, str] = {
    "LMB": "LMB",
    "LEFTMOUSEBUTTON": "LMB",
    "RMB": "RMB",
    "RIGHTMOUSEBUTTON": "RMB",
    "MMB": "MMB",
    "MIDDLEMOUSEBUTTON": "MMB",
    "MB4": "MB4",
    "MB5": "MB5",
}

MOUSE_BUTTON_NAMES: dict[str, str] = {
    "LMB": "left",
    "RMB": "right",
    "MMB": "middle",
    "MB4": "x",
    "MB5": "x2",
}

KEYBOARD_MODIFIER_ALIASES: dict[str, str] = {
    "CTRL": "ctrl",
    "RCTRL": "right ctrl",
    "ALT": "alt",
    "RALT": "right alt",
    "SHIFT": "shift",
    "RSHIFT": "right shift",
    "LWIN": "left windows",
    "RWIN": "right windows",
    "APPS": "apps",
}

_BRACED_TOKEN_PATTERN = re.compile(r"\{([^{}]+)\}")

RESERVED_HOTKEYS: set[str] = {
    "{ALT}{TAB}",
    "{ALT}{F4}",
    "{ALT}{ESC}",
    "{CTRL}{ALT}{DELETE}",
    "{CTRL}{SHIFT}{ESC}",
    "{LWIN}D",
    "{LWIN}L",
    "{LWIN}R",
    "{LWIN}{TAB}",
}

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_MOD_ALT = 0x0001
_MOD_CONTROL = 0x0002
_MOD_SHIFT = 0x0004
_MOD_WIN = 0x0008

REGISTER_HOTKEY_MODIFIERS: dict[str, int] = {
    "CTRL": _MOD_CONTROL,
    "ALT": _MOD_ALT,
    "SHIFT": _MOD_SHIFT,
    "LWIN": _MOD_WIN,
}


@dataclass(frozen=True)
class ParsedHotkey:
    modifiers: tuple[str, ...]
    key_token: str
    canonical: str
    keyboard_hotkey: str
    includes_mouse: bool


class HotkeyManager:
    def __init__(
        self,
        on_profile_hotkey: Callable[[str], None],
        on_auto_stop_hotkey: Callable[[], None],
        on_settings_toggle_hotkey: Callable[[], None],
    ) -> None:
        self._on_profile_hotkey = on_profile_hotkey
        self._on_auto_stop_hotkey = on_auto_stop_hotkey
        self._on_settings_toggle_hotkey = on_settings_toggle_hotkey
        self._registered_ids: list[int] = []
        self._registered_auto_stop_ids: list[int] = []
        self._registered_settings_hotkey_id: int | None = None
        self._registered_mouse_handlers: list[Callable] = []
        self._registered_auto_stop_mouse_handlers: list[Callable] = []
        self._probe_hotkey_id = 0xA000

    def apply_profile_hotkeys(self, profiles: list[SpamProfile]) -> None:
        self._clear_profile_hotkeys()
        seen: dict[str, str] = {}
        for profile in profiles:
            normalized = self._normalize_hotkey(profile.select_hotkey)
            if not normalized:
                continue
            parsed = _parse_hotkey(normalized)
            if parsed is None:
                raise ValueError(f"Hotkey '{profile.select_hotkey}' has invalid format.")
            if normalized in RESERVED_HOTKEYS:
                raise ValueError(
                    f"Hotkey '{profile.select_hotkey}' is reserved by Windows."
                )
            owner = seen.get(normalized)
            if owner is not None:
                raise ValueError(
                    f"Hotkey conflict in app: '{profile.select_hotkey}' is already used by '{owner}'."
                )
            if not self._can_bind_hotkey(parsed):
                raise ValueError(
                    f"Hotkey '{profile.select_hotkey}' cannot be bound. It may be invalid or already in use by Windows/another app."
                )
            if parsed.includes_mouse:
                self._register_mouse_hotkey(
                    parsed=parsed,
                    callback=lambda profile_name=profile.name: self._on_profile_hotkey(profile_name),
                    into=self._registered_mouse_handlers,
                )
            else:
                hotkey_id = keyboard.add_hotkey(
                    parsed.keyboard_hotkey,
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
            parsed = _parse_hotkey(normalized)
            if parsed is None:
                continue
            if parsed.includes_mouse:
                self._register_mouse_hotkey(
                    parsed=parsed,
                    callback=self._on_auto_stop_hotkey,
                    into=self._registered_auto_stop_mouse_handlers,
                )
            else:
                hotkey_id = keyboard.add_hotkey(
                    parsed.keyboard_hotkey,
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
        parsed = _parse_hotkey(normalized)
        if parsed is None:
            return False
        return self._can_bind_hotkey(parsed)

    def apply_settings_toggle_hotkey(self, hotkey: str) -> str:
        self._clear_settings_toggle_hotkey()
        normalized = self._normalize_hotkey(hotkey)
        if not normalized:
            raise ValueError("Settings overlay hotkey format is invalid.")
        if normalized in RESERVED_HOTKEYS:
            raise ValueError("Settings overlay hotkey is reserved by Windows.")
        parsed = _parse_hotkey(normalized)
        if parsed is None:
            raise ValueError("Settings overlay hotkey format is invalid.")
        if not self._can_bind_hotkey(parsed):
            raise ValueError(
                "Settings overlay hotkey cannot be bound. It may already be in use."
            )
        if parsed.includes_mouse:
            raise ValueError("Settings overlay hotkey must use a keyboard key.")
        self._registered_settings_hotkey_id = keyboard.add_hotkey(
            parsed.keyboard_hotkey,
            self._on_settings_toggle_hotkey,
            suppress=False,
        )
        return normalized

    def _normalize_hotkey(self, hotkey: str) -> str:
        parsed = _parse_hotkey(hotkey)
        if parsed is None:
            return ""
        return parsed.canonical

    def _can_bind_hotkey(self, parsed: ParsedHotkey) -> bool:
        if parsed.includes_mouse:
            return True
        register_parts = self._parse_for_register_hotkey(parsed)
        if register_parts is None:
            return False
        modifiers, vk = register_parts
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

    def _parse_for_register_hotkey(self, parsed: ParsedHotkey) -> tuple[int, int] | None:
        modifiers = 0
        for modifier in parsed.modifiers:
            mod_value = REGISTER_HOTKEY_MODIFIERS.get(modifier)
            if mod_value is None:
                return None
            modifiers |= mod_value
        vk = HOTKEY_VK_BY_TOKEN.get(parsed.key_token)
        if vk is None:
            return None
        return modifiers, vk

    def _register_mouse_hotkey(
        self,
        *,
        parsed: ParsedHotkey,
        callback: Callable[[], None],
        into: list[Callable],
    ) -> None:
        button = MOUSE_BUTTON_NAMES.get(parsed.key_token)
        if button is None:
            raise ValueError(f"Unsupported mouse button in hotkey '{parsed.canonical}'.")
        modifiers = [KEYBOARD_MODIFIER_ALIASES[item] for item in parsed.modifiers]

        def _handler(event) -> None:
            if not isinstance(event, mouse.ButtonEvent):
                return
            if event.event_type != "down":
                return
            if event.button != button:
                return
            if not all(keyboard.is_pressed(modifier_key) for modifier_key in modifiers):
                return
            callback()

        mouse.hook(_handler)
        into.append(_handler)

    def shutdown(self) -> None:
        self._clear_profile_hotkeys()
        self._clear_auto_stop_hotkeys()
        self._clear_settings_toggle_hotkey()

    def _clear_profile_hotkeys(self) -> None:
        for hotkey_id in self._registered_ids:
            try:
                keyboard.remove_hotkey(hotkey_id)
            except KeyError:
                continue
        self._registered_ids.clear()
        for handler in self._registered_mouse_handlers:
            mouse.unhook(handler)
        self._registered_mouse_handlers.clear()

    def _clear_auto_stop_hotkeys(self) -> None:
        for hotkey_id in self._registered_auto_stop_ids:
            try:
                keyboard.remove_hotkey(hotkey_id)
            except KeyError:
                continue
        self._registered_auto_stop_ids.clear()
        for handler in self._registered_auto_stop_mouse_handlers:
            mouse.unhook(handler)
        self._registered_auto_stop_mouse_handlers.clear()

    def _clear_settings_toggle_hotkey(self) -> None:
        if self._registered_settings_hotkey_id is not None:
            try:
                keyboard.remove_hotkey(self._registered_settings_hotkey_id)
            except KeyError:
                pass
            self._registered_settings_hotkey_id = None


def _normalize_modifier_token(token: str) -> str | None:
    compact = token.strip().replace(" ", "").upper()
    mapping = {
        "CTRL": "CTRL",
        "CONTROL": "CTRL",
        "RCTRL": "RCTRL",
        "RIGHTCTRL": "RCTRL",
        "ALT": "ALT",
        "RALT": "RALT",
        "RIGHTALT": "RALT",
        "SHIFT": "SHIFT",
        "RSHIFT": "RSHIFT",
        "RIGHTSHIFT": "RSHIFT",
        "LWIN": "LWIN",
        "WIN": "LWIN",
        "WINDOWS": "LWIN",
        "RWIN": "RWIN",
        "RIGHTWIN": "RWIN",
        "APPS": "APPS",
        "MENU": "APPS",
    }
    return mapping.get(compact)


def _normalize_key_token(token: str) -> str | None:
    value = token.strip()
    if not value:
        return None
    compact = value.replace(" ", "")
    upper = compact.upper()
    if upper in MOUSE_BUTTON_ALIASES:
        return MOUSE_BUTTON_ALIASES[upper]
    alias = SYMBOL_ALIASES.get(compact.lower())
    if alias is not None:
        compact = alias
        upper = compact.upper()
    if len(compact) == 1:
        return compact.upper() if compact.isalnum() else compact
    if upper in HOTKEY_VK_BY_TOKEN:
        return upper
    return None


def _parse_braced_input(raw: str) -> tuple[list[str], str, str | None, bool] | None:
    index = 0
    modifiers: list[str] = []
    main_key: str | None = None
    main_key_braced_label: str | None = None
    main_key_is_braced = False
    while index < len(raw):
        char = raw[index]
        if char.isspace():
            index += 1
            continue
        if char == "{":
            match = _BRACED_TOKEN_PATTERN.match(raw, index)
            if match is None:
                return None
            token = match.group(1).strip()
            modifier = _normalize_modifier_token(token)
            if modifier is not None:
                if main_key is not None:
                    return None
                modifiers.append(modifier)
            else:
                key_token = _normalize_key_token(token)
                if key_token is None or main_key is not None:
                    return None
                main_key = key_token
                main_key_braced_label = token
                main_key_is_braced = True
            index = match.end()
            continue
        key_token = _normalize_key_token(char)
        if key_token is None or main_key is not None:
            return None
        main_key = key_token
        main_key_braced_label = char
        main_key_is_braced = False
        index += 1
    if main_key is None:
        return None
    return modifiers, main_key, main_key_braced_label, main_key_is_braced


def _parse_hotkey(raw: str) -> ParsedHotkey | None:
    value = raw.strip()
    if not value:
        return None
    parsed = _parse_braced_input(value)
    if parsed is None:
        return None
    modifiers_in, key_token, key_braced_label, key_is_braced = parsed
    seen: set[str] = set()
    modifiers: list[str] = []
    for modifier in MODIFIER_ORDER:
        if modifier in modifiers_in and modifier not in seen:
            modifiers.append(modifier)
            seen.add(modifier)
    if key_token in MODIFIER_TOKENS:
        return None
    if key_braced_label is not None:
        key_display = f"{{{key_braced_label}}}" if key_is_braced else key_braced_label
    else:
        key_display = (
            f"{{{key_token}}}"
            if len(key_token) > 1 and key_token not in MOUSE_BUTTON_ALIASES
            else (f"{{{key_token}}}" if key_token in MOUSE_BUTTON_NAMES else key_token)
        )
    canonical = "".join(f"{{{item}}}" for item in modifiers) + key_display
    keyboard_parts = [KEYBOARD_MODIFIER_ALIASES[item] for item in modifiers]
    if key_token in MOUSE_BUTTON_NAMES:
        keyboard_hotkey = "+".join(keyboard_parts + [key_token.lower()])
        includes_mouse = True
    else:
        keyboard_key = key_token.lower() if len(key_token) > 1 else key_token
        keyboard_hotkey = "+".join([*keyboard_parts, keyboard_key])
        includes_mouse = False
    return ParsedHotkey(
        modifiers=tuple(modifiers),
        key_token=key_token,
        canonical=canonical,
        keyboard_hotkey=keyboard_hotkey,
        includes_mouse=includes_mouse,
    )
