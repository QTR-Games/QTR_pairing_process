"""Tk runtime preflight helpers for startup resilience and diagnostics."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple


def _possible_tcl_roots() -> list[str]:
    roots = []
    for base in {sys.base_prefix, sys.prefix}:
        if not base:
            continue
        roots.append(str(Path(base) / "tcl"))
        roots.append(str(Path(base) / "Library" / "lib"))
    return roots


def collect_tk_environment() -> Dict[str, object]:
    """Collect environment details useful for diagnosing Tk startup issues."""
    candidates = _possible_tcl_roots()
    existing = [path for path in candidates if Path(path).exists()]
    return {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "sys_prefix": sys.prefix,
        "sys_base_prefix": sys.base_prefix,
        "TCL_LIBRARY": os.environ.get("TCL_LIBRARY"),
        "TK_LIBRARY": os.environ.get("TK_LIBRARY"),
        "possible_tcl_roots": candidates,
        "existing_tcl_roots": existing,
    }


def run_tk_preflight() -> Tuple[bool, Optional[str], Dict[str, object]]:
    """Return (ok, error_message, diagnostic_details) for Tk runtime availability."""
    details = collect_tk_environment()
    try:
        import tkinter as tk

        details["tk_version"] = getattr(tk, "TkVersion", None)
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        details["tk_root_init"] = "ok"
        return True, None, details
    except Exception as exc:
        details["tk_root_init"] = "failed"
        details["exception_type"] = type(exc).__name__
        details["exception_message"] = str(exc)
        return False, str(exc), details
