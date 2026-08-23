# Contributing to QTR Pairing Process

Thanks for working on QTR Pairing Process. This guide covers local setup, how to run
and add tests, the linting baseline, and how changes get reviewed and merged.

> This is proprietary software (see `LICENSE`). Contributions are accepted only from
> authorized collaborators.

## 1. Local setup

Requirements: Python 3.11+ (the app also runs on the standard CPython that ships with
`tkinter`), on Windows or Linux.

```powershell
git clone https://github.com/QTR-Games/QTR_pairing_process.git
cd QTR_pairing_process
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows
# source .venv/bin/activate       # Linux/macOS
python -m pip install -r requirements.txt
python -m pip install pytest ruff mypy
```

Run the app:

```powershell
python main.py                # or: python entrypoint.py --perf
```

## 2. Running the tests

```powershell
python -m pytest -q
```

- Tests live at the repo root (`test_*.py`).
- **Tk-dependent tests skip automatically when no display is available** (headless).
  That's expected locally if you run in a headless shell.
- To force the Tk tests to run on **Linux/CI**, use a virtual display:
  ```bash
  xvfb-run -a python -m pytest -q
  ```
  On **Windows**, Tk runs natively - no extra setup.

### Adding a test

- Name it `test_<feature>.py` at the repo root, matching the existing suite.
- If it drives Tk widgets, mark it `@pytest.mark.requires_tk` so the skip logic is
  explicit:
  ```python
  import pytest

  @pytest.mark.requires_tk
  def test_tree_renders():
      ...
  ```
- Prefer testing logic (data models, validators, importers/exporters) without Tk where
  possible - those tests run everywhere, including headless CI.

## 3. Linting and types

We use `ruff` (lint + import order) and `mypy` (types). Configuration lives in
`pyproject.toml`.

```powershell
python -m ruff check .
python -m mypy qtr_pairing_process
```

During the initial rollout, lint/type findings are **advisory** (they annotate PRs but
do not block). They will become blocking once the baseline is clean. Please don't add
new findings.

## 4. Branch, commit, and PR flow

1. Branch off `main`: `git switch -c <type>/<short-description>` (e.g.
   `feat/xlsx-export-headers`, `fix/tree-sync-crash`).
2. Make focused changes. **Do not touch** release artifacts, bundled builds, sample
   data, or PDFs unless the task is about the release pipeline.
3. Run tests and `ruff check .` locally.
4. Push and open a PR into `main`. Fill out the PR template.
5. CI (`tests`) must be green. A code owner reviews and merges.

### Commit messages

Use a short, conventional prefix and an imperative summary:

```
feat: add XLSX export header row
fix: prevent crash when matchup cache is empty
chore: pin openpyxl minimum version
test: cover decision-tree sync edge case
docs: document Tk-headless testing
```

## 5. Optional: local pre-commit hook

A pre-commit hook that runs `ruff` and the fast (non-Tk) tests is available under
`githooks/`. Enable it once per clone:

```powershell
git config core.hooksPath githooks
```

## 6. Getting help / architecture

See `.github/copilot-instructions.md` for the architecture map and module overview -
it's the fastest orientation to the codebase, whether you're a person or an AI agent.

## Optional: local pre-commit hook

This repo ships an opt-in pre-commit hook that runs `ruff` on your staged changes and the fast (non-Tk) test subset before each commit, so obvious problems are caught before they reach CI.

**off by default**. To enable it in your clone:

```sh
git config core.hooksPath githooks
```

To disable it again:

```sh
git config --unset core.hooksPath
```

To skip it for a single commit (emergency):

```sh
git commit --no-verify
```

The hook is intentionally lightweight and never needs a display. The full suite (including
Tk tests across Linux and Windows) still runs in CI regardless of whether you use the hook.
