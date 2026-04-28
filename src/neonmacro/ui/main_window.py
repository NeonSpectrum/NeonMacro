from __future__ import annotations

import re
import logging
import tkinter as tk
import time
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import win32gui

from ..core.config import ConfigStore
from ..core.hotkeys import HotkeyManager
from ..core.keymaps import normalize_spam_key_combo
from ..models import AppOptions, SpamProfile
from ..core.overlay import OverlayWindow
from ..services.profile_service import (
    build_status_view,
    enforce_parallel_profile_policy,
    sanitize_startup_hotkeys,
    validate_profile_uniqueness,
)
from ..core.spam_engine import EngineStatus, SpamEngine
from .dialogs import OptionsDialog
from .main_window_components import build_main_window_widgets
from .overlay_controller import (
    active_profiles_matching_title,
    get_foreground_context,
    is_allowed_application_focused,
)
from .table_ui_manager import TableUiManager
from .window_icon import apply_window_icon

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.title("NeonMacro")
        self._window_icon_ico_path: str | None = None
        self._apply_window_icon()
        self._default_width = 600
        self._default_height = 700
        self._minimum_width = 500
        self._table_panel_min_height = 180
        self._details_panel_min_height = 360
        self._outer_vertical_padding = 100
        self.minsize(self._minimum_width, self._minimum_window_height())

        self._store = ConfigStore(config_path)
        self._config = self._store.load()
        self._apply_initial_window_geometry()

        self._engine = SpamEngine(
            # Spam delivery can be constrained to the foreground app when
            # background mode is disabled in Spam Settings.
            allowed_executables_supplier=self._spam_allowed_executables,
            on_tick=self._on_engine_tick,
            on_error=self._on_engine_error,
        )
        self._hotkeys = HotkeyManager(
            on_profile_hotkey=self._on_profile_selected_by_hotkey,
            on_auto_stop_hotkey=self._on_auto_stop_hotkey,
            on_settings_toggle_hotkey=self._on_settings_toggle_hotkey,
        )
        self._overlay = OverlayWindow(
            self,
            x=self._config.overlay.x,
            y=self._config.overlay.y,
            lock_overlay=self._config.options.lock_overlay,
            on_position_changed=self._on_overlay_position_changed,
            on_drag_state_changed=self._on_overlay_drag_state_changed,
        )
        self._overlay_sync_job: str | None = None
        self._theme_sync_job: str | None = None
        self._config_save_job: str | None = None
        self._pending_overlay_center: tuple[int, int] | None = None
        self._overlay_is_dragging = False
        self._options_dialog: OptionsDialog | None = None
        self._options_return_focus_hwnd: int | None = None
        self._last_engine_error_message: str = ""
        self._last_engine_error_at: float = 0.0
        self._column_ratios: dict[str, float] = {
            "name": 0.25,
            "window_title": 0.30,
            "interval": 0.11,
            "hotkey": 0.16,
            "spam_key": 0.12,
        }
        self._column_min_widths: dict[str, int] = {
            "name": 150,
            "window_title": 180,
            "interval": 90,
            "hotkey": 110,
            "spam_key": 90,
        }
        self._checkbox_col_width = 52

        self._selected_profile_name: str | None = None
        self._dragged_row_id: str | None = None
        self._row_drag_in_progress = False
        self._table_drag_cursor = "fleur"
        self._drag_status_text: str | None = None
        self._overlay_has_active_spam = False
        self._last_overlay_visible: bool | None = None
        self._last_overlay_text: tuple[str, ...] = ()
        self._startup_hotkey_issues: list[str] = []
        self._sanitize_profile_hotkeys_on_startup()
        self._build_layout()
        self._apply_table_theme()
        self._bind_events()
        self._refresh_profile_list()
        self._apply_active_profiles_state()
        try:
            self._apply_options()
        except ValueError as exc:
            messagebox.showerror("Hotkey validation", str(exc))
        self._engine.start()
        self._schedule_overlay_sync()
        self._schedule_theme_sync()
        if self._startup_hotkey_issues:
            details = "\n".join(f"- {item}" for item in self._startup_hotkey_issues)
            messagebox.showerror(
                "Hotkey validation",
                "Some profile hotkeys were removed because they are unavailable:\n\n"
                f"{details}",
            )

    def _apply_window_icon(self) -> None:
        result = apply_window_icon(self, apply_default_icon=True)
        self._window_icon_ico_path = result.ico_path

    def _center_on_screen(self, width: int, height: int) -> None:
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _minimum_window_height(self) -> int:
        return (
            self._table_panel_min_height
            + self._details_panel_min_height
            + self._outer_vertical_padding
        )

    def _apply_initial_window_geometry(self) -> None:
        width = self._coerce_window_width(self._config.window_width)
        height = self._coerce_window_height(self._config.window_height)
        x = self._config.window_x
        y = self._config.window_y
        if x is None or y is None:
            self.geometry(f"{width}x{height}")
            self._center_on_screen(width, height)
            return
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _coerce_window_width(self, value: int | None) -> int:
        if value is None:
            return self._default_width
        return max(self._minimum_width, value)

    def _coerce_window_height(self, value: int | None) -> int:
        if value is None:
            return self._default_height
        return max(self._minimum_window_height(), value)

    def _apply_table_theme(self) -> None:
        self._table_ui.apply_theme()

    def _sanitize_profile_hotkeys_on_startup(self) -> None:
        removed_any, issues = sanitize_startup_hotkeys(
            profiles=self._config.profiles,
            normalize_hotkey=self._hotkeys.normalize_hotkey,
            can_bind_hotkey=self._hotkeys.can_bind_hotkey,
        )
        self._startup_hotkey_issues.extend(issues)
        if removed_any:
            self._store.save(self._config)

    def _build_layout(self) -> None:
        # Keep the form section stable; let the table section absorb resize first.
        self.grid_rowconfigure(0, weight=1, minsize=self._table_panel_min_height)
        self.grid_rowconfigure(1, weight=0, minsize=self._details_panel_min_height)
        widgets = build_main_window_widgets(
            self,
            open_options=self._open_options,
            open_key_help=self._open_key_help,
            add_profile=self._add_profile,
            update_profile=self._update_selected,
            delete_profile=self._delete_selected,
            checkbox_col_width=self._checkbox_col_width,
        )
        self.status_var = widgets.status_var
        self.profile_table = widgets.table.tree
        self._table_scroll_y = widgets.table.scrollbar
        self.use_regex_var = widgets.form.use_regex_var
        self.name_entry = widgets.form.name_entry
        self.window_title_entry = widgets.form.window_title_entry
        self.interval_entry = widgets.form.interval_entry
        self.hotkey_entry = widgets.form.hotkey_entry
        self.spam_key_entry = widgets.form.spam_key_entry
        self.update_button = widgets.update_button
        self.delete_button = widgets.delete_button

        self._table_ui = TableUiManager(
            root=self,
            table=self.profile_table,
            scrollbar=self._table_scroll_y,
            column_ratios=self._column_ratios,
            column_min_widths=self._column_min_widths,
            checkbox_col_width=self._checkbox_col_width,
        )
        self.profile_table.bind("<Configure>", self._table_ui.on_table_resize, add="+")
        self.profile_table.bind("<Map>", self._table_ui.on_table_mapped, add="+")
        self.profile_table.configure(yscrollcommand=self._table_ui.on_table_yscroll)
        self._table_ui.build_checkbox_images()
        self.after_idle(self._table_ui.apply_responsive_column_widths)
        self.after_idle(self._table_ui.update_scrollbar_visibility)

    def _bind_events(self) -> None:
        self.profile_table.bind("<<TreeviewSelect>>", self._on_table_selected)
        self.profile_table.bind("<ButtonPress-1>", self._on_table_press, add="+")
        self.profile_table.bind("<B1-Motion>", self._on_table_drag, add="+")
        self.profile_table.bind("<ButtonRelease-1>", self._on_table_release, add="+")
        self.profile_table.bind("<Button-1>", self._on_table_click, add="+")
        self.bind("<Configure>", self._on_window_configure, add="+")
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _on_window_configure(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        self._save_config_debounced(delay_ms=300)

    def _open_options(
        self,
        center_on_window_rect: tuple[int, int, int, int] | None = None,
        topmost: bool = False,
        return_focus_hwnd: int | None = None,
    ) -> None:
        if self._options_dialog is not None and self._options_dialog.winfo_exists():
            self._options_dialog.lift()
            self._options_dialog.focus_force()
            return
        dialog = OptionsDialog(
            self,
            self._config.options,
            overlay_x=self._config.overlay.x,
            overlay_y=self._config.overlay.y,
            on_save=self._save_options,
        )
        self._options_dialog = dialog
        self._options_return_focus_hwnd = return_focus_hwnd
        dialog.bind("<Destroy>", self._on_options_dialog_destroyed, add="+")
        dialog.transient(self)
        if center_on_window_rect is None:
            self._center_dialog_on_parent(dialog)
        else:
            self._center_dialog_on_rect(dialog, center_on_window_rect)
        if topmost:
            dialog.attributes("-topmost", True)
        self._set_modal_popup(dialog)

    def _toggle_settings_overlay(self) -> None:
        if self._options_dialog is not None and self._options_dialog.winfo_exists():
            self._options_dialog.destroy()
            return
        if self.state() == "iconic":
            self.deiconify()
        self.lift()
        self.focus_force()
        self._open_options()

    def _toggle_settings_overlay_on_allowed_app(self) -> None:
        if self._options_dialog is not None and self._options_dialog.winfo_exists():
            return_focus_hwnd = self._options_return_focus_hwnd
            self._options_dialog.destroy()
            if return_focus_hwnd:
                self.after(0, lambda: self._restore_foreground_focus(return_focus_hwnd))
            return
        foreground = get_foreground_context()
        if foreground is None:
            return
        if not is_allowed_application_focused(self._config.options, foreground.exe_name):
            return
        try:
            left, top, right, bottom = win32gui.GetWindowRect(foreground.hwnd)
        except win32gui.error:
            return
        self._open_options(
            center_on_window_rect=(left, top, right, bottom),
            topmost=True,
            return_focus_hwnd=foreground.hwnd,
        )

    def _open_key_help(self) -> None:
        symbols = "` ~ ! @ # $ % ^ & * ( ) - _ = + [ ] { } \\ | ; : ' \" , < . > / ?"
        text = (
            "Spam keys\n"
            "- Allowed: 0-9, A-Z, {F1}-{F24}, symbols, named keys, and mouse buttons.\n"
            "- Symbols: "
            f"{symbols}\n"
            "- Named keys: {DEL} {INS} {PGUP} {PGDN} {HOME} {END} {RETURN} {ESCAPE} {BACKSPACE} {TAB} {PRTSCN} {PAUSE} {SPACE} {CAPSLOCK} {NUMLOCK} {SCROLLLOCK} {BREAK} {CTRLBREAK}\n"
            "- Mouse: {LMB}, {RMB}, {MMB}, {MB4}, {MB5}\n"
            "- Rule: spam key must be exactly one key with no modifier.\n"
            "- Examples: {F1}, A, 7, /, `, {LMB}, {DEL}, {PRTSCN}\n\n"
            "Hotkey input\n"
            "- Format: append one key after optional modifiers.\n"
            "- Modifiers: {CTRL} {RCTRL} {ALT} {RALT} {SHIFT} {RSHIFT} {LWIN} {RWIN} {APPS}\n"
            "- Keys: letters/numbers, symbols, {F1}-{F24}, and the same named keys listed above.\n"
            "- Mouse buttons: {LMB}, {RMB}, {MMB}, {MB4}, {MB5}\n"
            "- Examples: {CTRL}{F1}, {CTRL}1, {CTRL}`, {RALT}{LMB}, {APPS}A, {CTRL}{DEL}"
        )
        messagebox.showinfo("Key Input Help", text)

    def _set_modal_popup(self, dialog: tk.Toplevel) -> None:
        # Make popups modal so interactions stay within the popup window.
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()

    def _on_options_dialog_destroyed(self, _event=None) -> None:
        try:
            if self.grab_current() is self._options_dialog:
                self.grab_release()
        except tk.TclError:
            pass
        self._options_dialog = None
        self._options_return_focus_hwnd = None

    def _restore_foreground_focus(self, hwnd: int) -> None:
        try:
            if hwnd == int(self.winfo_id()):
                return
            if not win32gui.IsWindow(hwnd):
                return
            win32gui.SetForegroundWindow(hwnd)
        except (ValueError, tk.TclError, win32gui.error):
            return

    def _center_dialog_on_parent(self, dialog: tk.Toplevel) -> None:
        self.update_idletasks()
        dialog.update_idletasks()

        parent_x = self.winfo_rootx()
        parent_y = self.winfo_rooty()
        parent_w = self.winfo_width()
        parent_h = self.winfo_height()
        dialog_w = max(dialog.winfo_width(), dialog.winfo_reqwidth())
        dialog_h = max(dialog.winfo_height(), dialog.winfo_reqheight())

        x = parent_x + max(0, (parent_w - dialog_w) // 2)
        y = parent_y + max(0, (parent_h - dialog_h) // 2)

        # Clamp within the virtual desktop so multi-monitor coordinates
        # (including negative x/y on left/top monitors) are respected.
        virtual_x = self.winfo_vrootx()
        virtual_y = self.winfo_vrooty()
        virtual_w = self.winfo_vrootwidth()
        virtual_h = self.winfo_vrootheight()
        max_x = virtual_x + virtual_w - dialog_w
        max_y = virtual_y + virtual_h - dialog_h
        x = max(virtual_x, min(x, max_x))
        y = max(virtual_y, min(y, max_y))
        dialog.geometry(f"+{x}+{y}")

    def _center_dialog_on_rect(
        self,
        dialog: tk.Toplevel,
        rect: tuple[int, int, int, int],
    ) -> None:
        self.update_idletasks()
        dialog.update_idletasks()
        left, top, right, bottom = rect
        rect_w = max(1, right - left)
        rect_h = max(1, bottom - top)
        dialog_w = max(dialog.winfo_width(), dialog.winfo_reqwidth())
        dialog_h = max(dialog.winfo_height(), dialog.winfo_reqheight())
        x = left + max(0, (rect_w - dialog_w) // 2)
        y = top + max(0, (rect_h - dialog_h) // 2)
        virtual_x = self.winfo_vrootx()
        virtual_y = self.winfo_vrooty()
        virtual_w = self.winfo_vrootwidth()
        virtual_h = self.winfo_vrootheight()
        max_x = virtual_x + virtual_w - dialog_w
        max_y = virtual_y + virtual_h - dialog_h
        x = max(virtual_x, min(x, max_x))
        y = max(virtual_y, min(y, max_y))
        dialog.geometry(f"+{x}+{y}")

    def _save_options(
        self,
        options: AppOptions,
        overlay_position: tuple[int, int] | None = None,
    ) -> None:
        previous_options = self._config.options
        previous_overlay = (self._config.overlay.x, self._config.overlay.y)
        self._config.options = options
        if overlay_position is not None:
            self._config.overlay.x, self._config.overlay.y = overlay_position
        try:
            self._apply_options()
            if overlay_position is not None:
                self._overlay.set_position(self._config.overlay.x, self._config.overlay.y)
        except ValueError as exc:
            self._config.options = previous_options
            self._config.overlay.x, self._config.overlay.y = previous_overlay
            self._apply_options()
            self._overlay.set_position(self._config.overlay.x, self._config.overlay.y)
            messagebox.showerror("Options", str(exc))
            return
        self._refresh_profile_list(selected_name=self._selected_profile_name)
        self._apply_active_profiles_state()
        self._save_config_debounced()

    def _apply_options(self) -> None:
        self._enforce_parallel_profile_policy()
        self._hotkeys.apply_profile_hotkeys(self._config.profiles)
        self._hotkeys.apply_auto_stop_hotkeys(
            enabled=self._config.options.auto_stop_on_key_press,
            stop_keys=self._config.options.auto_stop_keys,
        )
        settings_hotkey = self._hotkeys.normalize_hotkey(
            self._config.options.settings_toggle_hotkey
        )
        if not settings_hotkey:
            raise ValueError("Settings overlay hotkey format is invalid.")
        profile_hotkeys = {
            self._hotkeys.normalize_hotkey(profile.select_hotkey)
            for profile in self._config.profiles
            if profile.select_hotkey.strip()
        }
        if settings_hotkey in profile_hotkeys:
            raise ValueError(
                "Settings overlay hotkey conflicts with a profile hotkey. Pick a different key."
            )
        self._config.options.settings_toggle_hotkey = self._hotkeys.apply_settings_toggle_hotkey(
            settings_hotkey
        )
        self._overlay.set_lock(
            self._config.options.lock_overlay and not self._config.options.force_overlay_visible
        )
        self._sync_overlay_visibility()

    def _enforce_parallel_profile_policy(self) -> None:
        enforce_parallel_profile_policy(
            self._config.profiles,
            allow_parallel=self._config.options.allow_parallel,
        )

    def _schedule_overlay_sync(self) -> None:
        self._sync_overlay_visibility()
        self._overlay_sync_job = self.after(150, self._schedule_overlay_sync)

    def _schedule_theme_sync(self) -> None:
        current = ctk.get_appearance_mode().lower()
        if current != self._table_ui.last_appearance_mode:
            self._apply_table_theme()
        self._theme_sync_job = self.after(500, self._schedule_theme_sync)

    def _sync_overlay_visibility(self) -> None:
        sync_started = time.perf_counter()
        if self._config.options.force_overlay_visible:
            self._set_overlay_state(visible=True, names=["FORCED OVERLAY"])
            return
        if self._overlay_is_dragging:
            # Keep overlay visible while dragging to avoid flicker caused by
            # transient foreground-title changes during mouse capture.
            self._set_overlay_state(visible=True, names=list(self._last_overlay_text))
            return
        foreground = get_foreground_context()
        matching_profiles = active_profiles_matching_title(
            self._config.profiles,
            foreground_title=foreground.title if foreground is not None else "",
        )
        allowed_app_focused = foreground is not None and is_allowed_application_focused(
            self._config.options, foreground.exe_name
        )
        should_show = (
            self._config.options.enable_overlay
            and bool(matching_profiles)
            and allowed_app_focused
        )
        self._set_overlay_state(visible=should_show, names=matching_profiles if should_show else [])
        elapsed_ms = (time.perf_counter() - sync_started) * 1000
        if elapsed_ms >= 5:
            logger.debug("overlay_sync_ms=%.2f visible=%s matches=%d", elapsed_ms, should_show, len(matching_profiles))

    def _set_overlay_state(self, visible: bool, names: list[str]) -> None:
        name_tuple = tuple(names)
        if name_tuple != self._last_overlay_text:
            self._overlay.set_text(list(name_tuple), bool(name_tuple))
            self._last_overlay_text = name_tuple
        if visible == self._last_overlay_visible:
            if visible:
                self._overlay.keep_topmost_without_focus()
            return
        self._last_overlay_visible = visible
        if visible:
            self._overlay.deiconify()
            self._overlay.attributes("-topmost", True)
            self._overlay.keep_topmost_without_focus()
            return
        self._overlay.withdraw()

    def _on_overlay_drag_state_changed(self, is_dragging: bool) -> None:
        self._overlay_is_dragging = is_dragging
        self._sync_overlay_visibility()

    def _parse_profile_from_form(self) -> SpamProfile | None:
        name = self.name_entry.get().strip()
        title = self.window_title_entry.get().strip()
        hotkey = self.hotkey_entry.get().strip()
        spam_key = self.spam_key_entry.get().strip()
        if not name:
            messagebox.showerror("Validation", "Profile name is required.")
            return None
        if not title:
            messagebox.showerror("Validation", "Window title pattern is required.")
            return None
        if not hotkey:
            messagebox.showerror("Validation", "Hotkey is required.")
            return None
        normalized_hotkey = self._hotkeys.normalize_hotkey(hotkey)
        if not normalized_hotkey:
            messagebox.showerror("Validation", "Hotkey format is invalid.")
            return None
        if not spam_key:
            messagebox.showerror("Validation", "Spam key is required.")
            return None
        try:
            canonical_spam_key, _ = normalize_spam_key_combo(spam_key)
        except ValueError as exc:
            messagebox.showerror("Validation", str(exc))
            return None
        try:
            interval = max(10, int(self.interval_entry.get().strip()))
        except ValueError:
            messagebox.showerror("Validation", "Interval must be a number.")
            return None
        return SpamProfile(
            name=name,
            window_title=title,
            use_regex=self.use_regex_var.get(),
            spam_key=canonical_spam_key,
            interval_ms=interval,
            select_hotkey=normalized_hotkey,
            is_active=False,
        )

    def _add_profile(self) -> None:
        profile = self._parse_profile_from_form()
        if profile is None:
            return
        validation_error = validate_profile_uniqueness(
            profiles=self._config.profiles,
            candidate=profile,
            normalize_hotkey=self._hotkeys.normalize_hotkey,
        )
        if validation_error:
            messagebox.showerror("Validation", validation_error)
            return
        self._config.profiles.append(profile)
        self._refresh_profile_list()
        self._apply_options()
        self._apply_active_profiles_state()
        self._save_config_debounced()

    def _update_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showerror("Update", "Select a profile first.")
            return
        profile = self._parse_profile_from_form()
        if profile is None:
            return
        existing_name = self._config.profiles[index].name
        profile.is_active = self._config.profiles[index].is_active
        validation_error = validate_profile_uniqueness(
            profiles=self._config.profiles,
            candidate=profile,
            normalize_hotkey=self._hotkeys.normalize_hotkey,
            ignore_index=index,
        )
        if validation_error:
            messagebox.showerror("Validation", validation_error)
            return
        self._config.profiles[index] = profile
        if self._selected_profile_name == existing_name:
            self._selected_profile_name = profile.name
        self._refresh_profile_list(selected_name=profile.name)
        self._apply_options()
        self._apply_active_profiles_state()
        self._save_config_debounced()

    def _delete_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        name = self._config.profiles[index].name
        del self._config.profiles[index]
        if self._selected_profile_name == name:
            self._selected_profile_name = None
            self._clear_form()
        self._refresh_profile_list()
        self._apply_options()
        self._apply_active_profiles_state()
        self._save_config_debounced()

    def _on_table_selected(self, _event=None) -> None:
        index = self._selected_index()
        if index is None:
            self._set_selection_buttons_enabled(False)
            return
        self._set_selection_buttons_enabled(True)
        profile = self._config.profiles[index]
        self._selected_profile_name = profile.name
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, profile.name)
        self.window_title_entry.delete(0, tk.END)
        self.window_title_entry.insert(0, profile.window_title)
        self.use_regex_var.set(profile.use_regex)
        self.spam_key_entry.delete(0, tk.END)
        self.spam_key_entry.insert(0, profile.spam_key)
        self.interval_entry.delete(0, tk.END)
        self.interval_entry.insert(0, str(profile.interval_ms))
        self.hotkey_entry.delete(0, tk.END)
        self.hotkey_entry.insert(0, profile.select_hotkey)

    def _on_table_click(self, event) -> None:
        row_id = self.profile_table.identify_row(event.y)
        col_id = self.profile_table.identify_column(event.x)
        if row_id and col_id == "#0":
            index = self.profile_table.index(row_id)
            self._toggle_profile_active(index)
            return "break"
        if row_id:
            return
        self.profile_table.selection_remove(self.profile_table.selection())
        self.profile_table.focus("")
        self._selected_profile_name = None
        self._clear_form()
        self._set_selection_buttons_enabled(False)
        self._save_config_debounced()

    def _on_table_press(self, event) -> None:
        row_id = self.profile_table.identify_row(event.y)
        col_id = self.profile_table.identify_column(event.x)
        if not row_id or col_id == "#0":
            self._dragged_row_id = None
            self._row_drag_in_progress = False
            self.profile_table.configure(cursor="")
            self._drag_status_text = None
            return
        self._dragged_row_id = row_id
        self._row_drag_in_progress = False

    def _on_table_drag(self, event) -> str | None:
        if self._dragged_row_id is None:
            return None
        target_row_id = self.profile_table.identify_row(event.y)
        if not target_row_id or target_row_id == self._dragged_row_id:
            return None
        from_index = self.profile_table.index(self._dragged_row_id)
        to_index = self.profile_table.index(target_row_id)
        if from_index == to_index:
            return None
        self.profile_table.move(self._dragged_row_id, "", to_index)
        moved = self._config.profiles.pop(from_index)
        self._config.profiles.insert(to_index, moved)
        self.profile_table.selection_set(self._dragged_row_id)
        self.profile_table.focus(self._dragged_row_id)
        self._selected_profile_name = moved.name
        self._drag_status_text = f"Dragging '{moved.name}' to row {to_index + 1}"
        self.status_var.set(self._drag_status_text)
        self._row_drag_in_progress = True
        self.profile_table.configure(cursor=self._table_drag_cursor)
        return "break"

    def _on_table_release(self, _event) -> str | None:
        self.profile_table.configure(cursor="")
        if self._dragged_row_id is None:
            return None
        was_dragging = self._row_drag_in_progress
        self._dragged_row_id = None
        self._row_drag_in_progress = False
        self._drag_status_text = None
        if was_dragging:
            self._on_table_selected()
            self._apply_active_profiles_state()
            self._update_status_text(self._engine.status)
            self._save_config_debounced()
            return "break"
        return None

    def _on_profile_selected_by_hotkey(self, profile_name: str) -> None:
        self.after(0, lambda: self._toggle_profile_by_hotkey(profile_name))

    def _toggle_profile_by_hotkey(self, profile_name: str) -> None:
        if self._config.options.restrict_profile_hotkeys_to_allowed_apps:
            foreground = get_foreground_context()
            if foreground is None:
                return
            if not is_allowed_application_focused(self._config.options, foreground.exe_name):
                return
        for index, profile in enumerate(self._config.profiles):
            if profile.name == profile_name:
                self._toggle_profile_active(index, persist=False)
                return

    def _spam_allowed_executables(self) -> list[str]:
        if self._config.options.allow_background:
            return []
        foreground = get_foreground_context()
        if foreground is None:
            return ["__neonmacro_no_foreground__"]
        exe_name = foreground.exe_name.strip().lower()
        if not exe_name:
            return ["__neonmacro_no_foreground__"]
        return [exe_name]

    def _apply_active_profiles_state(self) -> None:
        active_profiles = [profile for profile in self._config.profiles if profile.is_active]
        self._engine.set_active_profiles(active_profiles)
        self._engine.set_enabled(bool(active_profiles))
        self._hotkeys.apply_profile_hotkeys(self._config.profiles)
        self._update_status_text(self._engine.status)

    def _on_engine_tick(self, status: EngineStatus) -> None:
        self.after(0, lambda: self._update_status_text(status))

    def _on_engine_error(self, message: str) -> None:
        self.after(0, lambda: self._show_engine_error(message))

    def _show_engine_error(self, message: str) -> None:
        now = self.tk.call("clock", "seconds")
        if message == self._last_engine_error_message and (float(now) - self._last_engine_error_at) < 3:
            return
        self._last_engine_error_message = message
        self._last_engine_error_at = float(now)
        messagebox.showerror("Spam key validation", message)

    def _update_status_text(self, status: EngineStatus) -> None:
        status_view = build_status_view(
            enabled=status.enabled,
            active_profile_names=status.active_profile_names or [],
        )
        self._overlay_has_active_spam = status_view.overlay_has_active_spam
        if self._drag_status_text:
            self.status_var.set(self._drag_status_text)
        else:
            self.status_var.set(status_view.text)
        self._sync_overlay_visibility()

    def _refresh_profile_list(self, selected_name: str | None = None) -> None:
        for item_id in self.profile_table.get_children():
            self.profile_table.delete(item_id)
        for profile in self._config.profiles:
            self.profile_table.insert(
                "",
                tk.END,
                image=self._table_ui.checkbox_images[profile.is_active],
                values=(
                    profile.name,
                    profile.window_title,
                    profile.interval_ms,
                    profile.select_hotkey,
                    profile.spam_key,
                ),
            )
        self.after_idle(self._update_table_scrollbar_visibility)
        target = selected_name or self._selected_profile_name
        if not target:
            return
        for index, profile in enumerate(self._config.profiles):
            if profile.name == target:
                self._select_table_row(index)
                self._on_table_selected()
                break

    def _update_table_scrollbar_visibility(self) -> None:
        self._table_ui.update_scrollbar_visibility()

    def _update_table_row(self, index: int) -> None:
        children = self.profile_table.get_children()
        if index < 0 or index >= len(children):
            return
        profile = self._config.profiles[index]
        item_id = children[index]
        self.profile_table.item(
            item_id,
            image=self._table_ui.checkbox_images[profile.is_active],
            values=(
                profile.name,
                profile.window_title,
                profile.interval_ms,
                profile.select_hotkey,
                profile.spam_key,
            ),
        )

    def _selected_index(self) -> int | None:
        selected = self.profile_table.selection()
        if not selected:
            return None
        item_id = selected[0]
        try:
            return self.profile_table.index(item_id)
        except tk.TclError:
            return None

    def _select_table_row(self, index: int) -> None:
        children = self.profile_table.get_children()
        if index < 0 or index >= len(children):
            return
        item_id = children[index]
        self.profile_table.selection_set(item_id)
        self.profile_table.focus(item_id)
        self.profile_table.see(item_id)

    def _save_config(self) -> None:
        if self._config_save_job is not None:
            self.after_cancel(self._config_save_job)
            self._config_save_job = None
        if self.state() != "zoomed":
            self._config.window_width = self.winfo_width()
            self._config.window_height = self.winfo_height()
            self._config.window_x = self.winfo_x()
            self._config.window_y = self.winfo_y()
        x, y = self._overlay.get_position()
        self._config.overlay.x = x
        self._config.overlay.y = y
        self._config.selected_profile_name = self._selected_profile_name
        self._store.save(self._config)

    def _save_config_debounced(self, delay_ms: int = 150) -> None:
        if self._config_save_job is not None:
            self.after_cancel(self._config_save_job)
        self._config_save_job = self.after(delay_ms, self._save_config)

    def _on_overlay_position_changed(self, center_x: int, center_y: int) -> None:
        self._pending_overlay_center = (center_x, center_y)
        if self._options_dialog is not None and self._options_dialog.winfo_exists():
            self._options_dialog.overlay_x_var.set(str(center_x))
            self._options_dialog.overlay_y_var.set(str(center_y))

    def _toggle_profile_active(self, index: int, persist: bool = True) -> None:
        if index < 0 or index >= len(self._config.profiles):
            return
        profile = self._config.profiles[index]
        next_active = not profile.is_active
        if not self._config.options.allow_parallel and next_active:
            for i, item in enumerate(self._config.profiles):
                item.is_active = i == index
                self._update_table_row(i)
        else:
            profile.is_active = next_active
            self._update_table_row(index)
        self._apply_active_profiles_state()
        if persist:
            self._save_config_debounced()

    def _on_auto_stop_hotkey(self) -> None:
        self.after(0, self._stop_all_active_profiles_if_allowed_app)

    def _on_settings_toggle_hotkey(self) -> None:
        self.after(0, self._toggle_settings_overlay_on_allowed_app)

    def _stop_all_active_profiles_if_allowed_app(self) -> None:
        foreground = get_foreground_context()
        if foreground is None:
            return
        if not is_allowed_application_focused(self._config.options, foreground.exe_name):
            return
        self._stop_all_active_profiles()

    def _stop_all_active_profiles(self) -> None:
        changed = False
        for index, profile in enumerate(self._config.profiles):
            if profile.is_active:
                profile.is_active = False
                self._update_table_row(index)
                changed = True
        if not changed:
            return
        self._apply_active_profiles_state()
        self._save_config_debounced()

    def _clear_form(self) -> None:
        self.name_entry.delete(0, tk.END)
        self.window_title_entry.delete(0, tk.END)
        self.use_regex_var.set(False)
        self.spam_key_entry.delete(0, tk.END)
        self.interval_entry.delete(0, tk.END)
        self.hotkey_entry.delete(0, tk.END)

    def _set_selection_buttons_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.update_button.configure(state=state)
        self.delete_button.configure(state=state)

    def _on_exit(self) -> None:
        if self._overlay_sync_job is not None:
            self.after_cancel(self._overlay_sync_job)
            self._overlay_sync_job = None
        if self._theme_sync_job is not None:
            self.after_cancel(self._theme_sync_job)
            self._theme_sync_job = None
        if self._config_save_job is not None:
            self.after_cancel(self._config_save_job)
            self._config_save_job = None
        if self._pending_overlay_center is not None:
            center_x, center_y = self._pending_overlay_center
            self._config.overlay.x = center_x
            self._config.overlay.y = center_y
            self._pending_overlay_center = None
        self._save_config()
        self._engine.stop()
        self._hotkeys.shutdown()
        self._overlay.destroy()
        self.destroy()

