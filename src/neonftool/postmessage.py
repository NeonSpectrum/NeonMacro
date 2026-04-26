from __future__ import annotations

import re
import logging
import time
import ctypes
from dataclasses import dataclass
from typing import Callable

import psutil
import win32api
import win32con
import win32gui
import win32process

from .keymaps import normalize_spam_key_combo

logger = logging.getLogger(__name__)
KEYUP_DELAY_SECONDS = 0.015
_USER32 = ctypes.WinDLL("user32", use_last_error=True)


@dataclass
class TargetWindow:
    hwnd: int
    title: str
    exe_name: str


def _build_matcher(pattern: str, use_regex: bool) -> Callable[[str], bool]:
    if use_regex:
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            # Keep the engine alive even if a profile has an invalid regex.
            logger.warning("Invalid regex pattern '%s'; profile will match nothing.", pattern)
            return lambda _title: False
        return lambda title: bool(regex.search(title))
    lowered = pattern.lower()
    return lambda title: lowered in title.lower()


def _get_process_name(hwnd: int) -> str:
    _, process_id = win32process.GetWindowThreadProcessId(hwnd)
    process = psutil.Process(process_id)
    return process.name()


def find_target_windows(
    title_pattern: str,
    use_regex: bool,
    allowed_executables: list[str],
) -> list[TargetWindow]:
    matcher = _build_matcher(title_pattern, use_regex)
    allowed = {item.lower() for item in allowed_executables}
    matches: list[TargetWindow] = []
    title_only_matches: list[TargetWindow] = []

    def _enum_handler(hwnd: int, _: int) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title.strip():
            return
        if not matcher(title):
            return
        try:
            exe_name = _get_process_name(hwnd)
        except (psutil.Error, win32process.error):
            return
        target = TargetWindow(hwnd=hwnd, title=title, exe_name=exe_name)
        title_only_matches.append(target)
        if allowed and exe_name.lower() not in allowed:
            return
        matches.append(target)

    win32gui.EnumWindows(_enum_handler, 0)
    logger.debug(
        "find_target_windows pattern=%r regex=%s allowed=%s title_matches=%d filtered_matches=%d",
        title_pattern,
        use_regex,
        allowed_executables,
        len(title_only_matches),
        len(matches),
    )
    if matches:
        return matches
    if allowed:
        # Fallback: don't block title-matched windows just because app filter is outdated.
        return title_only_matches
    return matches


def send_key(hwnd: int, key_name: str) -> bool:
    def _post_message(target_hwnd: int, msg: int, wparam: int, lparam: int) -> tuple[bool, int]:
        ctypes.set_last_error(0)
        ok = bool(_USER32.PostMessageW(target_hwnd, msg, wparam, lparam))
        err = ctypes.get_last_error()
        return ok, err

    def _post_pair(
        target_hwnd: int,
        vk_code: int,
        down_lparam: int,
        up_lparam: int,
        keyup_delay_seconds: float = KEYUP_DELAY_SECONDS,
    ) -> tuple[bool, int, bool, int]:
        down_ok, down_err = _post_message(target_hwnd, win32con.WM_KEYDOWN, vk_code, down_lparam)
        if down_ok and keyup_delay_seconds > 0:
            time.sleep(keyup_delay_seconds)
        up_ok, up_err = _post_message(target_hwnd, win32con.WM_KEYUP, vk_code, up_lparam)
        return down_ok, down_err, up_ok, up_err

    canonical, vk_sequence = normalize_spam_key_combo(key_name)
    modifier_vks = vk_sequence[:-1]
    main_vk = vk_sequence[-1]
    sent_to_child = False

    def _press_sequence(target_hwnd: int) -> tuple[bool, int, bool, int]:
        last_down_ok = True
        last_down_err = 0
        last_up_ok = True
        last_up_err = 0
        for modifier_vk in modifier_vks:
            scan_code = win32api.MapVirtualKey(modifier_vk, 0)
            lparam_down = 1 | (scan_code << 16)
            last_down_ok, last_down_err = _post_message(
                target_hwnd,
                win32con.WM_KEYDOWN,
                modifier_vk,
                lparam_down,
            )
        scan_code = win32api.MapVirtualKey(main_vk, 0)
        lparam_down = 1 | (scan_code << 16)
        lparam_up = lparam_down | (1 << 30) | (1 << 31)
        last_down_ok, last_down_err, last_up_ok, last_up_err = _post_pair(
            target_hwnd, main_vk, lparam_down, lparam_up
        )
        for modifier_vk in reversed(modifier_vks):
            scan_code = win32api.MapVirtualKey(modifier_vk, 0)
            lparam_down = 1 | (scan_code << 16)
            lparam_up = lparam_down | (1 << 30) | (1 << 31)
            last_up_ok, last_up_err = _post_message(
                target_hwnd,
                win32con.WM_KEYUP,
                modifier_vk,
                lparam_up,
            )
        return last_down_ok, last_down_err, last_up_ok, last_up_err

    down_ok, down_err, up_ok, up_err = _press_sequence(hwnd)

    # Some windows process keyboard messages only on their focused child window.
    child = win32gui.GetWindow(hwnd, win32con.GW_CHILD)
    if child:
        child_down_ok, child_down_err, child_up_ok, child_up_err = _press_sequence(child)
        sent_to_child = True
        down_ok = down_ok or child_down_ok
        up_ok = up_ok or child_up_ok
        if down_err == 0:
            down_err = child_down_err
        if up_err == 0:
            up_err = child_up_err

    logger.debug(
        "send_key hwnd=%s key=%s class=%s valid=%s foreground=%s post_down=%s post_down_err=%s post_up=%s post_up_err=%s child=%s",
        hwnd,
        canonical,
        win32gui.GetClassName(hwnd),
        bool(win32gui.IsWindow(hwnd)),
        win32gui.GetForegroundWindow() == hwnd,
        down_ok,
        down_err,
        up_ok,
        up_err,
        sent_to_child,
    )
    return down_ok and up_ok

