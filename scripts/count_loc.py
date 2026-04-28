#!/usr/bin/env python3
"""Count application source lines excluding tests and documentation."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

EXCLUDE_DIRS = {
    ".git",
    ".pytest_cache",
    ".vscode",
    "__pycache__",
    "docs",
    "import_logs",
    "legacy",
    "release",
    "scripts",
}

EXCLUDE_FILE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^test_.*\.py$"),
    re.compile(r".*_test\.py$"),
    re.compile(r"^conftest\.py$"),
    re.compile(r"^test\.py$"),
    re.compile(r"^test2\.py$"),
]


def is_excluded(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDE_DIRS:
        return True
    name = path.name
    return any(pat.match(name) for pat in EXCLUDE_FILE_PATTERNS)


def count_file_lines(path: Path) -> int:
    loc = 0
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            loc += 1
    return loc


def iter_source_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if is_excluded(path.relative_to(root)):
            continue
        yield path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Count non-empty, non-comment Python LOC excluding tests and documentation.",
    )
    parser.add_argument(
        "--per-file",
        action="store_true",
        help="Show per-file counts in addition to the total.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    totals: list[tuple[Path, int]] = []
    total_loc = 0

    for path in iter_source_files(repo_root):
        loc = count_file_lines(path)
        totals.append((path.relative_to(repo_root), loc))
        total_loc += loc

    print(f"Total non-blank, non-comment Python LOC: {total_loc}")
    if args.per_file:
        for rel, loc in sorted(totals, key=lambda pair: str(pair[0])):
            print(f"{loc:5d}  {rel}")


if __name__ == "__main__":
    main()
