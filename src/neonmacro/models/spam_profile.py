from __future__ import annotations

from dataclasses import dataclass
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
            select_hotkey=str(data.get("select_hotkey", "")),
            is_active=False,
        )
