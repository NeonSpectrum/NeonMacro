from __future__ import annotations

from dataclasses import dataclass

from ..models import SpamProfile
from ..core.postmessage import TargetWindow, list_visible_windows
from .title_matching import CompiledTitleMatcher, compile_title_matcher, title_matches


@dataclass(frozen=True)
class CompiledProfileMatcher:
    profile: SpamProfile
    matcher: CompiledTitleMatcher


def compile_profile_matchers(profiles: list[SpamProfile]) -> list[CompiledProfileMatcher]:
    compiled: list[CompiledProfileMatcher] = []
    for profile in profiles:
        matcher = compile_title_matcher(profile.window_title, profile.use_regex)
        if matcher is None:
            continue
        compiled.append(
            CompiledProfileMatcher(
                profile=profile,
                matcher=matcher,
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
        for window in windows:
            if not title_matches(matcher.matcher, window.title):
                continue
            if allowed and window.exe_name.lower() not in allowed:
                continue
            filtered.append(window)
        result[matcher.profile.name] = filtered
    return result

