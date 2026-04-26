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
