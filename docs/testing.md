# Testing

## Local workflow

Tests live at the repository root as `test_*.py` files. On Windows, use the
task runner:

```powershell
.\dev.ps1 setup
.\dev.ps1 test
.\dev.ps1 test-fast
.\dev.ps1 check
```

`test` runs `pytest -q`. `test-fast` adds `-x` and
`-m "not requires_tk"` to stop at the first failure while excluding explicit
Tk tests. `check` runs Ruff, mypy against `qtr_pairing_process`, and the full
test suite.

Each pytest invocation receives a unique `--basetemp` directory and removes it
in `finally`. This avoids Windows `WinError 5` failures when pytest tries to
clean a shared `pytest-current` directory; that cleanup failure is
infrastructure noise, not an application test failure.

## Tk-aware collection

The project configures the `requires_tk` marker with strict markers enabled,
so marker typos fail rather than silently changing selection. During
collection, `conftest.py` runs the Tk preflight once. If the runtime cannot
create a Tk root, explicitly marked tests—and tests detected as constructing
Tk widgets—are skipped with a diagnostic entry in
`qtr_pairing_process.log`.

That is intentionally different from skipping the whole suite: non-UI logic
still runs when no display is available.

## CI model

The GitHub Actions workflow runs the complete suite on Python 3.11 and 3.12
under Linux using Xvfb, then on native Windows with Python 3.12. Xvfb supplies
the display that Tk needs on Linux; Windows uses its native Tk runtime. Both
jobs pass an isolated pytest base temp directory, and the final `tests` job
requires both platforms to succeed.

Keep path examples platform-aware. The Linux workflow uses
`${{ runner.temp }}/pt`; the Windows workflow uses
`${{ runner.temp }}\pt`. Do not hard-code one separator into cross-platform
automation—let the shell and platform determine the correct path form.
