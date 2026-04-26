from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from ..models import AppOptions


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

        self.enable_overlay_var = ctk.BooleanVar(value=options.enable_overlay)
        self.lock_overlay_var = ctk.BooleanVar(value=options.lock_overlay)
        self.allow_parallel_var = ctk.BooleanVar(value=options.allow_parallel)
        self.auto_stop_on_key_press_var = ctk.BooleanVar(value=options.auto_stop_on_key_press)
        self.auto_stop_keys_var = ctk.StringVar(value=";".join(options.auto_stop_keys))
        self.allowed_apps_var = ctk.StringVar(value=";".join(options.allowed_applications))
        self.overlay_x_var = ctk.StringVar(value=str(overlay_x))
        self.overlay_y_var = ctk.StringVar(value=str(overlay_y))

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        overlay_group = ctk.CTkFrame(body)
        overlay_group.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(overlay_group, text="Overlay").pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkCheckBox(overlay_group, text="Enable overlay", variable=self.enable_overlay_var).pack(
            anchor="w", padx=10, pady=2
        )
        ctk.CTkCheckBox(overlay_group, text="Click through overlay", variable=self.lock_overlay_var).pack(
            anchor="w", padx=10, pady=(2, 6)
        )
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

        spam_group = ctk.CTkFrame(body)
        spam_group.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(spam_group, text="Spam Settings").pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkCheckBox(spam_group, text="Allow parallel", variable=self.allow_parallel_var).pack(
            anchor="w", padx=10, pady=2
        )
        ctk.CTkCheckBox(
            spam_group,
            text="Enable auto stop when key press",
            variable=self.auto_stop_on_key_press_var,
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

        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkButton(btns, text="Save", command=self._save).pack(side="right")

    def _save(self) -> None:
        try:
            overlay_x = int(self.overlay_x_var.get().strip())
            overlay_y = int(self.overlay_y_var.get().strip())
        except ValueError:
            messagebox.showerror("Options", "Overlay X and Y must be valid integers.")
            return
        apps = [item.strip() for item in self.allowed_apps_var.get().split(";") if item.strip()]
        stop_keys = [item.strip() for item in self.auto_stop_keys_var.get().split(";") if item.strip()]
        options = AppOptions(
            enable_overlay=self.enable_overlay_var.get(),
            lock_overlay=self.lock_overlay_var.get(),
            allow_parallel=self.allow_parallel_var.get(),
            auto_stop_on_key_press=self.auto_stop_on_key_press_var.get(),
            auto_stop_keys=stop_keys,
            allowed_applications=apps,
        )
        self.on_save(options, (overlay_x, overlay_y))
        self.destroy()

