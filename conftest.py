"""Global pytest configuration and Tk runtime preflight behavior."""

from __future__ import annotations

import inspect
import json
import logging
from pathlib import Path

import pytest

from qtr_pairing_process.tk_runtime_guard import run_tk_preflight


LOGGER = logging.getLogger("pytest.tk_preflight")
_TK_OK = None
_TK_ERROR = None
_TK_DETAILS = None


def _run_once_tk_preflight():
    global _TK_OK, _TK_ERROR, _TK_DETAILS
    if _TK_OK is not None:
        return _TK_OK, _TK_ERROR, _TK_DETAILS
    _TK_OK, _TK_ERROR, _TK_DETAILS = run_tk_preflight()
    try:
        LOGGER.warning(
            "Tk test preflight status=%s error=%s details=%s",
            _TK_OK,
            _TK_ERROR,
            json.dumps(_TK_DETAILS, ensure_ascii=False, default=str),
        )
    except Exception:
        pass
    return _TK_OK, _TK_ERROR, _TK_DETAILS


def _is_tk_dependent(item) -> bool:
    """Best-effort Tk dependency detection.

    Prefer @pytest.mark.requires_tk for explicitness in tests that may not contain
    direct tkinter calls in function source (for example helper-driven setups).
    """
    marker = item.get_closest_marker("requires_tk")
    if marker is not None:
        return True

    fn = getattr(item, "function", None)
    if fn is None:
        return False

    try:
        source = inspect.getsource(fn)
    except (OSError, TypeError):
        return False

    probes = (
        "tk.Tk(",
        "ttk.Treeview(",
        "tk.Toplevel(",
        "tk.Frame(",
        "tk.Label(",
        "tk.IntVar(",
        "tk.StringVar(",
    )
    return any(probe in source for probe in probes)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_tk: marks test as requiring Tk runtime",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    ok, err, details = _run_once_tk_preflight()
    if ok:
        return

    reason = "Tk runtime unavailable; skipping Tk-dependent tests"
    root = Path(config.rootpath)
    for item in items:
        if not _is_tk_dependent(item):
            continue

        try:
            log_path = root / "qtr_pairing_process.log"
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(
                    "\n[pytest.tk_preflight] skipping test="
                    + item.nodeid
                    + " error="
                    + str(err)
                    + " details="
                    + json.dumps(details, ensure_ascii=False, default=str)
                    + "\n"
                )
        except Exception:
            pass

        item.add_marker(pytest.mark.skip(reason=reason))
