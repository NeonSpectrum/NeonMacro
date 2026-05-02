from __future__ import annotations

from .hotkeys import _parse_hotkey
from .keycodes import MODIFIER_BY_TOKEN, VK_BY_KEY


def normalize_spam_key_combo(raw: str) -> tuple[str, list[int]]:
    parsed = _parse_hotkey(raw)
    if parsed is None:
        raise ValueError("Spam key format is invalid.")
    if parsed.modifiers:
        raise ValueError("Spam key must be a single key without modifiers.")

    if parsed.key_token in {"LMB", "RMB", "MMB", "MB4", "MB5"}:
        return parsed.canonical, []

    sequence: list[int] = []
    modifier_vk_by_token = {
        "CTRL": MODIFIER_BY_TOKEN["ctrl"],
        "RCTRL": MODIFIER_BY_TOKEN["rctrl"],
        "ALT": MODIFIER_BY_TOKEN["alt"],
        "RALT": MODIFIER_BY_TOKEN["ralt"],
        "SHIFT": MODIFIER_BY_TOKEN["shift"],
        "RSHIFT": MODIFIER_BY_TOKEN["rshift"],
        "LWIN": MODIFIER_BY_TOKEN["win"],
        "RWIN": 0x5C,
        "APPS": 0x5D,
    }
    for token in parsed.modifiers:
        modifier_vk = modifier_vk_by_token.get(token)
        if modifier_vk is None:
            raise ValueError(f"Unsupported spam modifier '{token}'.")
        sequence.append(modifier_vk)

    main_vk = VK_BY_KEY.get(parsed.key_token)
    if main_vk is None:
        raise ValueError(f"Unsupported spam key token '{parsed.key_token}'.")
    sequence.append(main_vk)
    return parsed.canonical, sequence
