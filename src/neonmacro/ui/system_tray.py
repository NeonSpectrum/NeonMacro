from __future__ import annotations

import logging
from pathlib import Path
import threading
from collections.abc import Callable

import win32api
import win32con
import win32gui

logger = logging.getLogger(__name__)


class SystemTrayController:
    def __init__(
        self,
        *,
        tooltip: str,
        icon_path: str | None,
        on_open: Callable[[], None],
        on_exit: Callable[[], None],
        on_reload: Callable[[], None] | None = None,
    ) -> None:
        self._tooltip = tooltip
        self._icon_path = icon_path
        self._on_open = on_open
        self._on_exit = on_exit
        self._on_reload = on_reload
        self._thread: threading.Thread | None = None
        self._hwnd: int | None = None
        self._notify_id: tuple | None = None
        self._hicon: int | None = None
        self._window_class_name = "NeonMacroSystemTrayWindow"
        self._startup_event = threading.Event()
        self._lock = threading.Lock()
        self._visible = False

    @property
    def is_visible(self) -> bool:
        return self._visible

    def show(self) -> None:
        with self._lock:
            if self._visible:
                return
            if not self._icon_path:
                logger.warning("Tray icon path is unavailable; tray mode disabled.")
                return
            icon_file = Path(self._icon_path)
            if not icon_file.exists():
                logger.warning("Tray icon path is unavailable; tray mode disabled.")
                return
            self._startup_event.clear()
            self._thread = threading.Thread(target=self._run_message_loop, daemon=True)
            self._thread.start()
        if not self._startup_event.wait(timeout=2.0):
            logger.error("Timed out while creating system tray icon window.")
            return
        with self._lock:
            self._visible = self._hwnd is not None and self._notify_id is not None

    def hide(self) -> None:
        with self._lock:
            hwnd = self._hwnd
            thread = self._thread
        if hwnd:
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            except win32gui.error:
                pass
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        with self._lock:
            self._thread = None
            self._hwnd = None
            self._notify_id = None
            self._hicon = None
            self._visible = False

    def shutdown(self) -> None:
        self.hide()

    def _run_message_loop(self) -> None:
        message_id = win32con.WM_USER + 1
        open_command = 1001
        exit_command = 1002
        reload_command = 1003

        def on_command(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
            command = win32api.LOWORD(wparam)
            if command == open_command:
                self._handle_open()
            elif command == exit_command:
                self._handle_exit()
            elif command == reload_command:
                self._handle_reload()
            return 0

        def on_taskbar_notify(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
            if lparam in (win32con.WM_LBUTTONUP, win32con.WM_LBUTTONDBLCLK):
                self._handle_open()
                return 0
            if lparam == win32con.WM_RBUTTONUP:
                self._show_context_menu(
                    hwnd, open_command, reload_command, exit_command
                )
            return 0

        def on_destroy(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
            with self._lock:
                notify_id = self._notify_id
                hicon = self._hicon
            if notify_id is not None:
                try:
                    win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, notify_id)
                except win32gui.error:
                    pass
            if hicon:
                try:
                    win32gui.DestroyIcon(hicon)
                except win32gui.error:
                    pass
            with self._lock:
                self._hwnd = None
                self._notify_id = None
                self._hicon = None
                self._visible = False
            win32gui.PostQuitMessage(0)
            return 0

        message_map = {
            win32con.WM_COMMAND: on_command,
            message_id: on_taskbar_notify,
            win32con.WM_DESTROY: on_destroy,
        }
        window_class = win32gui.WNDCLASS()
        window_class.hInstance = win32api.GetModuleHandle(None)
        window_class.lpszClassName = self._window_class_name
        window_class.lpfnWndProc = message_map

        try:
            win32gui.RegisterClass(window_class)
        except win32gui.error:
            # Already registered in this process; safe to continue.
            pass

        hwnd = win32gui.CreateWindowEx(
            0,
            self._window_class_name,
            self._window_class_name,
            0,
            0,
            0,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            0,
            0,
            window_class.hInstance,
            None,
        )

        icon_path = str(self._icon_path) if self._icon_path else ""
        hicon = win32gui.LoadImage(
            0,
            icon_path,
            win32con.IMAGE_ICON,
            0,
            0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
        )
        if not hicon:
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        notify_id = (
            hwnd,
            0,
            win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
            message_id,
            hicon,
            self._tooltip,
        )
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, notify_id)

        with self._lock:
            self._hwnd = hwnd
            self._notify_id = notify_id
            self._hicon = hicon
            self._visible = True
        self._startup_event.set()
        win32gui.PumpMessages()

    def _show_context_menu(
        self,
        hwnd: int,
        open_command: int,
        reload_command: int,
        exit_command: int,
    ) -> None:
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, open_command, "Open NeonMacro")
        if self._on_reload is not None:
            win32gui.AppendMenu(menu, win32con.MF_STRING, reload_command, "Reload")
        win32gui.AppendMenu(menu, win32con.MF_STRING, exit_command, "Exit")
        pos_x, pos_y = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(hwnd)
        win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON,
            pos_x,
            pos_y,
            0,
            hwnd,
            None,
        )
        win32gui.PostMessage(hwnd, win32con.WM_NULL, 0, 0)
        win32gui.DestroyMenu(menu)

    def _handle_open(self) -> None:
        try:
            self._on_open()
        except Exception:
            logger.exception("System tray open handler failed.")

    def _handle_exit(self) -> None:
        try:
            self._on_exit()
        except Exception:
            logger.exception("System tray exit handler failed.")

    def _handle_reload(self) -> None:
        if self._on_reload is None:
            return
        try:
            self._on_reload()
        except Exception:
            logger.exception("System tray reload handler failed.")
