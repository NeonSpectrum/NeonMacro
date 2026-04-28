from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _is_packaged_runtime() -> bool:
    # PyInstaller/py2exe-style flag.
    if getattr(sys, "frozen", False):
        return True
    # Nuitka provides __compiled__ in compiled modules.
    if "__compiled__" in globals():
        return True
    return False


def _read_log_level_from_dotenv() -> str | None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "LOG_LEVEL":
            return value.strip().strip('"').strip("'")
    return None


def configure_logging(log_file: Path) -> None:
    is_production_runtime = _is_packaged_runtime()
    root = logging.getLogger()

    # Force-disable logging for packaged/frozen runtime.
    if is_production_runtime:
        for handler in list(root.handlers):
            if isinstance(handler, RotatingFileHandler):
                root.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass
        logging.disable(logging.CRITICAL)
        return

    raw_level = os.getenv("LOG_LEVEL") or _read_log_level_from_dotenv()
    normalized_level = (raw_level or "DEBUG").strip().upper()

    if normalized_level in {"OFF", "NONE", "0"}:
        logging.disable(logging.CRITICAL)
        return

    logging.disable(logging.NOTSET)
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    level = level_map.get(normalized_level, logging.DEBUG)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    root.setLevel(level)

    for handler in list(root.handlers):
        if isinstance(handler, RotatingFileHandler) and getattr(handler, "baseFilename", "") == str(log_file):
            return

    handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(handler)
