from __future__ import annotations

import customtkinter as ctk

from ..models import AppOptions


class OptionsDialog(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk, options: AppOptions, on_save) -> None:
        super().__init__(parent)
        self.title("Options")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.on_save = on_save

        self.enable_overlay_var = ctk.BooleanVar(value=options.enable_overlay)
        self.lock_overlay_var = ctk.BooleanVar(value=options.lock_overlay)
        self.allowed_apps_var = ctk.StringVar(value=";".join(options.allowed_applications))

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkCheckBox(body, text="Enable overlay", variable=self.enable_overlay_var).pack(
            anchor="w", pady=2
        )
        ctk.CTkCheckBox(body, text="Lock overlay", variable=self.lock_overlay_var).pack(
            anchor="w", pady=(2, 10)
        )

        ctk.CTkLabel(body, text="Application list (semicolon separated)").pack(anchor="w")
        ctk.CTkEntry(body, textvariable=self.allowed_apps_var, width=320).pack(
            fill="x", pady=(2, 10)
        )

        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkButton(btns, text="Save", command=self._save).pack(side="right")

    def _save(self) -> None:
        apps = [item.strip() for item in self.allowed_apps_var.get().split(";") if item.strip()]
        options = AppOptions(
            enable_overlay=self.enable_overlay_var.get(),
            lock_overlay=self.lock_overlay_var.get(),
            allowed_applications=apps,
        )
        self.on_save(options)
        self.destroy()

