from __future__ import annotations

import ctypes
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

RESERVED_HOTKEYS: set[str] = {
    "ALT+TAB",
    "ALT+F4",
    "ALT+ESC",
    "CTRL+ALT+DELETE",
    "CTRL+SHIFT+ESC",
    "LWIN+D",
    "LWIN+L",
    "LWIN+R",
    "LWIN+TAB",
}

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_MOD_ALT = 0x0001
_MOD_CONTROL = 0x0002
_MOD_SHIFT = 0x0004
_MOD_WIN = 0x0008
_MAPVK_VK_TO_VSC = 0

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
        on_priority_pause_hotkey: Callable[[], None],
        on_settings_toggle_hotkey: Callable[[], None],
    ) -> None:
        self._on_profile_hotkey = on_profile_hotkey
        self._on_auto_stop_hotkey = on_auto_stop_hotkey
        self._on_priority_pause_hotkey = on_priority_pause_hotkey
        self._on_settings_toggle_hotkey = on_settings_toggle_hotkey
        self._registered_ids: list[int] = []
        self._registered_auto_stop_ids: list[int] = []
        self._registered_priority_pause_ids: list[int] = []
        self._registered_settings_hotkey_id: int | None = None
        self._registered_mouse_handlers: list[Callable] = []
        self._registered_auto_stop_mouse_handlers: list[Callable] = []
        self._registered_priority_pause_mouse_handlers: list[Callable] = []
        self._registered_priority_pause_keyboard_handlers: list[Callable] = []
        self._registered_profile_keyboard_handlers: list[Callable] = []
        self._registered_settings_keyboard_handlers: list[Callable] = []
        self._registered_settings_mouse_handlers: list[Callable] = []
        self._probe_hotkey_id = 0xA000
        self._hotkeys_enabled = True

    def set_enabled(self, enabled: bool) -> None:
        self._hotkeys_enabled = enabled

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
                self._register_keyboard_hook_hotkey(
                    parsed=parsed,
                    callback=lambda profile_name=profile.name: self._on_profile_hotkey(profile_name),
                    into=self._registered_profile_keyboard_handlers,
                )
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

    def apply_priority_pause_hotkeys(self, enabled: bool, pause_keys: list[str]) -> None:
        self._clear_priority_pause_hotkeys()
        if not enabled:
            return
        seen: set[str] = set()
        for pause_key in pause_keys:
            normalized = self._normalize_hotkey(pause_key)
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
                    callback=self._on_priority_pause_hotkey,
                    into=self._registered_priority_pause_mouse_handlers,
                )
            else:
                self._register_keyboard_hook_hotkey(
                    parsed=parsed,
                    callback=self._on_priority_pause_hotkey,
                    into=self._registered_priority_pause_keyboard_handlers,
                )
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
            self._register_mouse_hotkey(
                parsed=parsed,
                callback=self._on_settings_toggle_hotkey,
                into=self._registered_settings_mouse_handlers,
            )
        else:
            self._register_keyboard_hook_hotkey(
                parsed=parsed,
                callback=self._on_settings_toggle_hotkey,
                into=self._registered_settings_keyboard_handlers,
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
            if not self._hotkeys_enabled:
                return
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

    def _register_keyboard_hook_hotkey(
        self,
        *,
        parsed: ParsedHotkey,
        callback: Callable[[], None],
        into: list[Callable],
    ) -> None:
        expected_key = parsed.key_token.lower() if len(parsed.key_token) > 1 else parsed.key_token
        expected_scan_code = _scan_code_for_vk(HOTKEY_VK_BY_TOKEN.get(parsed.key_token))
        modifiers = set(parsed.modifiers)
        pressed = False

        def _handler(event) -> None:
            nonlocal pressed
            if not self._hotkeys_enabled:
                return
            if not isinstance(event, keyboard.KeyboardEvent):
                return
            event_name = (event.name or "").lower()
            event_scan_code = getattr(event, "scan_code", None)
            key_matches = event_name == expected_key or (
                expected_scan_code is not None and event_scan_code == expected_scan_code
            )
            if not key_matches:
                return
            if event.event_type == "up":
                pressed = False
                return
            if event.event_type != "down":
                return
            if pressed:
                return
            ctrl_down = keyboard.is_pressed("ctrl") or keyboard.is_pressed("right ctrl")
            rctrl_down = keyboard.is_pressed("right ctrl")
            alt_down = keyboard.is_pressed("alt") or keyboard.is_pressed("right alt")
            ralt_down = keyboard.is_pressed("right alt")
            shift_down = keyboard.is_pressed("shift") or keyboard.is_pressed("right shift")
            rshift_down = keyboard.is_pressed("right shift")
            lwin_down = keyboard.is_pressed("left windows")
            rwin_down = keyboard.is_pressed("right windows")
            apps_down = keyboard.is_pressed("apps")

            if ("CTRL" in modifiers) and not ctrl_down:
                return
            if ("RCTRL" in modifiers) and not rctrl_down:
                return
            if ("ALT" in modifiers) and not alt_down:
                return
            if ("RALT" in modifiers) and not ralt_down:
                return
            if ("SHIFT" in modifiers) and not shift_down:
                return
            if ("RSHIFT" in modifiers) and not rshift_down:
                return
            if ("LWIN" in modifiers) and not lwin_down:
                return
            if ("RWIN" in modifiers) and not rwin_down:
                return
            if ("APPS" in modifiers) and not apps_down:
                return

            # Enforce exact modifier intent so plain-key hotkeys don't fire while
            # CTRL/ALT/SHIFT/WIN/APPS are held for another hotkey.
            if ("CTRL" not in modifiers and "RCTRL" not in modifiers) and ctrl_down:
                return
            if ("ALT" not in modifiers and "RALT" not in modifiers) and alt_down:
                return
            if ("SHIFT" not in modifiers and "RSHIFT" not in modifiers) and shift_down:
                return
            if ("LWIN" not in modifiers and "RWIN" not in modifiers) and (lwin_down or rwin_down):
                return
            if ("APPS" not in modifiers) and apps_down:
                return
            pressed = True
            callback()

        keyboard.hook(_handler)
        into.append(_handler)

    def shutdown(self) -> None:
        self._clear_profile_hotkeys()
        self._clear_auto_stop_hotkeys()
        self._clear_priority_pause_hotkeys()
        self._clear_settings_toggle_hotkey()

    def _clear_profile_hotkeys(self) -> None:
        for hotkey_id in self._registered_ids:
            try:
                keyboard.remove_hotkey(hotkey_id)
            except KeyError:
                continue
        self._registered_ids.clear()
        for handler in self._registered_profile_keyboard_handlers:
            keyboard.unhook(handler)
        self._registered_profile_keyboard_handlers.clear()
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

    def _clear_priority_pause_hotkeys(self) -> None:
        for hotkey_id in self._registered_priority_pause_ids:
            try:
                keyboard.remove_hotkey(hotkey_id)
            except KeyError:
                continue
        self._registered_priority_pause_ids.clear()
        for handler in self._registered_priority_pause_keyboard_handlers:
            keyboard.unhook(handler)
        self._registered_priority_pause_keyboard_handlers.clear()
        for handler in self._registered_priority_pause_mouse_handlers:
            mouse.unhook(handler)
        self._registered_priority_pause_mouse_handlers.clear()

    def _clear_settings_toggle_hotkey(self) -> None:
        if self._registered_settings_hotkey_id is not None:
            try:
                keyboard.remove_hotkey(self._registered_settings_hotkey_id)
            except KeyError:
                pass
            self._registered_settings_hotkey_id = None
        for handler in self._registered_settings_keyboard_handlers:
            keyboard.unhook(handler)
        self._registered_settings_keyboard_handlers.clear()
        for handler in self._registered_settings_mouse_handlers:
            mouse.unhook(handler)
        self._registered_settings_mouse_handlers.clear()


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


def _parse_hotkey(raw: str) -> ParsedHotkey | None:
    value = raw.strip()
    if not value:
        return None
    parsed = _parse_plus_input(value)
    if parsed is None:
        return None
    modifiers_in, key_token, _key_braced_label, _key_is_braced = parsed
    seen: set[str] = set()
    modifiers: list[str] = []
    for modifier in MODIFIER_ORDER:
        if modifier in modifiers_in and modifier not in seen:
            modifiers.append(modifier)
            seen.add(modifier)
    if key_token in MODIFIER_TOKENS:
        return None
    canonical = "+".join([*modifiers, key_token]) if modifiers else key_token
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


def _parse_plus_input(raw: str) -> tuple[list[str], str, str | None, bool] | None:
    parts = [item.strip() for item in raw.split("+") if item.strip()]
    if not parts:
        return None
    modifiers: list[str] = []
    for token in parts[:-1]:
        modifier = _normalize_modifier_token(token)
        if modifier is None:
            return None
        modifiers.append(modifier)
    main_key_token = _normalize_key_token(parts[-1])
    if main_key_token is None:
        return None
    return modifiers, main_key_token, parts[-1], False


def _scan_code_for_vk(vk: int | None) -> int | None:
    if vk is None:
        return None
    scan_code = int(_USER32.MapVirtualKeyW(vk, _MAPVK_VK_TO_VSC))
    if scan_code <= 0:
        return None
    return scan_code
