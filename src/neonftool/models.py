from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SpamProfile:
    name: str
    window_title: str
    use_regex: bool
    spam_key: str
    interval_ms: int
    select_hotkey: str
    is_active: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpamProfile":
        return cls(
            name=str(data.get("name", "New Spam")),
            window_title=str(data.get("window_title", "")),
            use_regex=bool(data.get("use_regex", False)),
            spam_key=str(data.get("spam_key", "1")).upper(),
            interval_ms=max(10, int(data.get("interval_ms", 250))),
            select_hotkey=str(data.get("select_hotkey", "")).upper(),
            is_active=bool(data.get("is_active", False)),
        )


@dataclass
class AppOptions:
    enable_overlay: bool = True
    lock_overlay: bool = False
    allowed_applications: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppOptions":
        apps = data.get("allowed_applications", [])
        normalized_apps = [str(item) for item in apps if str(item).strip()]
        return cls(
            enable_overlay=bool(data.get("enable_overlay", True)),
            lock_overlay=bool(data.get("lock_overlay", False)),
            allowed_applications=normalized_apps,
        )


@dataclass
class OverlayConfig:
    x: int = 100
    y: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OverlayConfig":
        return cls(x=int(data.get("x", 100)), y=int(data.get("y", 100)))


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

