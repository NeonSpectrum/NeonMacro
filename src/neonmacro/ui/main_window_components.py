from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

import customtkinter as ctk


@dataclass
class TableWidgets:
    frame: ctk.CTkFrame
    tree: ttk.Treeview
    scrollbar: ctk.CTkScrollbar


@dataclass
class FormWidgets:
    name_entry: ctk.CTkEntry
    window_title_entry: ctk.CTkEntry
    interval_entry: ctk.CTkEntry
    hotkey_entry: ctk.CTkEntry
    spam_key_entry: ctk.CTkEntry
    use_regex_var: ctk.BooleanVar


@dataclass
class MainWindowWidgets:
    status_var: ctk.StringVar
    table: TableWidgets
    form: FormWidgets


def build_main_window_widgets(
    window: ctk.CTk,
    *,
    open_options,
    open_key_help,
    add_profile,
    update_profile,
    delete_profile,
    checkbox_col_width: int,
) -> MainWindowWidgets:
    window.grid_columnconfigure(0, weight=1)

    top = ctk.CTkFrame(window)
    top.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
    bottom = ctk.CTkFrame(window)
    bottom.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
    bottom.grid_columnconfigure(0, weight=1)

    header = ctk.CTkFrame(top, fg_color="transparent")
    header.pack(fill="x", padx=10, pady=(10, 6))
    status_var = ctk.StringVar(value="Current Spam: None | Status: Inactive")
    ctk.CTkLabel(header, textvariable=status_var, anchor="w").pack(side="left", anchor="w")
    ctk.CTkButton(header, text="Options", width=96, command=open_options).pack(
        side="right", anchor="e"
    )
    ctk.CTkButton(header, text="Help", width=80, command=open_key_help).pack(
        side="right", anchor="e", padx=(0, 6)
    )

    table_frame = ctk.CTkFrame(top, fg_color="transparent")
    table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

    columns = ("name", "window_title", "interval", "hotkey", "spam_key")
    profile_table = ttk.Treeview(
        table_frame,
        columns=columns,
        show=("tree", "headings"),
        selectmode="browse",
        style="Neon.Treeview",
    )
    profile_table.heading("#0", text="")
    profile_table.column("#0", width=checkbox_col_width, anchor="center", stretch=False)
    profile_table.heading("name", text="Name")
    profile_table.heading("window_title", text="Window Title")
    profile_table.heading("interval", text="Interval")
    profile_table.heading("hotkey", text="Hotkey")
    profile_table.heading("spam_key", text="Spam Key")
    profile_table.column("name", width=180, anchor="w")
    profile_table.column("window_title", width=340, anchor="w")
    profile_table.column("interval", width=110, anchor="center")
    profile_table.column("hotkey", width=150, anchor="center")
    profile_table.column("spam_key", width=100, anchor="center")

    table_scroll_y = ctk.CTkScrollbar(
        table_frame,
        orientation="vertical",
        command=profile_table.yview,
        width=10,
    )
    profile_table.grid(row=0, column=0, sticky="nsew")
    table_scroll_y.grid(row=0, column=1, sticky="ns", padx=(6, 0))
    table_frame.grid_columnconfigure(0, weight=1)
    table_frame.grid_rowconfigure(0, weight=1)

    use_regex_var = ctk.BooleanVar(value=False)

    ctk.CTkLabel(bottom, text="Profile Name").grid(row=1, column=0, sticky="w", padx=10, pady=(10, 2))
    name_entry = ctk.CTkEntry(bottom, placeholder_text="Enter profile name...")
    name_entry.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))

    ctk.CTkLabel(bottom, text="Window Title / Regex").grid(row=3, column=0, sticky="w", padx=10, pady=(0, 2))
    window_title_entry = ctk.CTkEntry(bottom, placeholder_text="Enter window title...")
    window_title_entry.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 4))

    ctk.CTkCheckBox(bottom, text="Use regex", variable=use_regex_var).grid(
        row=5, column=0, sticky="w", padx=10, pady=(0, 8)
    )

    ctk.CTkLabel(bottom, text="Interval (ms)").grid(row=6, column=0, sticky="w", padx=10, pady=(0, 2))
    interval_entry = ctk.CTkEntry(bottom, placeholder_text="Enter interval (ms)...")
    interval_entry.grid(row=7, column=0, sticky="ew", padx=10, pady=(0, 8))

    ctk.CTkLabel(bottom, text="Hotkey (e.g., {CTRL}{F1}, {CTRL}1, {CTRL}`)").grid(
        row=8, column=0, sticky="w", padx=10, pady=(0, 2)
    )
    hotkey_entry = ctk.CTkEntry(bottom, placeholder_text="Enter hotkey...")
    hotkey_entry.grid(row=9, column=0, sticky="ew", padx=10, pady=(0, 8))

    ctk.CTkLabel(bottom, text="Spam Key (single key, e.g., {F1}, A, /)").grid(
        row=10, column=0, sticky="w", padx=10, pady=(0, 2)
    )
    spam_key_entry = ctk.CTkEntry(bottom, placeholder_text="Enter spam key...")
    spam_key_entry.grid(row=11, column=0, sticky="ew", padx=10, pady=(0, 8))

    button_row = ctk.CTkFrame(bottom, fg_color="transparent")
    button_row.grid(row=12, column=0, sticky="ew", padx=10, pady=(8, 16))
    ctk.CTkButton(button_row, text="Add", command=add_profile).pack(side="left")
    ctk.CTkButton(button_row, text="Update", command=update_profile).pack(side="left", padx=6)
    ctk.CTkButton(button_row, text="Delete", command=delete_profile).pack(side="left")

    return MainWindowWidgets(
        status_var=status_var,
        table=TableWidgets(frame=table_frame, tree=profile_table, scrollbar=table_scroll_y),
        form=FormWidgets(
            name_entry=name_entry,
            window_title_entry=window_title_entry,
            interval_entry=interval_entry,
            hotkey_entry=hotkey_entry,
            spam_key_entry=spam_key_entry,
            use_regex_var=use_regex_var,
        ),
    )
