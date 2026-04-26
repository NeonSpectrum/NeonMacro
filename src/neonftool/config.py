from __future__ import annotations

import json
from pathlib import Path

from .models import AppConfig


class ConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> AppConfig:
        if not self.path.exists():
            config = AppConfig()
            self.save(config)
            return config
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return AppConfig.from_dict(raw)

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(config.to_dict(), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

