from __future__ import annotations

import time
import tkinter.font as tkfont
from typing import Callable

import customtkinter as ctk

from ..platform.windows.overlay_native import OverlayNativeController


class OverlayWindow(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTk,
        x: int,
        y: int,
        lock_overlay: bool,
        on_position_changed: Callable[[int, int], None] | None = None,
        on_drag_state_changed: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.resizable(False, False)
        transparent_key = "#010203"
        self.configure(fg_color=transparent_key)
        self.wm_attributes("-transparentcolor", transparent_key)
        self.wm_attributes("-alpha", 0.60)
        self.geometry(f"1x1+{x}+{y}")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self._lock_overlay = lock_overlay
        self._on_position_changed = on_position_changed
        self._on_drag_state_changed = on_drag_state_changed
        self._drag_origin_x = 0
        self._drag_origin_y = 0
        self._drag_window_origin_x = 0
        self._drag_window_origin_y = 0
        self._center_x = x
        self._center_y = y
        self._last_set_text: str = ""
        self._last_geometry: str = ""
        self._last_drag_sync_monotonic: float = 0.0
        self._native = OverlayNativeController(
            window_id_supplier=self.winfo_id,
            lock_supplier=lambda: self._lock_overlay,
        )
        self._native.apply_toolwindow_hint(self.wm_attributes)

        self._panel = ctk.CTkFrame(
            self,
            fg_color="#000000",
            corner_radius=14,
            border_width=1,
            border_color="#00ffff",
        )
        self._panel.pack(fill="both", expand=True, padx=6, pady=6)

        self.profile_label = ctk.CTkLabel(
            self._panel,
            text="Profiles: None",
            anchor="w",
            fg_color="transparent",
            text_color="#00ffff",
        )
        self.profile_label.pack(fill="x", padx=14, pady=14)

        self._bind_drag_events(self)
        self._bind_drag_events(self._panel)
        self._bind_drag_events(self.profile_label)
        self.bind("<Map>", self._on_map, add="+")
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.after(0, self._native.install_hit_test_passthrough_proc)
        self.after(0, self._apply_interaction_lock)
        self.after(0, lambda: self._resize_to_text(self.profile_label.cget("text")))

    def _bind_drag_events(self, widget) -> None:
        widget.bind("<ButtonPress-1>", self._on_drag_start)
        widget.bind("<B1-Motion>", self._on_drag_move)
        widget.bind("<ButtonRelease-1>", self._on_drag_end)

    def set_lock(self, value: bool) -> None:
        self._lock_overlay = value
        if value and self._on_drag_state_changed is not None:
            self._on_drag_state_changed(False)
        self._apply_interaction_lock()

    def set_text(self, active_profile_names: list[str], active: bool) -> None:
        if not active or not active_profile_names:
            shown = "None"
        elif len(active_profile_names) <= 2:
            shown = ", ".join(active_profile_names)
        else:
            shown = f"{active_profile_names[0]}, {active_profile_names[1]} +{len(active_profile_names) - 2}"
        text = f"Profiles: {shown}"
        if text != self._last_set_text:
            self.profile_label.configure(text=text)
            self._last_set_text = text
            self._resize_to_text(text)

    def get_position(self) -> tuple[int, int]:
        return self._center_x, self._center_y

    def set_position(self, x: int, y: int) -> None:
        self._center_x = int(x)
        self._center_y = int(y)
        self._resize_to_text(self.profile_label.cget("text"))

    def keep_topmost_without_focus(self) -> None:
        self._native.keep_topmost_without_focus()

    def _on_map(self, _event=None) -> None:
        self.after_idle(self._reapply_window_flags_after_map)

    def _reapply_window_flags_after_map(self) -> None:
        self._native.apply_toolwindow_hint(self.wm_attributes)
        self._apply_interaction_lock()

    def _on_destroy(self, _event=None) -> None:
        self._native.restore_wndproc()

    def _apply_interaction_lock(self) -> None:
        self._native.apply_interaction_lock()

    def _on_drag_start(self, event) -> None:
        if self._lock_overlay:
            return
        if self._on_drag_state_changed is not None:
            self._on_drag_state_changed(True)
        self._drag_origin_x = event.x_root
        self._drag_origin_y = event.y_root
        self._drag_window_origin_x = self.winfo_x()
        self._drag_window_origin_y = self.winfo_y()

    def _on_drag_move(self, event) -> None:
        if self._lock_overlay:
            return
        delta_x = event.x_root - self._drag_origin_x
        delta_y = event.y_root - self._drag_origin_y
        next_x = self._drag_window_origin_x + delta_x
        next_y = self._drag_window_origin_y + delta_y
        self.geometry(f"+{next_x}+{next_y}")
        now = time.monotonic()
        if now - self._last_drag_sync_monotonic >= 0.03:
            self._last_drag_sync_monotonic = now
            self._sync_center_from_current_geometry()
            if self._on_position_changed is not None:
                self._on_position_changed(self._center_x, self._center_y)

    def _on_drag_end(self, _event) -> None:
        if self._lock_overlay:
            return
        if self._on_drag_state_changed is not None:
            self._on_drag_state_changed(False)
        self._sync_center_from_current_geometry()
        if self._on_position_changed is not None:
            self._on_position_changed(self._center_x, self._center_y)

    def _resize_to_text(self, text: str) -> None:
        label_font = tkfont.nametofont(str(self.profile_label.cget("font")))
        text_width = label_font.measure(text)
        text_height = label_font.metrics("linespace")
        target_width = text_width + (14 * 2) + (6 * 2)
        target_height = text_height + (14 * 2) + (6 * 2)
        top_left_x = int(self._center_x - (target_width / 2))
        top_left_y = int(self._center_y - (target_height / 2))
        geometry = f"{target_width}x{target_height}+{top_left_x}+{top_left_y}"
        if geometry == self._last_geometry:
            return
        self._last_geometry = geometry
        self.geometry(geometry)

    def _sync_center_from_current_geometry(self) -> None:
        self._center_x = self.winfo_x() + (self.winfo_width() // 2)
        self._center_y = self.winfo_y() + (self.winfo_height() // 2)
