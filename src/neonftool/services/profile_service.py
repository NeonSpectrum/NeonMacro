from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..models import SpamProfile


@dataclass(frozen=True)
class StatusView:
    text: str
    overlay_has_active_spam: bool


def sanitize_startup_hotkeys(
    profiles: list[SpamProfile],
    normalize_hotkey: Callable[[str], str],
    can_bind_hotkey: Callable[[str], bool],
) -> tuple[bool, list[str]]:
    seen: dict[str, str] = {}
    removed_any = False
    issues: list[str] = []
    for profile in profiles:
        raw = profile.select_hotkey.strip()
        if not raw:
            continue
        normalized = normalize_hotkey(raw)
        if not normalized:
            issues.append(f"{profile.name}: '{raw}' has invalid format.")
            profile.select_hotkey = ""
            removed_any = True
            continue
        if normalized in seen:
            issues.append(f"{profile.name}: '{raw}' duplicates {seen[normalized]}.")
            profile.select_hotkey = ""
            removed_any = True
            continue
        if not can_bind_hotkey(normalized):
            issues.append(f"{profile.name}: '{raw}' is already used by Windows/another app.")
            profile.select_hotkey = ""
            removed_any = True
            continue
        seen[normalized] = profile.name
        profile.select_hotkey = normalized.upper()
    return removed_any, issues


def enforce_parallel_profile_policy(profiles: list[SpamProfile], allow_parallel: bool) -> None:
    if allow_parallel:
        return
    seen_active = False
    for profile in profiles:
        if not profile.is_active:
            continue
        if not seen_active:
            seen_active = True
            continue
        profile.is_active = False


def validate_profile_uniqueness(
    profiles: list[SpamProfile],
    candidate: SpamProfile,
    normalize_hotkey: Callable[[str], str],
    ignore_index: int | None = None,
) -> str | None:
    for index, item in enumerate(profiles):
        if ignore_index is not None and index == ignore_index:
            continue
        if item.name == candidate.name:
            return "Spam name must be unique."
        if normalize_hotkey(item.select_hotkey) == normalize_hotkey(candidate.select_hotkey):
            return f"Hotkey '{candidate.select_hotkey}' is already used by another profile."
    return None


def build_status_view(enabled: bool, active_profile_names: list[str]) -> StatusView:
    if not active_profile_names:
        shown = "None"
    elif len(active_profile_names) <= 3:
        shown = ", ".join(active_profile_names)
    else:
        shown = ", ".join(active_profile_names[:3]) + f" (+{len(active_profile_names) - 3})"
    active = enabled and bool(active_profile_names)
    label = "Active" if active else "Inactive"
    return StatusView(
        text=f"Current Spam: {shown} | Status: {label}",
        overlay_has_active_spam=active,
    )

