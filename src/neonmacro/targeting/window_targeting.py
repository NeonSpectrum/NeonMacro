from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import SpamProfile
from ..core.postmessage import TargetWindow, list_visible_windows


@dataclass(frozen=True)
class CompiledProfileMatcher:
    profile: SpamProfile
    regex: re.Pattern[str] | None
    lowered_pattern: str


def compile_profile_matchers(profiles: list[SpamProfile]) -> list[CompiledProfileMatcher]:
    compiled: list[CompiledProfileMatcher] = []
    for profile in profiles:
        pattern = profile.window_title.strip()
        if not pattern:
            continue
        regex: re.Pattern[str] | None = None
        lowered = ""
        if profile.use_regex:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error:
                continue
        else:
            lowered = pattern.lower()
        compiled.append(
            CompiledProfileMatcher(
                profile=profile,
                regex=regex,
                lowered_pattern=lowered,
            )
        )
    return compiled


def collect_targets_by_profile(
    profiles: list[SpamProfile],
    allowed_executables: list[str],
) -> dict[str, list[TargetWindow]]:
    windows = list_visible_windows()
    allowed = {value.strip().lower() for value in allowed_executables if value.strip()}
    result: dict[str, list[TargetWindow]] = {}
    for matcher in compile_profile_matchers(profiles):
        filtered: list[TargetWindow] = []
        fallback: list[TargetWindow] = []
        for window in windows:
            if matcher.regex is not None:
                if not matcher.regex.search(window.title):
                    continue
            elif matcher.lowered_pattern not in window.title.lower():
                continue
            fallback.append(window)
            if allowed and window.exe_name.lower() not in allowed:
                continue
            filtered.append(window)
        result[matcher.profile.name] = filtered or fallback if allowed else filtered
    return result

