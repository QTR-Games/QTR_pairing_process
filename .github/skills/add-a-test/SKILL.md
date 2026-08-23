---
name: add-a-test
description: Use when adding or fixing a test in QTR, especially a Tkinter UI test.
---

# Add a QTR test

## 1. Decide whether Tk is required

Use ordinary unit tests when the behavior can be exercised without a GUI. For a
test that directly creates Tk widgets, or depends on helpers that do, add
`@pytest.mark.requires_tk` so the collection preflight can skip it cleanly when
Tk is unavailable.

## 2. Use the root test naming convention

Add focused tests at the repository root with a `test_*.py` filename and a
descriptive `test_*` function. Follow neighboring tests for fixtures and
imports; do not place new tests in `legacy/` unless the behavior is explicitly
legacy-only.

## 3. Run tests with the right display setup

Run a focused test with `python -m pytest test_name.py -q`. Run the full suite
on Windows with an isolated temporary base, such as
`python -m pytest -q --basetemp="$env:TEMP\qtr-pytest"`. Linux CI runs GUI tests
under `xvfb-run -a`; do not require a real desktop display in a test.

## 4. Check the pull request scope

Keep assertions deterministic, cover the behavior being changed, and retain the
Tk preflight behavior in `conftest.py`. Do not change sample files, release
artifacts, PDFs, or unrelated database and Excel behavior while adding a test.

## 5. Respect the CI matrix

The `tests` workflow runs Linux on Python 3.11 and 3.12 under Xvfb and Windows
on Python 3.12 with native Tk. A test must work across that matrix or carry a
clear, narrowly scoped platform reason.
