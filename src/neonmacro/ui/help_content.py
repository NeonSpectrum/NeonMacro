from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HelpSection:
    title: str
    bullets: tuple[str, ...]


HELP_SECTIONS: tuple[HelpSection, ...] = (
    HelpSection(
        title="Overview",
        bullets=(
            "Purpose: create profiles that target a window and repeatedly send a key using PostMessage.",
            "Use profiles to switch between different games/apps and key timings quickly.",
            "During key-capture mode, app hotkeys are temporarily disabled to avoid accidental toggles.",
        ),
    ),
    HelpSection(
        title="Profile Fields",
        bullets=(
            "Profile name: friendly label shown in the table and used for quick identification.",
            "Window title pattern (regex): regular expression used to find matching target windows by title.",
            "Interval (ms): delay between spam sends. Lower values are faster; very low values can be heavy.",
            "Hotkey: key combo used to activate/select the profile.",
            "Spam key: single key only (no modifiers) that gets repeatedly sent when profile spamming runs.",
        ),
    ),
    HelpSection(
        title="Options",
        bullets=(
            "General: startup behavior and tray behavior (open on startup, minimize options).",
            "Tray: right-click the icon and choose Reload to restart NeonMacro with the same command-line flags (config is saved first).",
            "Overlay: enable/disable overlay, click-through mode, force visibility, and manual coordinates.",
            "Spam settings: allow parallel profiles, allow background spam, and auto pause/stop controls.",
            "Auto pause/stop keys: semicolon-separated hotkeys that pause/stop spam when input activity is detected.",
            "Profile hotkey restrictions: optionally only allow profile hotkeys for listed applications.",
            "Application list: semicolon-separated executable names used by restriction rules when that option is on.",
            "When the list is non-empty, global hotkeys also re-bind automatically once if the foreground app switches from a program not in the list to one that is (for example after closing a game).",
            "Settings overlay hotkey: shortcut to open/close the settings overlay quickly.",
        ),
    ),
)


def build_help_popup_text() -> str:
    sections: list[str] = []
    for section in HELP_SECTIONS:
        bullets = "\n".join(f"- {item}" for item in section.bullets)
        sections.append(f"{section.title}\n{bullets}")
    return "\n\n".join(sections)
