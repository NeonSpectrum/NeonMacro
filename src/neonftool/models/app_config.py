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

    def to_dict(self) -> dict[str, Any]:
        return {
            "profiles": [profile.to_dict() for profile in self.profiles],
            "options": self.options.to_dict(),
            "overlay": self.overlay.to_dict(),
            "selected_profile_name": self.selected_profile_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        profiles = [SpamProfile.from_dict(item) for item in data.get("profiles", [])]
        selected = data.get("selected_profile_name")
        if selected is not None:
            selected = str(selected)
        return cls(
            profiles=profiles,
            options=AppOptions.from_dict(data.get("options", {})),
            overlay=OverlayConfig.from_dict(data.get("overlay", {})),
            selected_profile_name=selected,
        )
