# QTR Pairing Process v2.1.4 — Release Notes

**Release Date:** 2026-04-28

## Bug Fix

### Critical: Application crashed on launch in compiled exe (ModuleNotFoundError)

The v2.1.3 executable failed immediately on launch with:

```
ModuleNotFoundError: No module named 'qtr_pairing_process.excel_management.simple_excel_importer'
```

**Root cause:** PyInstaller only collected modules it could trace through static imports. The new `excel_management` sub-package (added in v2.1.3 via the XLSX import/export feature) was not automatically discovered.

**Fix:** Added `--collect-all qtr_pairing_process` to the PyInstaller build command. This bundles the entire `qtr_pairing_process` package and all sub-packages (including `excel_management`, `db_management`, and any future additions) regardless of how they are imported at runtime.

The SQL schema `--add-data` flag is retained for clarity but is now redundant — `--collect-all` handles it too.

## All v2.1.3 Features Included

- XLSX import/export support
- Import Templates popup (Ctrl+Shift+T)
- Import logs folder access (Ctrl+Shift+L)
- Full keyboard shortcut suite (22 bindings)
- Tab/Shift-Tab navigation in the rating grid
- Thread-safe SecureDBInterface
- User guide bundled in every release
- Carries forward v2.1.2 fix: SQL schema files bundled in exe
