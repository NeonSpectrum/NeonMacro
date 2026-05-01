from __future__ import annotations

import customtkinter as ctk
from pathlib import Path
from tkinter import messagebox

from ..models import AppOptions
from .widget_state import set_checkbox_enabled, set_entry_enabled
from .window_icon import apply_window_icon


class OptionsDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTk,
        options: AppOptions,
        overlay_x: int,
        overlay_y: int,
        on_save,
    ) -> None:
        super().__init__(parent)
        self.title("Options")
        self.resizable(False, False)
        self.on_save = on_save
        self._window_icon_ico_path = None

        self.open_on_startup_var = ctk.BooleanVar(value=options.open_on_startup)
        self.minimize_to_tray_on_startup_var = ctk.BooleanVar(
            value=options.minimize_to_tray_on_startup
        )
        self.enable_overlay_var = ctk.BooleanVar(value=options.enable_overlay)
        self.lock_overlay_var = ctk.BooleanVar(value=options.lock_overlay)
        self.force_overlay_visible_var = ctk.BooleanVar(value=options.force_overlay_visible)
        self.allow_parallel_var = ctk.BooleanVar(value=options.allow_parallel)
        self.allow_background_var = ctk.BooleanVar(value=options.allow_background)
        self.auto_pause_stop_on_key_press_var = ctk.BooleanVar(
            value=options.auto_pause_stop_on_key_press
        )
        self.auto_pause_stop_duration_ms_var = ctk.StringVar(
            value=str(options.auto_pause_stop_duration_ms)
        )
        self.auto_pause_stop_keys_var = ctk.StringVar(value=";".join(options.auto_pause_stop_keys))
        self.restrict_profile_hotkeys_var = ctk.BooleanVar(
            value=options.restrict_profile_hotkeys_to_allowed_apps
        )
        self.allowed_apps_var = ctk.StringVar(value=";".join(options.allowed_applications))
        self.settings_toggle_hotkey_var = ctk.StringVar(value=options.settings_toggle_hotkey)
        self.overlay_x_var = ctk.StringVar(value=str(overlay_x))
        self.overlay_y_var = ctk.StringVar(value=str(overlay_y))
        self._autosave_job: str | None = None

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        startup_group = ctk.CTkFrame(body)
        startup_group.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(startup_group, text="Startup").pack(anchor="w", padx=10, pady=(8, 2))
        self.open_on_startup_checkbox = ctk.CTkCheckBox(
            startup_group,
            text="Open on startup",
            variable=self.open_on_startup_var,
        )
        self.open_on_startup_checkbox.pack(anchor="w", padx=10, pady=2)
        self.minimize_to_tray_on_startup_checkbox = ctk.CTkCheckBox(
            startup_group,
            text="Minimize to tray on startup",
            variable=self.minimize_to_tray_on_startup_var,
        )
        self.minimize_to_tray_on_startup_checkbox.pack(anchor="w", padx=10, pady=(2, 8))

        overlay_group = ctk.CTkFrame(body)
        overlay_group.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(overlay_group, text="Overlay").pack(anchor="w", padx=10, pady=(8, 2))
        self.enable_overlay_checkbox = ctk.CTkCheckBox(
            overlay_group,
            text="Enable overlay",
            variable=self.enable_overlay_var,
        )
        self.enable_overlay_checkbox.pack(
            anchor="w", padx=10, pady=2
        )
        self.lock_overlay_checkbox = ctk.CTkCheckBox(
            overlay_group,
            text="Click through overlay",
            variable=self.lock_overlay_var,
        )
        self.lock_overlay_checkbox.pack(
            anchor="w", padx=10, pady=(2, 6)
        )
        self.force_overlay_visible_checkbox = ctk.CTkCheckBox(
            overlay_group,
            text="Force overlay visible",
            variable=self.force_overlay_visible_var,
        )
        self.force_overlay_visible_checkbox.pack(anchor="w", padx=10, pady=(0, 6))
        self.overlay_coords_label = ctk.CTkLabel(overlay_group, text="Coordinates")
        self.overlay_coords_label.pack(anchor="w", padx=10, pady=(0, 2))
        coords_row = ctk.CTkFrame(overlay_group, fg_color="transparent")
        coords_row.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(coords_row, text="X").pack(side="left")
        self.overlay_x_entry = ctk.CTkEntry(coords_row, textvariable=self.overlay_x_var, width=80)
        self.overlay_x_entry.pack(
            side="left", padx=(6, 14)
        )
        ctk.CTkLabel(coords_row, text="Y").pack(side="left")
        self.overlay_y_entry = ctk.CTkEntry(coords_row, textvariable=self.overlay_y_var, width=80)
        self.overlay_y_entry.pack(
            side="left", padx=(6, 0)
        )
        self.overlay_save_button = ctk.CTkButton(
            coords_row,
            text="Save",
            width=80,
            command=self._save_overlay_position,
        )
        self.overlay_save_button.pack(side="right", padx=(8, 0))
        self.overlay_reset_button = ctk.CTkButton(
            coords_row,
            text="Reset",
            width=80,
            command=self._reset_overlay_position,
        )
        self.overlay_reset_button.pack(side="right", padx=(8, 0))

        spam_group = ctk.CTkFrame(body)
        spam_group.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(spam_group, text="Spam Settings").pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkCheckBox(spam_group, text="Allow parallel", variable=self.allow_parallel_var).pack(
            anchor="w", padx=10, pady=2
        )
        ctk.CTkCheckBox(
            spam_group,
            text="Allow background (spam key works when target app is not focused)",
            variable=self.allow_background_var,
        ).pack(anchor="w", padx=10, pady=2)
        self.auto_pause_stop_checkbox = ctk.CTkCheckBox(
            spam_group,
            text="Enable auto pause/stop when key press",
            variable=self.auto_pause_stop_on_key_press_var,
        )
        self.auto_pause_stop_checkbox.pack(anchor="w", padx=10, pady=2)
        pause_row = ctk.CTkFrame(spam_group, fg_color="transparent")
        pause_row.pack(fill="x", padx=10, pady=(0, 4))
        self.auto_pause_stop_duration_label = ctk.CTkLabel(
            pause_row, text="Pause duration (ms, -1 = full stop)"
        )
        self.auto_pause_stop_duration_label.pack(side="left")
        self.auto_pause_stop_duration_entry = ctk.CTkEntry(
            pause_row,
            textvariable=self.auto_pause_stop_duration_ms_var,
            width=100,
            placeholder_text="120",
        )
        self.auto_pause_stop_duration_entry.pack(side="left", padx=(8, 0))
        self.auto_pause_stop_keys_label = ctk.CTkLabel(
            spam_group, text="Auto pause/stop keys (semicolon separated)"
        )
        self.auto_pause_stop_keys_label.pack(
            anchor="w", padx=10, pady=(0, 0)
        )
        self.auto_pause_stop_keys_entry = ctk.CTkEntry(
            spam_group, textvariable=self.auto_pause_stop_keys_var, width=320
        )
        self.auto_pause_stop_keys_entry.pack(
            fill="x", padx=10, pady=(2, 8)
        )
        ctk.CTkCheckBox(
            spam_group,
            text="Profile hotkeys only work for allowed applications",
            variable=self.restrict_profile_hotkeys_var,
        ).pack(anchor="w", padx=10, pady=2)
        ctk.CTkLabel(spam_group, text="Application list (semicolon separated)").pack(
            anchor="w", padx=10
        )
        ctk.CTkEntry(spam_group, textvariable=self.allowed_apps_var, width=320).pack(
            fill="x", padx=10, pady=(2, 10)
        )
        ctk.CTkLabel(spam_group, text="Settings overlay hotkey").pack(anchor="w", padx=10)
        ctk.CTkEntry(
            spam_group,
            textvariable=self.settings_toggle_hotkey_var,
            width=320,
            placeholder_text="e.g. {F10}",
        ).pack(fill="x", padx=10, pady=(2, 10))

        self._register_autosave_callbacks()
        self.open_on_startup_var.trace_add("write", self._on_open_on_startup_changed)
        self.minimize_to_tray_on_startup_var.trace_add(
            "write", self._on_minimize_to_tray_on_startup_changed
        )
        self.enable_overlay_var.trace_add("write", self._on_enable_overlay_changed)
        self.force_overlay_visible_var.trace_add("write", self._on_force_overlay_visible_changed)
        self.auto_pause_stop_on_key_press_var.trace_add(
            "write", self._on_auto_pause_stop_toggle_changed
        )
        self._apply_startup_group_state()
        self._apply_overlay_group_state()
        self._apply_force_overlay_visible_state()
        self._apply_auto_pause_stop_state()
        self._apply_window_icon(parent)
        self.bind("<Destroy>", self._on_destroy, add="+")

    def iconbitmap(self, bitmap=None, default=None):
        if self._is_customtkinter_default_icon(bitmap):
            return None
        return super().iconbitmap(bitmap, default=default)

    def wm_iconbitmap(self, bitmap=None, default=None):
        if self._is_customtkinter_default_icon(bitmap):
            return None
        return super().wm_iconbitmap(bitmap, default=default)

    @staticmethod
    def _is_customtkinter_default_icon(bitmap) -> bool:
        if not bitmap:
            return False
        try:
            return Path(str(bitmap)).name.lower() == "customtkinter_icon_windows.ico"
        except Exception:
            return False

    def _apply_window_icon(self, parent: ctk.CTk) -> None:
        preferred_ico_path = getattr(parent, "_window_icon_ico_path", None)
        result = apply_window_icon(
            self,
            preferred_ico_path=preferred_ico_path,
        )
        self._window_icon_ico_path = result.ico_path

    def _build_options(self) -> AppOptions:
        apps = [item.strip() for item in self.allowed_apps_var.get().split(";") if item.strip()]
        pause_stop_keys = [
            item.strip() for item in self.auto_pause_stop_keys_var.get().split(";") if item.strip()
        ]
        pause_stop_ms = self._parse_pause_stop_ms()
        open_on_startup = self.open_on_startup_var.get()
        return AppOptions(
            open_on_startup=open_on_startup,
            minimize_to_tray_on_startup=(
                self.minimize_to_tray_on_startup_var.get() if open_on_startup else False
            ),
            enable_overlay=self.enable_overlay_var.get(),
            lock_overlay=self.lock_overlay_var.get(),
            force_overlay_visible=self.force_overlay_visible_var.get(),
            allow_parallel=self.allow_parallel_var.get(),
            allow_background=self.allow_background_var.get(),
            auto_pause_stop_on_key_press=self.auto_pause_stop_on_key_press_var.get(),
            auto_pause_stop_duration_ms=pause_stop_ms,
            auto_pause_stop_keys=pause_stop_keys,
            restrict_profile_hotkeys_to_allowed_apps=self.restrict_profile_hotkeys_var.get(),
            allowed_applications=apps,
            settings_toggle_hotkey=self.settings_toggle_hotkey_var.get().strip(),
        )

    def _parse_overlay_position(self) -> tuple[int, int] | None:
        try:
            overlay_x = int(self.overlay_x_var.get().strip())
            overlay_y = int(self.overlay_y_var.get().strip())
        except ValueError:
            return None
        return (overlay_x, overlay_y)

    def _parse_pause_stop_ms(self) -> int:
        raw = self.auto_pause_stop_duration_ms_var.get().strip()
        try:
            parsed = int(raw)
        except ValueError:
            return 120
        return max(-1, parsed)

    def _register_autosave_callbacks(self) -> None:
        watched_vars = (
            self.open_on_startup_var,
            self.minimize_to_tray_on_startup_var,
            self.enable_overlay_var,
            self.lock_overlay_var,
            self.force_overlay_visible_var,
            self.allow_parallel_var,
            self.allow_background_var,
            self.auto_pause_stop_on_key_press_var,
            self.auto_pause_stop_duration_ms_var,
            self.auto_pause_stop_keys_var,
            self.restrict_profile_hotkeys_var,
            self.allowed_apps_var,
            self.settings_toggle_hotkey_var,
        )
        for var in watched_vars:
            var.trace_add("write", self._schedule_autosave)

    def _schedule_autosave(self, *_args) -> None:
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(250, self._autosave_now)

    def _autosave_now(self) -> None:
        self._autosave_job = None
        options = self._build_options()
        overlay_position = self._parse_overlay_position()
        self.on_save(options, overlay_position)

    def _on_destroy(self, _event=None) -> None:
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
            self._autosave_job = None
            # Persist pending edits when the dialog is closed quickly.
            self._autosave_now()

    def _reset_overlay_position(self) -> None:
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        center_x = screen_w // 2
        center_y = screen_h // 2
        self.overlay_x_var.set(str(center_x))
        self.overlay_y_var.set(str(center_y))
        options = self._build_options()
        self.on_save(options, (center_x, center_y))

    def _save_overlay_position(self) -> None:
        overlay_position = self._parse_overlay_position()
        if overlay_position is None:
            messagebox.showerror("Options", "Overlay coordinates must be valid numbers.")
            return
        options = self._build_options()
        self.on_save(options, overlay_position)

    def _on_force_overlay_visible_changed(self, *_args) -> None:
        self._apply_force_overlay_visible_state()

    def _apply_force_overlay_visible_state(self) -> None:
        if not self.enable_overlay_var.get():
            set_checkbox_enabled(self.lock_overlay_checkbox, enabled=False)
            return
        if self.force_overlay_visible_var.get():
            set_checkbox_enabled(self.lock_overlay_checkbox, enabled=False)
            return
        set_checkbox_enabled(self.lock_overlay_checkbox, enabled=True)

    def _on_enable_overlay_changed(self, *_args) -> None:
        self._apply_overlay_group_state()

    def _apply_overlay_group_state(self) -> None:
        overlay_enabled = self.enable_overlay_var.get()
        set_checkbox_enabled(self.force_overlay_visible_checkbox, enabled=overlay_enabled)
        set_entry_enabled(self.overlay_x_entry, enabled=overlay_enabled)
        set_entry_enabled(self.overlay_y_entry, enabled=overlay_enabled)
        button_state = "normal" if overlay_enabled else "disabled"
        self.overlay_save_button.configure(state=button_state)
        self.overlay_reset_button.configure(state=button_state)
        self._apply_force_overlay_visible_state()

    def _on_auto_pause_stop_toggle_changed(self, *_args) -> None:
        self._apply_auto_pause_stop_state()

    def _on_open_on_startup_changed(self, *_args) -> None:
        self._apply_startup_group_state()
        self._save_startup_options_now()

    def _on_minimize_to_tray_on_startup_changed(self, *_args) -> None:
        self._save_startup_options_now()

    def _save_startup_options_now(self) -> None:
        options = self._build_options()
        overlay_position = self._parse_overlay_position()
        self.on_save(options, overlay_position)

    def _apply_startup_group_state(self) -> None:
        open_enabled = self.open_on_startup_var.get()
        if not open_enabled:
            self.minimize_to_tray_on_startup_var.set(False)
        set_checkbox_enabled(self.minimize_to_tray_on_startup_checkbox, enabled=open_enabled)

    def _apply_auto_pause_stop_state(self) -> None:
        enabled = self.auto_pause_stop_on_key_press_var.get()
        set_entry_enabled(self.auto_pause_stop_duration_entry, enabled=enabled)
        self.auto_pause_stop_duration_label.configure(
            text_color=self._section_text_color(enabled=enabled)
        )
        self.auto_pause_stop_keys_label.configure(
            text_color=self._section_text_color(enabled=enabled)
        )
        set_entry_enabled(self.auto_pause_stop_keys_entry, enabled=enabled)

    @staticmethod
    def _section_text_color(enabled: bool) -> str:
        label_theme = ctk.ThemeManager.theme.get("CTkLabel", {})
        text_color = label_theme.get("text_color", ("#DCE4EE", "#DCE4EE"))
        if enabled:
            return text_color
        return label_theme.get("text_color_disabled", "#7A7A7A")

