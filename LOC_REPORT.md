# Application LOC Summary

This repository currently has **16,721** non-blank, non-comment lines of Python code in the functional application (main branch).

Counting rules:
- Included all `*.py` files.
- Excluded documentation and ancillary directories: `docs`, `release`, `import_logs`, `legacy`, `scripts`, and common cache/metadata folders.
- Excluded test files by pattern: `test_*.py`, `*_test.py`, `test.py`, `test2.py`, and `conftest.py`.
- Lines counted only when they are non-empty and not starting with `#`.

How to reproduce:
```bash
python scripts/count_loc.py --per-file
```

Run date: 2026-03-20.
