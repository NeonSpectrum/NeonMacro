from __future__ import annotations

import ctypes
import tkinter.font as tkfont
from typing import Callable

import customtkinter as ctk

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_HWND_TOPMOST = -1
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOACTIVATE = 0x0010
_SWP_SHOWWINDOW = 0x0040
_SWP_FRAMECHANGED = 0x0020
_GWL_EXSTYLE = -20
_WS_EX_TRANSPARENT = 0x00000020
_WS_EX_LAYERED = 0x00080000
_WS_EX_TOOLWINDOW = 0x00000080
_WS_EX_APPWINDOW = 0x00040000


class OverlayWindow(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTk,
        x: int,
        y: int,
        lock_overlay: bool,
        on_position_changed: Callable[[int, int], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.resizable(False, False)
        transparent_key = "#010203"
        self.configure(fg_color=transparent_key)
        self.wm_attributes("-transparentcolor", transparent_key)
        self.wm_attributes("-alpha", 0.60)
        self.geometry(f"1x1+{x}+{y}")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self._lock_overlay = lock_overlay
        self._on_position_changed = on_position_changed
        self._drag_origin_x = 0
        self._drag_origin_y = 0
        self._drag_window_origin_x = 0
        self._drag_window_origin_y = 0
        self._center_x = x
        self._center_y = y

        self._panel = ctk.CTkFrame(
            self,
            fg_color="#000000",
            corner_radius=14,
            border_width=1,
            border_color="#00ffff",
        )
        self._panel.pack(fill="both", expand=True, padx=6, pady=6)

        self.profile_label = ctk.CTkLabel(
            self._panel,
            text="Profiles: None",
            anchor="w",
            fg_color="transparent",
            text_color="#00ffff",
        )
        self.profile_label.pack(fill="x", padx=14, pady=14)

        self.bind("<ButtonPress-1>", self._on_drag_start)
        self.bind("<B1-Motion>", self._on_drag_move)
        self.bind("<ButtonRelease-1>", self._on_drag_end)
        self._panel.bind("<ButtonPress-1>", self._on_drag_start)
        self._panel.bind("<B1-Motion>", self._on_drag_move)
        self._panel.bind("<ButtonRelease-1>", self._on_drag_end)
        self.profile_label.bind("<ButtonPress-1>", self._on_drag_start)
        self.profile_label.bind("<B1-Motion>", self._on_drag_move)
        self.profile_label.bind("<ButtonRelease-1>", self._on_drag_end)
        self.after(0, self._apply_interaction_lock)
        self.after(0, lambda: self._resize_to_text(self.profile_label.cget("text")))

    def set_lock(self, value: bool) -> None:
        self._lock_overlay = value
        self._apply_interaction_lock()

    def set_text(self, active_profile_names: list[str], active: bool) -> None:
        if not active or not active_profile_names:
            shown = "None"
        elif len(active_profile_names) <= 2:
            shown = ", ".join(active_profile_names)
        else:
            shown = f"{active_profile_names[0]}, {active_profile_names[1]} +{len(active_profile_names) - 2}"
        text = f"Profiles: {shown}"
        self.profile_label.configure(text=text)
        self._resize_to_text(text)

    def get_position(self) -> tuple[int, int]:
        return self._center_x, self._center_y

    def keep_topmost_without_focus(self) -> None:
        hwnd = self.winfo_id()
        _USER32.SetWindowPos(
            hwnd,
            _HWND_TOPMOST,
            0,
            0,
            0,
            0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_SHOWWINDOW,
        )

    def _apply_interaction_lock(self) -> None:
        hwnd = self.winfo_id()
        get_style = _USER32.GetWindowLongW
        set_style = _USER32.SetWindowLongW
        style = get_style(hwnd, _GWL_EXSTYLE)
        # Keep overlay out of Alt+Tab/task switcher.
        style |= _WS_EX_TOOLWINDOW
        style &= ~_WS_EX_APPWINDOW
        if self._lock_overlay:
            style |= _WS_EX_TRANSPARENT | _WS_EX_LAYERED
        else:
            style &= ~_WS_EX_TRANSPARENT
        set_style(hwnd, _GWL_EXSTYLE, style)
        _USER32.SetWindowPos(
            hwnd,
            _HWND_TOPMOST,
            0,
            0,
            0,
            0,
            _SWP_NOMOVE
            | _SWP_NOSIZE
            | _SWP_NOACTIVATE
            | _SWP_SHOWWINDOW
            | _SWP_FRAMECHANGED,
        )

    def _on_drag_start(self, event) -> None:
        if self._lock_overlay:
            return
        self._drag_origin_x = event.x_root
        self._drag_origin_y = event.y_root
        self._drag_window_origin_x = self.winfo_x()
        self._drag_window_origin_y = self.winfo_y()

    def _on_drag_move(self, event) -> None:
        if self._lock_overlay:
            return
        delta_x = event.x_root - self._drag_origin_x
        delta_y = event.y_root - self._drag_origin_y
        next_x = self._drag_window_origin_x + delta_x
        next_y = self._drag_window_origin_y + delta_y
        self.geometry(f"+{next_x}+{next_y}")
        self._sync_center_from_current_geometry()
        if self._on_position_changed is not None:
            self._on_position_changed(self._center_x, self._center_y)

    def _on_drag_end(self, _event) -> None:
        if self._lock_overlay:
            return
        self._sync_center_from_current_geometry()
        if self._on_position_changed is not None:
            self._on_position_changed(self._center_x, self._center_y)

    def _resize_to_text(self, text: str) -> None:
        label_font = tkfont.nametofont(str(self.profile_label.cget("font")))
        text_width = label_font.measure(text)
        text_height = label_font.metrics("linespace")
        # width/height = text + label padding + panel padding
        target_width = text_width + (14 * 2) + (6 * 2)
        target_height = text_height + (14 * 2) + (6 * 2)
        top_left_x = int(self._center_x - (target_width / 2))
        top_left_y = int(self._center_y - (target_height / 2))
        self.geometry(f"{target_width}x{target_height}+{top_left_x}+{top_left_y}")

    def _sync_center_from_current_geometry(self) -> None:
        self.update_idletasks()
        self._center_x = self.winfo_x() + (self.winfo_width() // 2)
        self._center_y = self.winfo_y() + (self.winfo_height() // 2)

