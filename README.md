# NeonFtool

A Windows desktop app (CustomTkinter) for creating configurable key-spam profiles that target windows by title and send keys via the Win32 `PostMessage` API.

## Features

- Spam profiles with:
  - Name
  - Window title pattern (plain text or regex)
  - Spam key (`1-9`, `F1-F9`)
  - Interval (ms)
  - Profile hotkey (to select active profile)
  - Active/inactive status
- Global hotkey to toggle spam execution
- Options:
  - Global toggle hotkey
  - Overlay enabled
  - Overlay lock
  - Allowed application list (defaults to `Neuz.exe`)
- Always-on-top draggable overlay showing selected profile + status
- Auto-save JSON config for profiles, options, and overlay position

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .
neonftool
```

## Build EXE with Nuitka

```powershell
pip install -e . nuitka ordered-set zstandard
python -m nuitka --onefile --standalone --assume-yes-for-downloads --enable-plugin=tk-inter --windows-console-mode=disable --output-dir=build\dist src\neonftool\app.py
```

## Notes

- Requires Windows.
- Global hotkeys rely on the `keyboard` package and may require admin permissions on some systems.
