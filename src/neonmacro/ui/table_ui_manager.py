from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk


class TableUiManager:
    def __init__(
        self,
        root: ctk.CTk,
        table: ttk.Treeview,
        scrollbar: ctk.CTkScrollbar,
        *,
        column_ratios: dict[str, float],
        column_min_widths: dict[str, int],
        checkbox_col_width: int,
    ) -> None:
        self._root = root
        self._table = table
        self._scrollbar = scrollbar
        self._column_ratios = column_ratios
        self._column_min_widths = column_min_widths
        self._checkbox_col_width = checkbox_col_width
        self._table_scroll_visible = True
        self._checkbox_images: dict[bool, tk.PhotoImage] = {}
        self._last_appearance_mode: str = ""

    @property
    def checkbox_images(self) -> dict[bool, tk.PhotoImage]:
        return self._checkbox_images

    @property
    def last_appearance_mode(self) -> str:
        return self._last_appearance_mode

    def apply_theme(self) -> None:
        appearance = ctk.get_appearance_mode().lower()
        is_dark = appearance == "dark"

        if is_dark:
            bg = "#1f1f1f"
            fg = "#f2f2f2"
            heading_bg = "#2a2a2a"
            selected_bg = "#1f6aa5"
        else:
            bg = "#ffffff"
            fg = "#111111"
            heading_bg = "#ececec"
            selected_bg = "#2f80ed"

        style = ttk.Style(self._root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(
            "Neon.Treeview",
            background=bg,
            fieldbackground=bg,
            foreground=fg,
            rowheight=30,
            borderwidth=0,
        )
        style.configure(
            "Neon.Treeview.Heading",
            background=heading_bg,
            foreground=fg,
            relief="flat",
        )
        style.map(
            "Neon.Treeview",
            background=[("selected", selected_bg)],
            foreground=[("selected", "#ffffff")],
        )
        style.map(
            "Neon.Treeview.Heading",
            background=[("active", heading_bg)],
            foreground=[("active", fg)],
        )
        self._last_appearance_mode = appearance

    def build_checkbox_images(self) -> None:
        self._checkbox_images = {
            False: self._create_checkbox_image(checked=False),
            True: self._create_checkbox_image(checked=True),
        }

    def _create_checkbox_image(self, checked: bool) -> tk.PhotoImage:
        image = tk.PhotoImage(width=18, height=18)
        image.put("#9ca3af", to=(0, 0, 17, 17))
        image.put("#ffffff", to=(1, 1, 16, 16))
        if checked:
            image.put("#22c55e", to=(1, 1, 16, 16))
            check_points = [
                (3, 9), (4, 10), (5, 11), (6, 12), (7, 13),
                (8, 12), (9, 11), (10, 10), (11, 9),
                (12, 8), (13, 7), (14, 6), (15, 5),
            ]
            for x, y in check_points:
                image.put("#14532d", to=(x, y, x, y))
                if y + 1 < 18:
                    image.put("#14532d", to=(x, y + 1, x, y + 1))
        return image

    def on_table_resize(self, _event=None) -> None:
        self.apply_responsive_column_widths()
        self.update_scrollbar_visibility()

    def on_table_mapped(self, _event=None) -> None:
        self._root.after_idle(self.apply_responsive_column_widths)
        self._root.after_idle(self.update_scrollbar_visibility)

    def on_table_yscroll(self, first: str, last: str) -> None:
        self._scrollbar.set(first, last)
        self.update_scrollbar_visibility(first, last)

    def update_scrollbar_visibility(
        self,
        first: str | float | None = None,
        last: str | float | None = None,
    ) -> None:
        if first is None or last is None:
            first, last = self._table.yview()
        first_f = float(first)
        last_f = float(last)
        should_show = (last_f - first_f) < 0.999999
        if should_show == self._table_scroll_visible:
            return
        self._table_scroll_visible = should_show
        if should_show:
            self._scrollbar.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        else:
            self._scrollbar.grid_remove()

    def apply_responsive_column_widths(self) -> None:
        total_width = max(1, self._table.winfo_width() - self._checkbox_col_width)
        columns = ("name", "window_title", "interval", "hotkey", "spam_key")
        computed: dict[str, int] = {}
        used = 0
        for column in columns[:-1]:
            width = int(total_width * self._column_ratios[column])
            width = max(self._column_min_widths[column], width)
            computed[column] = width
            used += width
        last = columns[-1]
        computed[last] = max(self._column_min_widths[last], total_width - used)

        for column in columns:
            self._table.column(column, width=computed[column], stretch=True)
