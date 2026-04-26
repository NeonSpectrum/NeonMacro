from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
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
_GWL_WNDPROC = -4
_GA_ROOT = 2
_WS_EX_TRANSPARENT = 0x00000020
_WS_EX_TOOLWINDOW = 0x00000080
_WS_EX_APPWINDOW = 0x00040000
_WS_EX_NOACTIVATE = 0x08000000
_WM_NCHITTEST = 0x0084
_HTTRANSPARENT = -1
_LRESULT = ctypes.c_ssize_t

_WNDPROC = ctypes.WINFUNCTYPE(
    _LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
_USER32.GetWindowLongPtrW.restype = ctypes.c_void_p
_USER32.SetWindowLongPtrW.restype = ctypes.c_void_p
_USER32.CallWindowProcW.restype = _LRESULT
_USER32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
_USER32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
_USER32.CallWindowProcW.argtypes = [
    ctypes.c_void_p,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]


class OverlayWindow(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTk,
        x: int,
        y: int,
        lock_overlay: bool,
        on_position_changed: Callable[[int, int], None] | None = None,
        on_drag_state_changed: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        # Hint Windows/Tk that this is a tool window (hide from Alt+Tab/taskbar).
        self._apply_toolwindow_hint()
        self.resizable(False, False)
        transparent_key = "#010203"
        self.configure(fg_color=transparent_key)
        self.wm_attributes("-transparentcolor", transparent_key)
        self.wm_attributes("-alpha", 0.60)
        self.geometry(f"1x1+{x}+{y}")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self._lock_overlay = lock_overlay
        self._on_position_changed = on_position_changed
        self._on_drag_state_changed = on_drag_state_changed
        self._drag_origin_x = 0
        self._drag_origin_y = 0
        self._drag_window_origin_x = 0
        self._drag_window_origin_y = 0
        self._center_x = x
        self._center_y = y
        self._native_hwnd: int | None = None
        self._original_wndproc: int | None = None
        self._wndproc_ref: Callable[..., int] | None = None

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

        self._bind_drag_events(self)
        self._bind_drag_events(self._panel)
        self._bind_drag_events(self.profile_label)
        self.bind("<Map>", self._on_map, add="+")
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.after(0, self._install_hit_test_passthrough_proc)
        self.after(0, self._apply_interaction_lock)
        self.after(0, lambda: self._resize_to_text(self.profile_label.cget("text")))

    def _bind_drag_events(self, widget) -> None:
        widget.bind("<ButtonPress-1>", self._on_drag_start)
        widget.bind("<B1-Motion>", self._on_drag_move)
        widget.bind("<ButtonRelease-1>", self._on_drag_end)

    def set_lock(self, value: bool) -> None:
        self._lock_overlay = value
        if value and self._on_drag_state_changed is not None:
            # If lock is enabled mid-drag, immediately clear drag state upstream.
            self._on_drag_state_changed(False)
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

    def set_position(self, x: int, y: int) -> None:
        self._center_x = int(x)
        self._center_y = int(y)
        self._resize_to_text(self.profile_label.cget("text"))

    def keep_topmost_without_focus(self) -> None:
        hwnd = self._get_native_hwnd()
        _USER32.SetWindowPos(
            hwnd,
            _HWND_TOPMOST,
            0,
            0,
            0,
            0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_SHOWWINDOW,
        )

    def _get_native_hwnd(self) -> int:
        if self._native_hwnd is not None:
            return self._native_hwnd
        hwnd = int(self.winfo_id())
        try:
            root = int(_USER32.GetAncestor(hwnd, _GA_ROOT))
            if root:
                hwnd = root
        except Exception:
            pass
        self._native_hwnd = hwnd
        return hwnd

    def _on_map(self, _event=None) -> None:
        # Tk can remap this toplevel after withdraw/deiconify, and Windows may
        # drop parts of extended styles on remap. Re-apply click-through state.
        self.after_idle(self._reapply_window_flags_after_map)

    def _reapply_window_flags_after_map(self) -> None:
        self._apply_toolwindow_hint()
        self._apply_interaction_lock()

    def _apply_toolwindow_hint(self) -> None:
        try:
            self.wm_attributes("-toolwindow", True)
        except Exception:
            pass

    def _install_hit_test_passthrough_proc(self) -> None:
        if self._wndproc_ref is not None:
            return
        hwnd = self._get_native_hwnd()
        original = _USER32.GetWindowLongPtrW(hwnd, _GWL_WNDPROC)
        if not original:
            return
        self._original_wndproc = int(original)

        @_WNDPROC
        def _overlay_wndproc(hwnd, msg, wparam, lparam):
            if msg == _WM_NCHITTEST and self._lock_overlay:
                return _HTTRANSPARENT
            return _USER32.CallWindowProcW(
                ctypes.c_void_p(self._original_wndproc),
                hwnd,
                msg,
                wparam,
                lparam,
            )

        self._wndproc_ref = _overlay_wndproc
        _USER32.SetWindowLongPtrW(
            hwnd,
            _GWL_WNDPROC,
            ctypes.cast(self._wndproc_ref, ctypes.c_void_p),
        )

    def _on_destroy(self, _event=None) -> None:
        if self._original_wndproc is None:
            return
        try:
            _USER32.SetWindowLongPtrW(
                self._get_native_hwnd(),
                _GWL_WNDPROC,
                ctypes.c_void_p(self._original_wndproc),
            )
        except Exception:
            pass
        self._original_wndproc = None
        self._wndproc_ref = None

    def _apply_interaction_lock(self) -> None:
        hwnd = self._get_native_hwnd()
        get_style = _USER32.GetWindowLongW
        set_style = _USER32.SetWindowLongW
        style = get_style(hwnd, _GWL_EXSTYLE)
        # Keep overlay out of Alt+Tab/task switcher.
        style |= _WS_EX_TOOLWINDOW
        style &= ~_WS_EX_APPWINDOW
        if self._lock_overlay:
            # Tk already configures layered/alpha behavior for this window.
            # For click-through, only toggle TRANSPARENT hit-testing.
            style |= _WS_EX_TRANSPARENT | _WS_EX_NOACTIVATE
        else:
            style &= ~_WS_EX_TRANSPARENT
            style &= ~_WS_EX_NOACTIVATE
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
        if self._on_drag_state_changed is not None:
            self._on_drag_state_changed(True)
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
        if self._on_drag_state_changed is not None:
            self._on_drag_state_changed(False)
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

