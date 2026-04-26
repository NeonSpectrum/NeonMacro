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
VK_SNAPSHOT = getattr(win32con, "VK_SNAPSHOT", 0x2C)
VK_PAUSE = getattr(win32con, "VK_PAUSE", 0x13)
VK_CAPITAL = getattr(win32con, "VK_CAPITAL", 0x14)
VK_NUMLOCK = getattr(win32con, "VK_NUMLOCK", 0x90)
VK_SCROLL = getattr(win32con, "VK_SCROLL", 0x91)
VK_CANCEL = getattr(win32con, "VK_CANCEL", 0x03)

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
    "PRTSCN": VK_SNAPSHOT,
    "PAUSE": VK_PAUSE,
    "CAPSLOCK": VK_CAPITAL,
    "NUMLOCK": VK_NUMLOCK,
    "SCROLLLOCK": VK_SCROLL,
    "BREAK": VK_PAUSE,
    "CTRLBREAK": VK_CANCEL,
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

HOTKEY_VK_BY_TOKEN: dict[str, int] = {
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
    "PRTSCN": VK_SNAPSHOT,
    "PAUSE": VK_PAUSE,
    "CAPSLOCK": VK_CAPITAL,
    "NUMLOCK": VK_NUMLOCK,
    "SCROLLLOCK": VK_SCROLL,
    "BREAK": VK_PAUSE,
    "CTRLBREAK": VK_CANCEL,
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
    "escape": "ESC",
    "return": "ENTER",
    "tab": "TAB",
    "backspace": "BACKSPACE",
    "space": "SPACE",
    "spacebar": "SPACE",
    "home": "HOME",
    "end": "END",
    "del": "DELETE",
    "delete": "DELETE",
    "ins": "INSERT",
    "insert": "INSERT",
    "pgup": "PAGEUP",
    "pageup": "PAGEUP",
    "pgdn": "PAGEDOWN",
    "pagedown": "PAGEDOWN",
    "prtscn": "PRTSCN",
    "printscreen": "PRTSCN",
    "pause": "PAUSE",
    "capslock": "CAPSLOCK",
    "numlock": "NUMLOCK",
    "scrolllock": "SCROLLLOCK",
    "break": "BREAK",
    "ctrlbreak": "CTRLBREAK",
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
