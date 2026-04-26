from __future__ import annotations

import ctypes
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path

import customtkinter as ctk


@dataclass
class IconApplyResult:
    ico_path: str | None
    win32_icon_handles: list[int]


def candidate_ico_paths(preferred_ico_path: str | None = None) -> list[Path]:
    candidates: list[Path] = []
    if preferred_ico_path:
        candidates.append(Path(preferred_ico_path))
    candidates.extend(
        [
            Path(__file__).resolve().parents[1] / "assets" / "icons" / "logo.ico",
            Path(__file__).resolve().parents[3] / "assets" / "icons" / "logo.ico",
            Path(ctk.__file__).resolve().parent / "assets" / "icons" / "CustomTkinter_icon_Windows.ico",
        ]
    )
    return candidates


def apply_window_icon(
    window: tk.Tk | tk.Toplevel,
    *,
    preferred_ico_path: str | None = None,
    apply_default_icon: bool = False,
    apply_win32_caption_icon: bool = False,
    win32_icon_handles: list[int] | None = None,
) -> IconApplyResult:
    for icon_path in candidate_ico_paths(preferred_ico_path):
        if not icon_path.exists():
            continue
        try:
            window.iconbitmap(str(icon_path))
            if apply_default_icon:
                try:
                    window.tk.call("wm", "iconbitmap", window._w, "-default", str(icon_path))
                except tk.TclError:
                    pass
            handles = _apply_win32_caption_icons(
                window, str(icon_path), existing_handles=win32_icon_handles
            ) if apply_win32_caption_icon else (win32_icon_handles or [])
            return IconApplyResult(ico_path=str(icon_path), win32_icon_handles=handles)
        except tk.TclError:
            continue

    return IconApplyResult(
        ico_path=None,
        win32_icon_handles=win32_icon_handles or [],
    )


def destroy_win32_icon_handles(handles: list[int]) -> None:
    if not handles:
        return
    try:
        user32 = ctypes.windll.user32
        for handle in handles:
            if handle:
                user32.DestroyIcon(handle)
    except Exception:
        pass
    handles.clear()


def _apply_win32_caption_icons(
    window: tk.Toplevel,
    ico_path: str,
    *,
    existing_handles: list[int] | None = None,
) -> list[int]:
    try:
        user32 = ctypes.windll.user32
        image_icon = 1
        load_from_file = 0x0010
        default_size = 0x0040
        wm_seticon = 0x0080
        icon_small = 0
        icon_big = 1
        hwnd = int(window.winfo_id())
        if existing_handles and len(existing_handles) == 2:
            hicon_small, hicon_big = existing_handles
        else:
            hicon_small = user32.LoadImageW(
                None, ico_path, image_icon, 16, 16, load_from_file | default_size
            )
            hicon_big = user32.LoadImageW(
                None, ico_path, image_icon, 32, 32, load_from_file | default_size
            )
            existing_handles = [hicon_small, hicon_big]
        if hicon_small:
            user32.SendMessageW(hwnd, wm_seticon, icon_small, hicon_small)
        if hicon_big:
            user32.SendMessageW(hwnd, wm_seticon, icon_big, hicon_big)
        return existing_handles
    except Exception:
        return existing_handles or []
