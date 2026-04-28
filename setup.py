""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
from pathlib import Path

from setuptools import setup  # type: ignore


def _read_app_version() -> str:
    version_file = Path(__file__).resolve().parent / "qtr_pairing_process" / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip()
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(
            f"Invalid canonical version '{version}'. Expected major.service.maintenance format."
        )
    return version

setup(
    name="qtr_pairing_process",
    version=_read_app_version(),
    author="Russ Rave",
    packages=[
        "qtr_pairing_process"
    ],
)