from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _resolve_icon_path(project_root: Path) -> Path | None:
    project_icon = project_root / "assets" / "icons" / "logo.ico"
    if project_icon.exists():
        return project_icon

    try:
        import customtkinter as ctk
    except Exception:
        return None

    fallback_icon = (
        Path(ctk.__file__).resolve().parent / "assets" / "icons" / "CustomTkinter_icon_Windows.ico"
    )
    if fallback_icon.exists():
        return fallback_icon
    return None


def main() -> int:
    if os.name != "nt":
        print("This build command is intended for Windows only.")
        return 1

    project_root = Path(__file__).resolve().parents[2]
    build_dir = project_root / "build"
    dist_dir = build_dir / "dist"
    launcher_path = build_dir / "nuitka_entry.py"
    output_path = dist_dir / "NeonMacro.exe"
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    dist_dir.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(dist_dir / "nuitka_entry.build", ignore_errors=True)
    shutil.rmtree(dist_dir / "nuitka_entry.dist", ignore_errors=True)
    if output_path.exists():
        try:
            output_path.unlink()
        except PermissionError:
            print(
                f"Cannot overwrite '{output_path}'. "
                "Close NeonMacro.exe and any app holding the file (Explorer preview, editor tab, AV scan), then retry."
            )
            return 1

    launcher_path.write_text(
        "\n".join(
            [
                "import os",
                "os.environ['LOG_LEVEL'] = 'NONE'",
                "",
                "from neonmacro.app import main",
                "",
                "if __name__ == '__main__':",
                "    main()",
                "",
            ]
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=tk-inter",
        "--include-package=neonmacro",
        "--windows-console-mode=disable",
        "--output-filename=NeonMacro.exe",
        f"--output-dir={dist_dir}",
    ]

    icon_path = _resolve_icon_path(project_root)
    if icon_path is not None:
        cmd.append(f"--windows-icon-from-ico={icon_path}")
        cmd.append(f"--include-data-files={icon_path}=neonmacro/assets/icons/logo.ico")

    cmd.append(str(launcher_path))

    print("Running:", " ".join(str(arg) for arg in cmd))
    subprocess.run(cmd, cwd=project_root, check=True)

    if not output_path.exists():
        print(f"Build finished but output not found: {output_path}")
        return 1
    print(f"Build complete: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
