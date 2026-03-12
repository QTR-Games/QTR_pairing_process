"""Performance timing helper."""

import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class PerfTimer:
    def __init__(self, enabled: bool = False, log_path: Optional[Path] = None):
        self.enabled = enabled
        self.log_path = log_path

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    @contextmanager
    def span(self, label: str, **meta: Any):
        if not self.enabled:
            yield
            return

        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self._write_log(label, elapsed_ms, meta)

    def _write_log(self, label: str, elapsed_ms: float, meta: Dict[str, Any]):
        if not self.log_path:
            return

        timestamp = datetime.now().isoformat(timespec="seconds")
        meta_text = " ".join([f"{key}={value}" for key, value in meta.items()])
        line = f"{timestamp} | {label} | {elapsed_ms:.2f}ms"
        if meta_text:
            line = f"{line} | {meta_text}"

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:
            pass
