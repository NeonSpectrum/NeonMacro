from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .app_options import AppOptions
from .overlay_config import OverlayConfig
from .spam_profile import SpamProfile


@dataclass
class AppConfig:
    profiles: list[SpamProfile] = field(default_factory=list)
    options: AppOptions = field(default_factory=AppOptions)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    selected_profile_name: str | None = None
    window_x: int | None = None
    window_y: int | None = None
    window_width: int | None = None
    window_height: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "profiles": [profile.to_dict() for profile in self.profiles],
            "options": self.options.to_dict(),
            "overlay": self.overlay.to_dict(),
            "selected_profile_name": self.selected_profile_name,
            "window_x": self.window_x,
            "window_y": self.window_y,
            "window_width": self.window_width,
            "window_height": self.window_height,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        profiles = [SpamProfile.from_dict(item) for item in data.get("profiles", [])]
        options_data = data.get("options")
        if not isinstance(options_data, dict):
            # Backward-compatibility for configs saved with a previous typo.
            legacy_options = data.get("optionss")
            options_data = legacy_options if isinstance(legacy_options, dict) else {}
        selected = data.get("selected_profile_name")
        if selected is not None:
            selected = str(selected)
        window_x = cls._as_int_or_none(data.get("window_x"))
        window_y = cls._as_int_or_none(data.get("window_y"))
        window_width = cls._as_int_or_none(data.get("window_width"))
        window_height = cls._as_int_or_none(data.get("window_height"))
        return cls(
            profiles=profiles,
            options=AppOptions.from_dict(options_data),
            overlay=OverlayConfig.from_dict(data.get("overlay", {})),
            selected_profile_name=selected,
            window_x=window_x,
            window_y=window_y,
            window_width=window_width,
            window_height=window_height,
        )

    @staticmethod
    def _as_int_or_none(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
