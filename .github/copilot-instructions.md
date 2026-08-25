# QTR Pairing Process agent guide

## Project overview

QTR Pairing Process is a Windows-focused Python desktop application for planning
5v5 tournament pairings. The user interface is Tkinter, persistent data uses
SQLite, and Excel imports and exports use `openpyxl`. Prefer a python.org Python
installation on Windows with Tcl/Tk included; Microsoft Store Python commonly
causes difficult-to-diagnose Tk runtime failures.

## Architecture map

- `main.py` is the primary launcher. `entrypoint.py` provides the packaged
  application entry point.
- `qtr_pairing_process/ui_manager_v2.py` is the preferred UI implementation
  for new UI work. Read and preserve integration points in `ui_manager.py`,
  `dynamic_ui_manager.py`, and related UI modules before changing behavior.
- `qtr_pairing_process/db_management/db_manager.py` and adjacent database
  modules manage SQLite state. Preserve the existing SQLite schema and
  parameterized-query conventions.
- `qtr_pairing_process/excel_management/` contains Excel import/export code.
  Use `openpyxl`; do not introduce a second spreadsheet library without an
  explicit project decision.
- `qtr_pairing_process/legacy/` is compatibility code. Avoid expanding it
  unless a regression requires a targeted legacy fix.

## Running the application

```powershell
python -m pip install -r requirements.txt
python main.py
```

Keep `setup.py` working. It remains part of the supported build and packaging
path even when the application is normally launched with `main.py`.

## Tests and Tk behavior

Run focused tests before the full suite when practical:

```powershell
python -m pytest test_some_feature.py -q
python -m pytest -q --basetemp="$env:TEMP\qtr-pytest"
```

`conftest.py` runs a Tk preflight during collection. Tests marked
`@pytest.mark.requires_tk`, or detected as directly using Tk, skip when the
local Tk runtime is unavailable. The preflight logs diagnostics and skip events
to `qtr_pairing_process.log`; do not replace this behavior with broad exception
handling or a fake GUI environment.

Linux CI uses `xvfb-run -a python -m pytest -q --basetemp=...` so Tk tests run
under a virtual display. Windows CI runs natively, using an isolated
`--basetemp` to avoid shared temporary-directory cleanup noise. Add
`@pytest.mark.requires_tk` to tests whose Tk dependency is indirect or not
recognizable from the test function source.

Ruff and mypy are available as advisory developer tools. Use them to catch
issues in changed Python code, but preserve the project's existing CI gates and
do not turn advisory tooling into a new required gate without agreement.

## Guardrails

- Do not modify release artifacts, bundled sample data, generated files, or PDF
  documents unless the task explicitly requires it.
- Do not change the SQLite storage convention, dependencies, or `setup.py`
  build path incidentally.
- Keep Windows behavior first-class and retain the Tk runtime preflight.
- Make focused, backward-compatible changes; avoid unrelated cleanup.

## Pull requests

Keep each PR scoped to one outcome. Include focused tests for behavior changes,
run the affected tests plus the appropriate full suite, and explain any
platform-specific Tk or Windows behavior. Do not merge, rebase unrelated work,
or alter other pull requests unless explicitly asked.

### Branch per pull request

This repository squash-merges. A squash merge creates a brand-new commit on
`main` with no ancestry link back to the commits it replaced, so the source
branch still looks like it carries unmerged work. Keep committing to that same
branch and every later push diverges and has to be forced.

So: one branch per pull request. When a PR merges, delete the branch and cut a
fresh one from `main` for the next piece of work. Never keep building on a
branch that has already been squash-merged.

Nothing is lost by squashing. GitHub keeps every original commit message in the
body of the squashed commit, and `main` ends up reading as one entry per
outcome, which is what you want from a fallback point.
