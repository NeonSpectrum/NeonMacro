from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .defaults import DEFAULT_AUTO_PAUSE_STOP_KEYS


@dataclass
class AppOptions:
    enable_overlay: bool = True
    lock_overlay: bool = False
    force_overlay_visible: bool = False
    allow_parallel: bool = True
    allow_background: bool = True
    auto_pause_stop_on_key_press: bool = False
    auto_pause_stop_duration_ms: int = 120
    auto_pause_stop_keys: list[str] = field(default_factory=lambda: list(DEFAULT_AUTO_PAUSE_STOP_KEYS))
    restrict_profile_hotkeys_to_allowed_apps: bool = False
    allowed_applications: list[str] = field(default_factory=list)
    settings_toggle_hotkey: str = "{F10}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppOptions":
        apps = data.get("allowed_applications", [])
        normalized_apps = [str(item) for item in apps if str(item).strip()]
        merged_enabled = bool(data.get("auto_pause_stop_on_key_press", False))
        merged_duration_raw = data.get("auto_pause_stop_duration_ms", 120)
        merged_keys_raw = data.get("auto_pause_stop_keys", DEFAULT_AUTO_PAUSE_STOP_KEYS)
        normalized_merged_keys = [str(item).strip() for item in merged_keys_raw if str(item).strip()]
        try:
            merged_duration_ms = int(merged_duration_raw)
        except (TypeError, ValueError):
            merged_duration_ms = 120
        return cls(
            enable_overlay=bool(data.get("enable_overlay", True)),
            lock_overlay=bool(data.get("lock_overlay", False)),
            force_overlay_visible=bool(data.get("force_overlay_visible", False)),
            allow_parallel=bool(data.get("allow_parallel", True)),
            allow_background=bool(data.get("allow_background", True)),
            auto_pause_stop_on_key_press=bool(merged_enabled),
            auto_pause_stop_duration_ms=max(-1, merged_duration_ms),
            auto_pause_stop_keys=normalized_merged_keys,
            restrict_profile_hotkeys_to_allowed_apps=bool(
                data.get("restrict_profile_hotkeys_to_allowed_apps", False)
            ),
            allowed_applications=normalized_apps,
            settings_toggle_hotkey=str(data.get("settings_toggle_hotkey", "{F10}")),
        )
