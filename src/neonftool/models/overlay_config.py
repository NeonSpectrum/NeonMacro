from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class OverlayConfig:
    x: int = 100
    y: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OverlayConfig":
        return cls(x=int(data.get("x", 100)), y=int(data.get("y", 100)))
