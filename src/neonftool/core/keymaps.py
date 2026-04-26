from __future__ import annotations

import win32con

from .keycodes import KEY_ALIASES, MODIFIER_BY_TOKEN, VK_BY_KEY

SHIFTED_SYMBOL_TO_BASE: dict[str, str] = {
    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
    "_": "-",
    "+": "=",
    "{": "[",
    "}": "]",
    "|": "\\",
    ":": ";",
    '"': "'",
    "<": ",",
    ">": ".",
    "?": "/",
    "~": "`",
}

SPAM_KEYS = list(VK_BY_KEY.keys())


def normalize_spam_key_combo(raw: str) -> tuple[str, list[int]]:
    normalized_raw = raw.replace("＋", "+").strip()
    parts = [item.strip() for item in normalized_raw.split("+") if item.strip()]
    if not parts:
        raise ValueError("Spam key is required.")
    if len(parts) > 1:
        raise ValueError("Spam key cannot use modifiers/combinations. Use a single key only (example: F1 or A).")
    modifiers: list[int] = []
    seen_modifiers: set[int] = set()
    main_key: str | None = None
    for part in parts:
        lowered = part.lower()
        compact = lowered.replace(" ", "")
        modifier_vk = MODIFIER_BY_TOKEN.get(lowered)
        if modifier_vk is None:
            modifier_vk = MODIFIER_BY_TOKEN.get(compact)
        if modifier_vk is not None:
            raise ValueError("Spam key cannot use modifiers/combinations. Use a single key only (example: F1 or A).")
        normalized = KEY_ALIASES.get(lowered, part)
        normalized = normalized.upper() if normalized.isalnum() else normalized
        if normalized not in VK_BY_KEY:
            raise ValueError(f"Unsupported spam key token '{part}'.")
        if main_key is not None:
            raise ValueError("Use only one spam key (example: F1 or A).")
        main_key = normalized
    if main_key is None:
        raise ValueError("A spam key is required (example: F1 or A).")
    canonical_mods: list[str] = []
    for vk in modifiers:
        if vk == win32con.VK_CONTROL:
            canonical_mods.append("CTRL")
        elif vk == win32con.VK_MENU:
            canonical_mods.append("ALT")
        elif vk == win32con.VK_SHIFT:
            canonical_mods.append("SHIFT")
        elif vk in {win32con.VK_LWIN, win32con.VK_RWIN}:
            canonical_mods.append("WIN")
    canonical = "+".join([*canonical_mods, main_key])
    main_vk = VK_BY_KEY.get(main_key)
    if main_vk is None:
        raise ValueError(f"Unsupported spam key token '{main_key}'.")
    return canonical, [*modifiers, main_vk]
