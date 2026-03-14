"""Performance timing helper."""

import time
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from glob import glob
from typing import Optional, Dict, Any


class PerfTimer:
    def __init__(
        self,
        enabled: bool = False,
        log_path: Optional[Path] = None,
        log_dir: Optional[Path] = None,
        buffered: bool = False,
        buffer_size: int = 25,
        max_daily_files: int = 5,
    ):
        self.enabled = enabled
        self.buffered = bool(buffered)
        self.buffer_size = max(1, int(buffer_size))
        self.max_daily_files = max(1, int(max_daily_files))
        self._lock = threading.Lock()
        self._buffer = []

        if log_path is not None:
            self.log_path = Path(log_path)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_path.touch(exist_ok=True)
        else:
            base_dir = Path(log_dir) if log_dir is not None else Path.cwd() / "perf_logs"
            self.log_path = self._create_session_log_file(base_dir)

    def set_enabled(self, enabled: bool):
        if not enabled:
            self.flush()
        self.enabled = enabled

    def _create_session_log_file(self, base_dir: Path) -> Path:
        base_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        date_key = now.strftime("%Y%m%d")
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
        log_path = base_dir / f"perf_{timestamp}.log"
        log_path.touch(exist_ok=True)
        self._enforce_daily_file_cap(base_dir, date_key)
        return log_path

    def _enforce_daily_file_cap(self, base_dir: Path, date_key: str):
        pattern = str(base_dir / f"perf_{date_key}_*.log")
        matches = sorted(glob(pattern))
        if len(matches) <= self.max_daily_files:
            return
        overflow = len(matches) - self.max_daily_files
        for old_path in matches[:overflow]:
            try:
                Path(old_path).unlink(missing_ok=True)
            except Exception:
                pass

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

        if self.buffered:
            flush_now = False
            with self._lock:
                self._buffer.append(line)
                flush_now = len(self._buffer) >= self.buffer_size
            if flush_now:
                self.flush()
            return

        self._flush_lines([line])

    def _flush_lines(self, lines):
        if not lines:
            return

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")
        except Exception:
            pass

    def flush(self):
        if not self.buffered:
            return
        with self._lock:
            lines = list(self._buffer)
            self._buffer.clear()
        self._flush_lines(lines)

    def close(self):
        self.flush()
