# QTR Pairing Process agent entrypoint

The authoritative repository guide is
[`.github/copilot-instructions.md`](.github/copilot-instructions.md).

## 30-second overview

- This is a Python/Tkinter desktop application, with Windows as the primary
  platform.
- Use `python main.py` for the normal launcher; `entrypoint.py` supports the
  packaged entry point.
- Run tests with `python -m pytest -q`; Linux GUI tests use Xvfb and Windows
  uses native Tk with an isolated `--basetemp`.
- Ruff is advisory. Do not modify release artifacts, sample data, or PDFs
  without an explicit request.
- Keep `setup.py` functional because it remains the supported build path.

Task-focused guidance for reusable work lives in
[`.github/skills/README.md`](.github/skills/README.md).
