from __future__ import annotations

from .keycodes import KEY_ALIASES, MODIFIER_BY_TOKEN, VK_BY_KEY

SPAM_MOUSE_ALIASES: dict[str, str] = {
    "lmb": "LMB",
    "rmb": "RMB",
    "mmb": "MMB",
    "mb4": "MB4",
    "mb5": "MB5",
}

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
    main_key: str | None = None
    for part in parts:
        if part.startswith("{") and part.endswith("}") and len(part) >= 3:
            part = part[1:-1].strip()
        lowered = part.lower()
        compact = lowered.replace(" ", "")
        modifier_vk = MODIFIER_BY_TOKEN.get(lowered)
        if modifier_vk is None:
            modifier_vk = MODIFIER_BY_TOKEN.get(compact)
        if modifier_vk is not None:
            raise ValueError("Spam key cannot use modifiers/combinations. Use a single key only (example: F1 or A).")
        mouse_alias = SPAM_MOUSE_ALIASES.get(compact)
        if mouse_alias is not None:
            if main_key is not None:
                raise ValueError("Use only one spam key (example: F1 or A).")
            main_key = mouse_alias
            continue
        normalized = KEY_ALIASES.get(lowered, part)
        normalized = normalized.upper() if normalized.isalnum() else normalized
        if normalized not in VK_BY_KEY:
            raise ValueError(f"Unsupported spam key token '{part}'.")
        if main_key is not None:
            raise ValueError("Use only one spam key (example: F1 or A).")
        main_key = normalized
    if main_key is None:
        raise ValueError("A spam key is required (example: F1 or A).")
    if main_key in {"LMB", "RMB", "MMB", "MB4", "MB5"}:
        canonical = f"{{{main_key}}}"
        return canonical, []
    if main_key.startswith("F") and main_key[1:].isdigit():
        canonical = f"{{{main_key}}}"
    else:
        canonical = main_key
    main_vk = VK_BY_KEY.get(main_key)
    if main_vk is None:
        raise ValueError(f"Unsupported spam key token '{main_key}'.")
    return canonical, [main_vk]
