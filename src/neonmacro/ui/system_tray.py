from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from PIL import Image
from pystray import Icon, Menu, MenuItem

logger = logging.getLogger(__name__)


class SystemTrayController:
    def __init__(
        self,
        *,
        tooltip: str,
        icon_path: str | None,
        on_open: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        self._tooltip = tooltip
        self._icon_path = icon_path
        self._on_open = on_open
        self._on_exit = on_exit
        self._icon: Icon | None = None
        self._visible = False

    @property
    def is_visible(self) -> bool:
        return self._visible

    def show(self) -> None:
        if self._visible:
            return
        image = self._load_image()
        if image is None:
            return
        menu = Menu(
            MenuItem("Open NeonMacro", self._handle_open, default=True),
            MenuItem("Exit", self._handle_exit),
        )
        self._icon = Icon("neonmacro", image, self._tooltip, menu)
        self._icon.run_detached()
        self._visible = True

    def hide(self) -> None:
        if not self._visible or self._icon is None:
            return
        self._icon.stop()
        self._icon = None
        self._visible = False

    def shutdown(self) -> None:
        self.hide()

    def _load_image(self) -> Image.Image | None:
        if self._icon_path:
            path = Path(self._icon_path)
            if path.exists():
                try:
                    return Image.open(path)
                except OSError:
                    logger.exception("Failed to load tray icon from %s", path)
        logger.warning("Tray icon path is unavailable; tray mode disabled.")
        return None

    def _handle_open(self, _icon: Icon | None = None, _item: MenuItem | None = None) -> None:
        self._on_open()

    def _handle_exit(self, _icon: Icon | None = None, _item: MenuItem | None = None) -> None:
        self._on_exit()
