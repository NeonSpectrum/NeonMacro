from __future__ import annotations

import sys


def is_packaged_runtime() -> bool:
    # PyInstaller/py2exe-style flag.
    if getattr(sys, "frozen", False):
        return True
    # Nuitka provides __compiled__ in compiled modules.
    if "__compiled__" in globals():
        return True
    return False
