# NeonMacro

NeonMacro is a Windows desktop app (built with CustomTkinter) for creating configurable key-spam profiles. It targets windows by title and sends keys through the Win32 `PostMessage` API.

## What it does

- Create multiple spam profiles with:
  - Profile name
  - Window title matcher (plain text or regex)
  - Spam key (`1-9`, `F1-F9`)
  - Interval in milliseconds
  - Profile hotkey (select active profile quickly)
  - Active/inactive status
- Use a global hotkey to start/stop spamming.
- Show an always-on-top draggable overlay for quick status.
- Configure:
  - Global toggle hotkey
  - Overlay enabled/locked
  - Open on startup (Windows user startup via Run key)
  - Minimize to tray on startup
  - Allowed application list (default: `Neuz.exe`)
  - Optional restriction so profile hotkeys only work inside allowed applications
- Auto-save profiles, options, and overlay position to JSON.

## Requirements

- Windows 10/11
- Python 3.10+ recommended

## Quick start (Poetry)

```powershell
poetry install
poetry run dev
```

If Poetry is not installed yet:

```powershell
pipx install poetry
```

## Build a single-file EXE (Nuitka + Poetry)

```powershell
poetry add --group dev nuitka ordered-set zstandard
poetry run build
```

Build output is written to `build\dist\NeonMacro.exe`.

## Basic usage

1. Launch `neonmacro`.
2. Create at least one profile and set:
   - Target window title pattern
   - Key and interval
   - Optional per-profile hotkey
3. Select the active profile.
4. Use the global toggle hotkey to start/stop sending keys.
5. Use the overlay to monitor current profile/status.

## Startup options

- Open **Options** and enable **Open on startup** to register NeonMacro in the current user's Windows startup (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).
- Enable **Minimize to tray on startup** to append `--silent` to the startup command.
- `--silent` launch starts NeonMacro minimized to tray; normal/manual launches stay visible.

## Troubleshooting

- **Hotkeys do not trigger**
  - Run the app as Administrator.
  - Check for conflicts with other tools that capture global hotkeys.
- **No keys sent to target app**
  - Confirm the window title pattern matches the target window.
  - Verify the process is included in the allowed app list.
- **Unexpected behavior with regex matching**
  - Start with plain-text matching, then switch to regex once confirmed.

## Notes

- Windows only.
- Global hotkeys rely on the `keyboard` package and may require elevated permissions on some systems.
