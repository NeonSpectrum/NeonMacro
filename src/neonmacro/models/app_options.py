from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .defaults import DEFAULT_AUTO_STOP_KEYS


@dataclass
class AppOptions:
    enable_overlay: bool = True
    lock_overlay: bool = False
    force_overlay_visible: bool = False
    allow_parallel: bool = True
    allow_background: bool = True
    auto_stop_on_key_press: bool = False
    restrict_profile_hotkeys_to_allowed_apps: bool = False
    auto_stop_keys: list[str] = field(default_factory=lambda: list(DEFAULT_AUTO_STOP_KEYS))
    allowed_applications: list[str] = field(default_factory=list)
    settings_toggle_hotkey: str = "{F10}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppOptions":
        apps = data.get("allowed_applications", [])
        normalized_apps = [str(item) for item in apps if str(item).strip()]
        stop_keys = data.get("auto_stop_keys", DEFAULT_AUTO_STOP_KEYS)
        normalized_stop_keys = [str(item).strip() for item in stop_keys if str(item).strip()]
        return cls(
            enable_overlay=bool(data.get("enable_overlay", True)),
            lock_overlay=bool(data.get("lock_overlay", False)),
            force_overlay_visible=bool(data.get("force_overlay_visible", False)),
            allow_parallel=bool(data.get("allow_parallel", True)),
            allow_background=bool(data.get("allow_background", True)),
            auto_stop_on_key_press=bool(data.get("auto_stop_on_key_press", False)),
            restrict_profile_hotkeys_to_allowed_apps=bool(
                data.get("restrict_profile_hotkeys_to_allowed_apps", False)
            ),
            auto_stop_keys=normalized_stop_keys,
            allowed_applications=normalized_apps,
            settings_toggle_hotkey=str(data.get("settings_toggle_hotkey", "{F10}")),
        )
