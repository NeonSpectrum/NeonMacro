from __future__ import annotations

import customtkinter as ctk


def entry_text_colors() -> tuple[str | tuple[str, str], str]:
    entry_theme = ctk.ThemeManager.theme.get("CTkEntry", {})
    enabled_text_color = entry_theme.get("text_color", ("#DCE4EE", "#DCE4EE"))
    disabled_text_color = "#7A7A7A"
    return enabled_text_color, disabled_text_color


def set_entry_enabled(entry: ctk.CTkEntry, enabled: bool) -> None:
    enabled_text_color, disabled_text_color = entry_text_colors()
    entry.configure(
        state="normal" if enabled else "disabled",
        text_color=enabled_text_color if enabled else disabled_text_color,
    )


def checkbox_fg_colors() -> tuple[str | tuple[str, str], str]:
    checkbox_theme = ctk.ThemeManager.theme.get("CTkCheckBox", {})
    enabled_fg_color = checkbox_theme.get("fg_color", ("#3B8ED0", "#1F6AA5"))
    disabled_fg_color = "#7A7A7A"
    return enabled_fg_color, disabled_fg_color


def set_checkbox_enabled(checkbox: ctk.CTkCheckBox, enabled: bool) -> None:
    enabled_fg_color, disabled_fg_color = checkbox_fg_colors()
    checkbox.configure(
        state="normal" if enabled else "disabled",
        fg_color=enabled_fg_color if enabled else disabled_fg_color,
    )
