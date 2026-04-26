from __future__ import annotations

import customtkinter as ctk
from pathlib import Path
from tkinter import messagebox

from ..models import AppOptions
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

        self.enable_overlay_var = ctk.BooleanVar(value=options.enable_overlay)
        self.lock_overlay_var = ctk.BooleanVar(value=options.lock_overlay)
        self.force_overlay_visible_var = ctk.BooleanVar(value=options.force_overlay_visible)
        self.allow_parallel_var = ctk.BooleanVar(value=options.allow_parallel)
        self.allow_background_var = ctk.BooleanVar(value=options.allow_background)
        self.auto_stop_on_key_press_var = ctk.BooleanVar(value=options.auto_stop_on_key_press)
        self.restrict_profile_hotkeys_var = ctk.BooleanVar(
            value=options.restrict_profile_hotkeys_to_allowed_apps
        )
        self.auto_stop_keys_var = ctk.StringVar(value=";".join(options.auto_stop_keys))
        self.allowed_apps_var = ctk.StringVar(value=";".join(options.allowed_applications))
        self.settings_toggle_hotkey_var = ctk.StringVar(value=options.settings_toggle_hotkey)
        self.overlay_x_var = ctk.StringVar(value=str(overlay_x))
        self.overlay_y_var = ctk.StringVar(value=str(overlay_y))
        self._autosave_job: str | None = None

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        overlay_group = ctk.CTkFrame(body)
        overlay_group.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(overlay_group, text="Overlay").pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkCheckBox(overlay_group, text="Enable overlay", variable=self.enable_overlay_var).pack(
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
        ctk.CTkCheckBox(
            overlay_group,
            text="Force overlay visible",
            variable=self.force_overlay_visible_var,
        ).pack(anchor="w", padx=10, pady=(0, 6))
        ctk.CTkLabel(overlay_group, text="Coordinates").pack(anchor="w", padx=10, pady=(0, 2))
        coords_row = ctk.CTkFrame(overlay_group, fg_color="transparent")
        coords_row.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(coords_row, text="X").pack(side="left")
        ctk.CTkEntry(coords_row, textvariable=self.overlay_x_var, width=80).pack(
            side="left", padx=(6, 14)
        )
        ctk.CTkLabel(coords_row, text="Y").pack(side="left")
        ctk.CTkEntry(coords_row, textvariable=self.overlay_y_var, width=80).pack(
            side="left", padx=(6, 0)
        )
        ctk.CTkButton(
            coords_row,
            text="Save",
            width=80,
            command=self._save_overlay_position,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            coords_row,
            text="Reset",
            width=80,
            command=self._reset_overlay_position,
        ).pack(side="right", padx=(8, 0))

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
        ctk.CTkCheckBox(
            spam_group,
            text="Enable auto stop when key press",
            variable=self.auto_stop_on_key_press_var,
        ).pack(anchor="w", padx=10, pady=2)
        ctk.CTkCheckBox(
            spam_group,
            text="Profile hotkeys only work for allowed applications",
            variable=self.restrict_profile_hotkeys_var,
        ).pack(anchor="w", padx=10, pady=2)
        ctk.CTkLabel(spam_group, text="Auto stop keys (semicolon separated)").pack(
            anchor="w", padx=10, pady=(4, 0)
        )
        ctk.CTkEntry(spam_group, textvariable=self.auto_stop_keys_var, width=320).pack(
            fill="x", padx=10, pady=(2, 8)
        )
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
        self.force_overlay_visible_var.trace_add("write", self._on_force_overlay_visible_changed)
        self._apply_force_overlay_visible_state()
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
        stop_keys = [item.strip() for item in self.auto_stop_keys_var.get().split(";") if item.strip()]
        return AppOptions(
            enable_overlay=self.enable_overlay_var.get(),
            lock_overlay=self.lock_overlay_var.get(),
            force_overlay_visible=self.force_overlay_visible_var.get(),
            allow_parallel=self.allow_parallel_var.get(),
            allow_background=self.allow_background_var.get(),
            auto_stop_on_key_press=self.auto_stop_on_key_press_var.get(),
            restrict_profile_hotkeys_to_allowed_apps=self.restrict_profile_hotkeys_var.get(),
            auto_stop_keys=stop_keys,
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

    def _register_autosave_callbacks(self) -> None:
        watched_vars = (
            self.enable_overlay_var,
            self.lock_overlay_var,
            self.force_overlay_visible_var,
            self.allow_parallel_var,
            self.allow_background_var,
            self.auto_stop_on_key_press_var,
            self.restrict_profile_hotkeys_var,
            self.auto_stop_keys_var,
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
        if self.force_overlay_visible_var.get():
            self.lock_overlay_checkbox.configure(state="disabled")
            return
        self.lock_overlay_checkbox.configure(state="normal")

