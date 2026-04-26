from __future__ import annotations

import re
from dataclasses import dataclass

import psutil
import win32con
import win32gui
import win32process

from ..models import AppOptions, SpamProfile


@dataclass(frozen=True)
class ForegroundContext:
    hwnd: int
    title: str
    exe_name: str


def get_foreground_context() -> ForegroundContext | None:
    try:
        foreground = win32gui.GetForegroundWindow()
        if foreground == 0:
            return None
        title = win32gui.GetWindowText(foreground)
        if not title.strip():
            return None
        _, process_id = win32process.GetWindowThreadProcessId(foreground)
        exe_name = psutil.Process(process_id).name().lower()
    except (win32gui.error, win32process.error, psutil.Error):
        return None
    return ForegroundContext(hwnd=foreground, title=title, exe_name=exe_name)


def active_profiles_matching_title(
    profiles: list[SpamProfile], foreground_title: str
) -> list[str]:
    lowered_title = foreground_title.lower()
    matches: list[str] = []
    for profile in profiles:
        if not profile.is_active:
            continue
        pattern = profile.window_title.strip()
        if not pattern:
            continue
        if profile.use_regex:
            try:
                if re.search(pattern, foreground_title, flags=re.IGNORECASE):
                    matches.append(profile.name)
            except re.error:
                continue
        elif pattern.lower() in lowered_title:
            matches.append(profile.name)
    return matches


def is_allowed_application_focused(options: AppOptions, exe_name: str) -> bool:
    allowed = {app.strip().lower() for app in options.allowed_applications if app.strip()}
    if not allowed:
        return True
    return exe_name in allowed


def is_app_window_focused(main_hwnd: int, overlay_hwnd: int) -> bool:
    try:
        foreground = win32gui.GetForegroundWindow()
    except win32gui.error:
        return False
    if foreground == 0:
        return False
    roots = (main_hwnd, overlay_hwnd)
    try:
        foreground_root = win32gui.GetAncestor(foreground, win32con.GA_ROOT)
    except win32gui.error:
        foreground_root = foreground
    if foreground_root in roots:
        return True
    for root in roots:
        if foreground == root:
            return True
        try:
            if win32gui.IsChild(root, foreground):
                return True
        except win32gui.error:
            continue
    return False

