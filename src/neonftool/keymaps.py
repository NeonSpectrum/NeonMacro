from __future__ import annotations

import win32con

VK_OEM_1 = getattr(win32con, "VK_OEM_1", 0xBA)
VK_OEM_PLUS = getattr(win32con, "VK_OEM_PLUS", 0xBB)
VK_OEM_COMMA = getattr(win32con, "VK_OEM_COMMA", 0xBC)
VK_OEM_MINUS = getattr(win32con, "VK_OEM_MINUS", 0xBD)
VK_OEM_PERIOD = getattr(win32con, "VK_OEM_PERIOD", 0xBE)
VK_OEM_2 = getattr(win32con, "VK_OEM_2", 0xBF)
VK_OEM_3 = getattr(win32con, "VK_OEM_3", 0xC0)
VK_OEM_4 = getattr(win32con, "VK_OEM_4", 0xDB)
VK_OEM_5 = getattr(win32con, "VK_OEM_5", 0xDC)
VK_OEM_6 = getattr(win32con, "VK_OEM_6", 0xDD)
VK_OEM_7 = getattr(win32con, "VK_OEM_7", 0xDE)

VK_BY_KEY: dict[str, int] = {
    **{str(n): ord(str(n)) for n in range(10)},
    **{chr(code): code for code in range(ord("A"), ord("Z") + 1)},
    **{f"F{n}": getattr(win32con, f"VK_F{n}") for n in range(1, 25)},
    "TAB": win32con.VK_TAB,
    "ENTER": win32con.VK_RETURN,
    "ESC": win32con.VK_ESCAPE,
    "SPACE": win32con.VK_SPACE,
    "BACKSPACE": win32con.VK_BACK,
    "DELETE": win32con.VK_DELETE,
    "INSERT": win32con.VK_INSERT,
    "HOME": win32con.VK_HOME,
    "END": win32con.VK_END,
    "PAGEUP": win32con.VK_PRIOR,
    "PAGEDOWN": win32con.VK_NEXT,
    "UP": win32con.VK_UP,
    "DOWN": win32con.VK_DOWN,
    "LEFT": win32con.VK_LEFT,
    "RIGHT": win32con.VK_RIGHT,
    "`": VK_OEM_3,
    "-": VK_OEM_MINUS,
    "=": VK_OEM_PLUS,
    "[": VK_OEM_4,
    "]": VK_OEM_6,
    "\\": VK_OEM_5,
    ";": VK_OEM_1,
    "'": VK_OEM_7,
    ",": VK_OEM_COMMA,
    ".": VK_OEM_PERIOD,
    "/": VK_OEM_2,
    "NUMPAD0": win32con.VK_NUMPAD0,
    "NUMPAD1": win32con.VK_NUMPAD1,
    "NUMPAD2": win32con.VK_NUMPAD2,
    "NUMPAD3": win32con.VK_NUMPAD3,
    "NUMPAD4": win32con.VK_NUMPAD4,
    "NUMPAD5": win32con.VK_NUMPAD5,
    "NUMPAD6": win32con.VK_NUMPAD6,
    "NUMPAD7": win32con.VK_NUMPAD7,
    "NUMPAD8": win32con.VK_NUMPAD8,
    "NUMPAD9": win32con.VK_NUMPAD9,
}

MODIFIER_BY_TOKEN: dict[str, int] = {
    "ctrl": win32con.VK_CONTROL,
    "control": win32con.VK_CONTROL,
    "lctrl": win32con.VK_CONTROL,
    "rctrl": win32con.VK_CONTROL,
    "alt": win32con.VK_MENU,
    "lalt": win32con.VK_MENU,
    "ralt": win32con.VK_MENU,
    "shift": win32con.VK_SHIFT,
    "lshift": win32con.VK_SHIFT,
    "rshift": win32con.VK_SHIFT,
    "win": win32con.VK_LWIN,
    "windows": win32con.VK_LWIN,
    "cmd": win32con.VK_LWIN,
}

KEY_ALIASES: dict[str, str] = {
    "esc": "ESC",
    "return": "ENTER",
    "spacebar": "SPACE",
    "del": "DELETE",
    "ins": "INSERT",
    "pgup": "PAGEUP",
    "pgdn": "PAGEDOWN",
    "plus": "=",
    "minus": "-",
    "underscore": "-",
    "equal": "=",
    "equals": "=",
    "comma": ",",
    "period": ".",
    "dot": ".",
    "slash": "/",
    "backslash": "\\",
    "semicolon": ";",
    "quote": "'",
    "apostrophe": "'",
    "backtick": "`",
    "grave": "`",
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

