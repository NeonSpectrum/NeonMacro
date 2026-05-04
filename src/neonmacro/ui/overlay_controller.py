from __future__ import annotations

from dataclasses import dataclass

import psutil
import win32gui
import win32process

from ..models import AppOptions, SpamProfile
from ..targeting.title_matching import compile_title_matcher, title_matches


@dataclass(frozen=True)
class ForegroundContext:
    hwnd: int
    title: str
    exe_name: str


def get_foreground_process_exe() -> str | None:
    """Foreground executable name, or None if unavailable.

    Unlike get_foreground_context, does not require a non-empty window title.
    """
    try:
        foreground = win32gui.GetForegroundWindow()
        if foreground == 0:
            return None
        _, process_id = win32process.GetWindowThreadProcessId(foreground)
        return psutil.Process(process_id).name().lower()
    except (win32gui.error, win32process.error, psutil.Error):
        return None


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
    matches: list[str] = []
    for profile in profiles:
        if not profile.is_active:
            continue
        matcher = compile_title_matcher(profile.window_title, profile.use_regex)
        if matcher is None:
            continue
        if title_matches(matcher, foreground_title):
            matches.append(profile.name)
    return matches


def allowed_application_exes(options: AppOptions) -> set[str]:
    """Lowercased executable names from options (may be empty)."""
    return {app.strip().lower() for app in options.allowed_applications if app.strip()}


def is_allowed_application_focused(options: AppOptions, exe_name: str) -> bool:
    allowed = allowed_application_exes(options)
    if not allowed:
        return True
    return exe_name in allowed

