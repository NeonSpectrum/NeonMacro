from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes

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


class OverlayNativeController:
    def __init__(self, window_id_supplier, lock_supplier) -> None:
        self._window_id_supplier = window_id_supplier
        self._lock_supplier = lock_supplier
        self._native_hwnd: int | None = None
        self._original_wndproc: int | None = None
        self._wndproc_ref = None

    def get_native_hwnd(self) -> int:
        if self._native_hwnd is not None:
            return self._native_hwnd
        hwnd = int(self._window_id_supplier())
        try:
            root = int(_USER32.GetAncestor(hwnd, _GA_ROOT))
            if root:
                hwnd = root
        except Exception:
            pass
        self._native_hwnd = hwnd
        return hwnd

    def apply_toolwindow_hint(self, wm_attributes) -> None:
        try:
            wm_attributes("-toolwindow", True)
        except Exception:
            pass

    def keep_topmost_without_focus(self) -> None:
        hwnd = self.get_native_hwnd()
        _USER32.SetWindowPos(
            hwnd,
            _HWND_TOPMOST,
            0,
            0,
            0,
            0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_SHOWWINDOW,
        )

    def install_hit_test_passthrough_proc(self) -> None:
        if self._wndproc_ref is not None:
            return
        hwnd = self.get_native_hwnd()
        original = _USER32.GetWindowLongPtrW(hwnd, _GWL_WNDPROC)
        if not original:
            return
        self._original_wndproc = int(original)

        @_WNDPROC
        def _overlay_wndproc(hwnd, msg, wparam, lparam):
            if msg == _WM_NCHITTEST and self._lock_supplier():
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

    def restore_wndproc(self) -> None:
        if self._original_wndproc is None:
            return
        try:
            _USER32.SetWindowLongPtrW(
                self.get_native_hwnd(),
                _GWL_WNDPROC,
                ctypes.c_void_p(self._original_wndproc),
            )
        except Exception:
            pass
        self._original_wndproc = None
        self._wndproc_ref = None

    def apply_interaction_lock(self) -> None:
        hwnd = self.get_native_hwnd()
        get_style = _USER32.GetWindowLongW
        set_style = _USER32.SetWindowLongW
        style = get_style(hwnd, _GWL_EXSTYLE)
        style |= _WS_EX_TOOLWINDOW
        style &= ~_WS_EX_APPWINDOW
        if self._lock_supplier():
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
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_SHOWWINDOW | _SWP_FRAMECHANGED,
        )

