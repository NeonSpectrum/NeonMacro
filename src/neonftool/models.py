from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


DEFAULT_AUTO_STOP_KEYS: list[str] = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
    "F6",
    "F7",
    "F8",
    "F9",
]


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
        # Runtime-only flag; do not persist active state in config.
        return {
            "name": self.name,
            "window_title": self.window_title,
            "use_regex": self.use_regex,
            "spam_key": self.spam_key,
            "interval_ms": self.interval_ms,
            "select_hotkey": self.select_hotkey,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpamProfile":
        return cls(
            name=str(data.get("name", "New Spam")),
            window_title=str(data.get("window_title", "")),
            use_regex=bool(data.get("use_regex", False)),
            spam_key=str(data.get("spam_key", "1")).upper(),
            interval_ms=max(10, int(data.get("interval_ms", 250))),
            select_hotkey=str(data.get("select_hotkey", "")).upper(),
            is_active=False,
        )


@dataclass
class AppOptions:
    enable_overlay: bool = True
    lock_overlay: bool = False
    force_overlay_visible: bool = False
    allow_parallel: bool = True
    auto_stop_on_key_press: bool = False
    auto_stop_keys: list[str] = field(default_factory=lambda: list(DEFAULT_AUTO_STOP_KEYS))
    allowed_applications: list[str] = field(default_factory=list)

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
            auto_stop_on_key_press=bool(data.get("auto_stop_on_key_press", False)),
            auto_stop_keys=normalized_stop_keys,
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

