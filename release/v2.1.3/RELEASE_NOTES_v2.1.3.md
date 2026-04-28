# Release Notes — QTR Pairing Process v2.1.3

## What's New

### Excel Import and Export (XLSX)

Team rosters and player ratings can now be imported from and exported to `.xlsx` Excel files in addition to CSV. All existing CSV workflows are unchanged.

### Import Templates

A new **Import Templates** popup (Data Management → Import Templates, or Ctrl+Shift+T) lets you download pre-filled template files in multiple formats:

- Single Team Import — XLSX or CSV
- Multiple Team Import — XLSX or CSV
- Names Only — roster template with no rating columns
- Download All (ZIP) — all templates bundled

Templates include editable example data showing the exact expected column format.

### Import Logs

**Data Management → Open Import Logs** (Ctrl+Shift+L) opens the folder where the app writes a timestamped log of every import operation. Useful for diagnosing unexpected import results.

### Keyboard Shortcuts

A full set of keyboard shortcuts is now available. Highlights:

| Shortcut | Action |
|---|---|
| Ctrl+Enter | Generate Combinations |
| Ctrl+S | Save Grid |
| Ctrl+1/2/3/4 | Apply sort mode |
| Ctrl+C / Ctrl+V | Copy / Paste 5×5 grid |
| Ctrl+Shift+T | Import Templates |
| Ctrl+Shift+S / Ctrl+Shift+X | Export CSV / XLSX |
| Ctrl+H | Open User Guide |

See the full shortcut reference in the bundled User Guide.

### Tab Navigation in the Rating Grid

Pressing Tab in any rating cell advances to the next cell in the row. Shift+Tab moves back. This makes data entry significantly faster for keyboard-driven workflows.

### Thread-Safe Database Connections

Internal database connections are now managed per-thread, preventing occasional errors when background operations accessed a connection created on the UI thread.

### Updated User Guide

The bundled `USER_GUIDE_v2.1.3.md` is a complete rewrite covering all features through this release. From now on, every release will include an up-to-date copy of the user guide.

---

## Bug Fixes

- **v2.1.2 hotfix carried forward**: Database creation no longer fails on first launch. SQL schema files are now correctly bundled into the compiled exe.

---

## Installation

1. Download `QTR_Pairing_Process_v2.1.3_release_bundle.zip` from the GitHub releases page.
2. Unzip anywhere on your PC.
3. Double-click `QTR_Pairing_Process_v2.1.3.exe` to launch. No installer required.

---

## Full Changelog

https://github.com/QTR-Games/QTR_pairing_process/compare/v2.1.2...v2.1.3
