"""Version automation helpers for QTR release workflows."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple


VERSION_FILE = Path(__file__).resolve().parents[1] / "qtr_pairing_process" / "VERSION"


def read_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def write_version(version: str) -> None:
    validate_version(version)
    VERSION_FILE.write_text(f"{version}\n", encoding="utf-8")


def parse_version(version: str) -> Tuple[int, int, int]:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(
            f"Invalid version '{version}'. Expected three numeric segments (major.service.maintenance)."
        )
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def validate_version(version: str) -> None:
    parse_version(version)


def bump_version(current_version: str, change_type: str) -> str:
    major, service, maintenance = parse_version(current_version)
    normalized = change_type.strip().lower()

    if normalized == "major":
        return f"{major + 1}.0.0"
    if normalized == "service":
        return f"{major}.{service + 1}.0"
    if normalized == "maintenance":
        return f"{major}.{service}.{maintenance + 1}"

    raise ValueError("Unsupported change type. Use one of: major, service, maintenance.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage canonical app version")
    parser.add_argument("--show", action="store_true", help="Print current version")
    parser.add_argument(
        "--set",
        dest="set_version",
        help="Set explicit version value (must be major.service.maintenance)",
    )
    parser.add_argument(
        "--bump",
        choices=["major", "service", "maintenance"],
        help="Increment version based on release taxonomy",
    )
    args = parser.parse_args()

    if args.show:
        print(read_version())
        return 0

    if args.set_version:
        write_version(args.set_version)
        print(read_version())
        return 0

    if args.bump:
        next_version = bump_version(read_version(), args.bump)
        write_version(next_version)
        print(next_version)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
