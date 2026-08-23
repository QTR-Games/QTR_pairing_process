# Architecture

## Runtime shape

QTR is a Python/Tkinter desktop application. `main.py` is the production
launcher: it reads application constants, runs the Tk runtime preflight, and
creates `qtr_pairing_process.ui_manager_v2.UiManager`. `entrypoint.py`
provides the same v2 UI path with optional performance logging flags for
development use.

`UiManager` is the composition point for the current UI. It selects a
database, loads preferences, builds the Tk widgets, coordinates the rating
grid, and invokes the tree and import/export components. The v1 implementation
is retained as `ui_manager_v1_original.py`; new UI work belongs in the v2
path unless a task explicitly targets the legacy code.

```text
main.py / entrypoint.py
        |
        +-- Tk preflight --> UiManager (v2)
                              |
        +---------------------+----------------------+
        |                     |                      |
  grid and dialogs      TreeGenerator          Excel import/export
        |                     |                      |
        +---------------------+----------------------+
                              |
                         DbManager / SQLite
```

## Data and persistence

`DbManager` owns SQLite initialization and access. A default instance uses
`default.db` in the user's home directory; it creates and seeds the teams,
players, scenarios, and ratings tables when needed. It also maintains
application settings and uses thread-local secure database interfaces for
parameterized operations.

The UI's database preferences and strategic settings are read from its
configuration path, including `KLIK_KLAK_KONFIG.json`. Rating grids and
pairing data flow through the UI, database helpers, and `TreeGenerator`.
The Excel modules use `openpyxl` for workbook import and export; CSV handling
uses the Python standard library.

SQL bootstrap files live under `qtr_pairing_process/db_management/sql`. They
are application data and are included by the release build.

## Dependency boundary

The application has one runtime third-party dependency: `openpyxl`. Tkinter
and SQLite are Python standard-library components supplied by a suitable
Python installation. Python must include Tcl/Tk support to run the GUI.

The project continues to package through `setup.py`. Its version is read from
the canonical `qtr_pairing_process/VERSION` file. `pyproject.toml` is
tool-only configuration for pytest, Ruff, and mypy; it intentionally has no
`[build-system]` table, so it does not replace or change the `setup.py`
packaging behavior.

## Tk and headless environments

Before creating the UI, `tk_runtime_guard.run_tk_preflight()` imports Tkinter,
creates a withdrawn root window, and destroys it. A failed preflight prevents
startup and records diagnostics in `qtr_pairing_process.log`.

The same preflight protects tests. A display-less Linux environment can import
Tkinter but still fail when creating a root window, so Tk-dependent tests are
skipped there unless a virtual display is provided. See [Testing](testing.md)
for the CI and local behavior.
