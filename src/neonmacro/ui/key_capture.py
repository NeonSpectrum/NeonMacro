from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

import customtkinter as ctk
import mouse

from ..core.hotkeys import _parse_hotkey

PROMPT_TEXT = "Press any key..."
PROMPT_NOTE_TEXT = "Press Enter to save, Esc to cancel"
CAPTURE_HINT_TEXT = "Key Capture Mode"

_SHIFTED_CHAR_TO_BASE: dict[str, str] = {
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

_KEYSYM_TO_TOKEN: dict[str, str] = {
    "space": "SPACE",
    "Space": "SPACE",
    "Escape": "ESC",
    "Tab": "TAB",
    "Return": "ENTER",
    "BackSpace": "BACKSPACE",
    "Delete": "DELETE",
    "Insert": "INSERT",
    "Home": "HOME",
    "End": "END",
    "Prior": "PAGEUP",
    "Next": "PAGEDOWN",
    "Print": "PRTSCN",
    "Pause": "PAUSE",
    "Caps_Lock": "CAPSLOCK",
    "Num_Lock": "NUMLOCK",
    "Scroll_Lock": "SCROLLLOCK",
    "Up": "UP",
    "Down": "DOWN",
    "Left": "LEFT",
    "Right": "RIGHT",
    "minus": "-",
    "equal": "=",
    "bracketleft": "[",
    "bracketright": "]",
    "backslash": "\\",
    "semicolon": ";",
    "apostrophe": "'",
    "grave": "`",
    "comma": ",",
    "period": ".",
    "slash": "/",
    "KP_Add": "+",
    "KP_Subtract": "-",
    "KP_Multiply": "*",
    "KP_Divide": "/",
    "KP_Decimal": ".",
}

_KEYSYM_TO_BASE_TOKEN: dict[str, str] = {
    "exclam": "1",
    "at": "2",
    "numbersign": "3",
    "dollar": "4",
    "percent": "5",
    "asciicircum": "6",
    "ampersand": "7",
    "asterisk": "8",
    "parenleft": "9",
    "parenright": "0",
    "underscore": "-",
    "plus": "=",
    "braceleft": "[",
    "braceright": "]",
    "bar": "\\",
    "colon": ";",
    "quotedbl": "'",
    "less": ",",
    "greater": ".",
    "question": "/",
    "asciitilde": "`",
}

_MODIFIER_KEYSYMS: set[str] = {
    "Shift_L",
    "Shift_R",
    "Control_L",
    "Control_R",
    "Alt_L",
    "Alt_R",
    "Super_L",
    "Super_R",
    "Menu",
}

_SHIFT_MASK = 0x0001
_CONTROL_MASK = 0x0004
_ALT_MASK = 0x0008
_WIN_MASK = 0x0040


def attach_hotkey_capture(
    entry: ctk.CTkEntry,
    *,
    on_captured: Callable[[str], str] | None = None,
    allow_modifiers: bool = True,
    on_capture_state_changed: Callable[[bool], None] | None = None,
) -> None:
    state: dict[str, Any] = {"overlay": None}

    def _set_entry_value(value: str) -> None:
        entry.delete(0, tk.END)
        entry.insert(0, value)

    def _on_overlay_closed() -> None:
        state["overlay"] = None
        if on_capture_state_changed is not None:
            on_capture_state_changed(False)

    def _close_overlay() -> None:
        overlay = state.get("overlay")
        if overlay is None:
            return
        overlay.close()
        state["overlay"] = None

    def _begin_capture(_event=None):
        if state.get("overlay") is not None:
            return "break"
        owner = entry.winfo_toplevel()
        overlay = _KeyCaptureOverlay(
            owner=owner,
            initial_value=entry.get().strip(),
            on_cancel=lambda original: _set_entry_value(original),
            on_save=lambda captured: _set_entry_value(captured),
            on_transform=on_captured,
            allow_modifiers=allow_modifiers,
            on_close=_on_overlay_closed,
        )
        state["overlay"] = overlay
        if on_capture_state_changed is not None:
            on_capture_state_changed(True)
        overlay.open()
        return "break"

    def _close_capture(_event=None):
        _close_overlay()
        return None

    entry.bind("<FocusIn>", _begin_capture, add="+")
    entry.bind("<ButtonRelease-1>", _begin_capture, add="+")
    entry.bind("<Destroy>", _close_capture, add="+")


class _KeyCaptureOverlay:
    def __init__(
        self,
        *,
        owner: tk.Misc,
        initial_value: str,
        on_cancel: Callable[[str], None],
        on_save: Callable[[str], None],
        on_transform: Callable[[str], str] | None,
        allow_modifiers: bool,
        on_close: Callable[[], None],
    ) -> None:
        self._owner = owner
        self._initial_value = initial_value
        self._on_cancel = on_cancel
        self._on_save = on_save
        self._on_transform = on_transform
        self._allow_modifiers = allow_modifiers
        self._on_close = on_close
        self._captured_value = ""
        self._state: dict[str, bool] = {
            "ctrl_down": False,
            "alt_down": False,
            "shift_down": False,
            "win_down": False,
        }
        self._backdrop_frame: ctk.CTkFrame | None = None
        self._card_frame: ctk.CTkFrame | None = None
        self._prompt_label: ctk.CTkLabel | None = None
        self._captured_label: ctk.CTkLabel | None = None
        self._note_label: ctk.CTkLabel | None = None
        self._key_press_bind_id: str | None = None
        self._key_release_bind_id: str | None = None
        self._mouse_hook_handler: Callable[[mouse.ButtonEvent], None] | None = None
        self._current_card_width: int = 0

    def open(self) -> None:
        owner = self._owner.winfo_toplevel()
        owner.update_idletasks()
        self._key_press_bind_id = owner.bind("<KeyPress>", self._on_key_press, add="+")
        self._key_release_bind_id = owner.bind("<KeyRelease>", self._on_key_release, add="+")
        self._mouse_hook_handler = self._on_mouse_event
        mouse.hook(self._mouse_hook_handler)
        is_dialog_owner = isinstance(owner, ctk.CTkToplevel)
        backdrop_color = "transparent" if is_dialog_owner else ("#1E1E1E", "#121212")
        self._backdrop_frame = ctk.CTkFrame(
            owner,
            fg_color=backdrop_color,
            corner_radius=0,
        )
        self._backdrop_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._backdrop_frame.lift()
        self._backdrop_frame.bind("<Button-1>", self._on_backdrop_click, add="+")

        self._current_card_width = self._card_width(self._owner_width(owner))
        self._card_frame = ctk.CTkFrame(
            self._backdrop_frame,
            fg_color=("#2B2B2B", "#222222"),
            border_width=1,
            border_color=("#555555", "#4A4A4A"),
            width=self._current_card_width,
            height=220,
        )
        self._card_frame.place(relx=0.5, rely=0.5, anchor="center")
        self._card_frame.pack_propagate(False)
        self._card_frame.bind(
            "<ButtonPress-1>",
            lambda _event: self._capture_mouse_token("LMB"),
            add="+",
        )
        self._card_frame.bind(
            "<ButtonPress-2>",
            lambda _event: self._capture_mouse_token("MMB"),
            add="+",
        )
        self._card_frame.bind(
            "<ButtonPress-3>",
            lambda _event: self._capture_mouse_token("RMB"),
            add="+",
        )
        self._card_frame.bind(
            "<ButtonPress-4>",
            lambda _event: self._capture_mouse_token("MB4"),
            add="+",
        )
        self._card_frame.bind(
            "<ButtonPress-5>",
            lambda _event: self._capture_mouse_token("MB5"),
            add="+",
        )

        ctk.CTkLabel(
            self._card_frame,
            text=CAPTURE_HINT_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#CFCFCF", "#CFCFCF"),
        ).pack(padx=32, pady=(16, 6))
        self._prompt_label = ctk.CTkLabel(
            self._card_frame,
            text=PROMPT_TEXT,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=("#F5FAFF", "#F4F8FF"),
        )
        self._prompt_label.pack(padx=32, pady=(0, 10))
        self._captured_label = ctk.CTkLabel(
            self._card_frame,
            text="-",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=("#EDEDED", "#EDEDED"),
        )
        self._captured_label.pack(padx=32, pady=(0, 12))
        self._note_label = ctk.CTkLabel(
            self._card_frame,
            text=PROMPT_NOTE_TEXT,
            font=ctk.CTkFont(size=14),
            text_color=("#D0D0D0", "#D0D0D0"),
        )
        self._note_label.pack(padx=32, pady=(0, 12))
        for widget in (
            self._prompt_label,
            self._captured_label,
            self._note_label,
        ):
            if widget is None:
                continue
            widget.bind(
                "<ButtonPress-1>",
                lambda _event: self._capture_mouse_token("LMB"),
                add="+",
            )
            widget.bind(
                "<ButtonPress-2>",
                lambda _event: self._capture_mouse_token("MMB"),
                add="+",
            )
            widget.bind(
                "<ButtonPress-3>",
                lambda _event: self._capture_mouse_token("RMB"),
                add="+",
            )
            widget.bind(
                "<ButtonPress-4>",
                lambda _event: self._capture_mouse_token("MB4"),
                add="+",
            )
            widget.bind(
                "<ButtonPress-5>",
                lambda _event: self._capture_mouse_token("MB5"),
                add="+",
            )
        self._backdrop_frame.grab_set()
        self._backdrop_frame.focus_force()

    def close(self) -> None:
        try:
            owner = self._owner.winfo_toplevel()
            if self._key_press_bind_id is not None:
                owner.unbind("<KeyPress>", self._key_press_bind_id)
            if self._key_release_bind_id is not None:
                owner.unbind("<KeyRelease>", self._key_release_bind_id)
            if self._mouse_hook_handler is not None:
                mouse.unhook(self._mouse_hook_handler)
            if self._backdrop_frame is not None:
                try:
                    if self._backdrop_frame.grab_current() is self._backdrop_frame:
                        self._backdrop_frame.grab_release()
                except tk.TclError:
                    pass
            if self._backdrop_frame is not None and self._backdrop_frame.winfo_exists():
                self._backdrop_frame.destroy()
        finally:
            self._backdrop_frame = None
            self._card_frame = None
            self._prompt_label = None
            self._captured_label = None
            self._note_label = None
            self._key_press_bind_id = None
            self._key_release_bind_id = None
            self._mouse_hook_handler = None
            self._on_close()

    def _on_key_press(self, event: tk.Event) -> str:
        _update_modifier_state(self._state, str(event.keysym), is_down=True)
        keysym = str(event.keysym)
        if keysym == "Escape":
            self._on_cancel(self._initial_value)
            self.close()
            return "break"
        if keysym == "Return":
            if self._captured_value:
                self._on_save(self._captured_value)
                self.close()
            return "break"
        if keysym in _MODIFIER_KEYSYMS:
            return "break"

        captured = _format_hotkey(event, self._state, allow_modifiers=self._allow_modifiers)
        if not captured:
            return "break"
        value = self._on_transform(captured) if self._on_transform is not None else captured
        if not value:
            return "break"
        self._captured_value = value
        if self._captured_label is not None:
            self._captured_label.configure(text=value)
        return "break"

    def _on_key_release(self, event: tk.Event) -> str:
        _update_modifier_state(self._state, str(event.keysym), is_down=False)
        return "break"

    def _on_backdrop_click(self, _event=None) -> str:
        self._on_cancel(self._initial_value)
        self.close()
        return "break"

    def _on_mouse_event(self, event) -> None:
        if not isinstance(event, mouse.ButtonEvent):
            return
        if event.event_type != "down":
            return
        button_name = str(event.button)
        if button_name in {"left", "right", "middle"}:
            return
        token_map = {
            "x": "MB4",
            "x2": "MB5",
        }
        key_token = token_map.get(button_name)
        if not key_token:
            return
        owner = self._owner.winfo_toplevel()
        owner.after(0, lambda: self._capture_mouse_token(key_token))

    def _capture_mouse_token(self, key_token: str) -> None:
        modifiers: list[str] = []
        if self._allow_modifiers and self._state["ctrl_down"]:
            modifiers.append("CTRL")
        if self._allow_modifiers and self._state["alt_down"]:
            modifiers.append("ALT")
        if self._allow_modifiers and self._state["shift_down"]:
            modifiers.append("SHIFT")
        if self._allow_modifiers and self._state["win_down"]:
            modifiers.append("LWIN")
        captured = "+".join([*modifiers, key_token]) if modifiers else key_token
        value = self._on_transform(captured) if self._on_transform is not None else captured
        if not value:
            return
        self._captured_value = value
        if self._captured_label is not None:
            self._captured_label.configure(text=value)

    @staticmethod
    def _card_width(owner_width: int) -> int:
        horizontal_padding = 56
        min_width = 360
        max_width = 560
        return max(min_width, min(max_width, owner_width - horizontal_padding))

    @staticmethod
    def _owner_width(owner: tk.Misc) -> int:
        width = int(owner.winfo_width())
        if width > 1:
            return width
        return int(owner.winfo_reqwidth())



def format_hotkey_for_display(value: str) -> str:
    parsed = _parse_hotkey(value)
    if parsed is None:
        return value
    return "+".join([*parsed.modifiers, parsed.key_token])


def _format_hotkey(
    event: tk.Event,
    state: dict[str, Any],
    *,
    allow_modifiers: bool,
) -> str:
    key_token = _key_token_from_event(event)
    if not key_token:
        return ""

    modifiers: list[str] = []
    bitmask = int(getattr(event, "state", 0))
    if allow_modifiers and (state["ctrl_down"] or (bitmask & _CONTROL_MASK)):
        modifiers.append("CTRL")
    if allow_modifiers and (state["alt_down"] or (bitmask & _ALT_MASK)):
        modifiers.append("ALT")
    if allow_modifiers and (state["shift_down"] or (bitmask & _SHIFT_MASK)):
        modifiers.append("SHIFT")
    if allow_modifiers and (state["win_down"] or (bitmask & _WIN_MASK)):
        modifiers.append("LWIN")

    key_display = key_token
    if not modifiers:
        return key_display
    return "+".join([*modifiers, key_display])


def _update_modifier_state(state: dict[str, Any], keysym: str, *, is_down: bool) -> None:
    if keysym in {"Control_L", "Control_R"}:
        state["ctrl_down"] = is_down
    elif keysym in {"Alt_L", "Alt_R"}:
        state["alt_down"] = is_down
    elif keysym in {"Shift_L", "Shift_R"}:
        state["shift_down"] = is_down
    elif keysym in {"Super_L", "Super_R"}:
        state["win_down"] = is_down


def _key_token_from_event(event: tk.Event) -> str:
    keysym = str(getattr(event, "keysym", "") or "")
    if not keysym:
        return ""

    if keysym in _KEYSYM_TO_TOKEN:
        return _KEYSYM_TO_TOKEN[keysym]
    if keysym in _KEYSYM_TO_BASE_TOKEN:
        return _KEYSYM_TO_BASE_TOKEN[keysym]
    if keysym.startswith("F") and keysym[1:].isdigit():
        return keysym.upper()
    if keysym.startswith("KP_") and len(keysym) == 4 and keysym[3].isdigit():
        return keysym[3]
    if len(keysym) == 1 and keysym.isalnum():
        return keysym.upper()

    char = str(getattr(event, "char", "") or "")
    if not char:
        return ""
    if char in _SHIFTED_CHAR_TO_BASE:
        return _SHIFTED_CHAR_TO_BASE[char]
    if char.isalnum():
        return char.upper()
    return char if char in {"`", "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/"} else ""
