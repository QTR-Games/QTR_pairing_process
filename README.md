# QTR Pairing Process

![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red)
![Platforms](https://img.shields.io/badge/Platforms-Windows%20%C2%B7%20iOS%20%C2%B7%20Android-blue)
![Status](https://img.shields.io/badge/Status-Active%20Development-green)

Tournament pairing tools for 5v5 team miniature‑wargaming events (the World Team
Championship format), by Daniel P. Raven and Matt Russell. **QTR** stands for
*"Quote The Raven."*

This repository contains two applications:

- **KLIK KLAK** — the current cross‑platform app (desktop, iPhone/iPad, Android).
  **This is the app to use.**
- **QTR Pairing Process (legacy)** — the original Python/Tkinter desktop tool,
  still shipped for now and documented below.

---

## KLIK KLAK

*Play like you've got a pairing.*

KLIK KLAK is a fast, offline pairing planner. You rate your five players against
the opponent's five, and it tells you how the round is likely to go, which
matchups you can refuse, and — while you're at the table — what to nominate next.
One codebase ships as a Windows desktop app, an iOS home‑screen app, and an
Android app. Boards are stored **on your device** and everything works with **no
signal** after the first open.

### Highlights

- **5×5 rating grid** with six scales (Stoplight, 1‑5, 1‑5 half‑steps, 1‑10,
  1‑20, 0‑100) and red→amber→green heat.
- **Round verdict** as a range — **Guaranteed / Typical / Ceiling** — in either
  **round‑win %** or **rating points**.
- **Insight cards**: trade‑off (safest vs. boldest), dodge pricing, protect
  (exposed vs. shielded), dice‑off value, and (on desktop) reach and the
  interactive protocol tree.
- **Live round assistant** that walks the nomination protocol one pick at a time,
  with adjustable advice and optional surprise‑pick alerts.
- **Longshanks import** — build one board per opposing team straight from an
  event roster.
- **Backup & restore** with merge or full‑replace, so boards survive a new build
  or move to another device.
- **Desktop niceties**: native Save/Open dialogs, native menu, window memory, and
  **self‑updating** installs.

### Install

- **Windows (desktop)** — download `KLIK.KLAK_x.y.z_x64-setup.exe` from the
  [Releases](https://github.com/QTR-Games/QTR_pairing_process/releases) page (the
  `desktop-v…` release) and run it. On the SmartScreen warning, click
  **More info → Run anyway** (the installer isn't code‑signed yet). It
  auto‑updates itself after that.
- **iPhone / iPad** — open the web app in Safari and **Share → Add to Home
  Screen**.
- **Android** — the event laptop runs `npm run phone:install` with your phone
  paired over Wi‑Fi (no public download by design).

### Documentation

- 📘 [**User's Guide**](docs/klikklak-users-guide.md) — full walkthrough of every
  screen, setting, and concept.
- ⚡ [**Tip Sheet**](docs/klikklak-tip-sheet.md) — one‑page cheat sheet for the
  table.
- 🛠️ [**How‑to Guide**](docs/klikklak-how-to.md) — task‑by‑task recipes.

### Building it yourself

The KLIK KLAK frontend lives in [`webapp/`](webapp/). Desktop packaging and the
signed auto‑update pipeline are described in
[`docs/desktop-release.md`](docs/desktop-release.md); the Android build in
[`docs/android-build.md`](docs/android-build.md).

---

## Legacy desktop tool (Python / Tkinter)

The original **QTR Pairing Process** is a Tkinter desktop application for the same
tournament format. It remains in the repo and is supported through the current
event; new work happens in KLIK KLAK.

### What it does

- Interactive **5×5 matchup grid** rated on a 1–5 scale (1 = near‑certain loss,
  3 = even, 5 = near‑certain win).
- **Decision‑tree generator** visualizing every possible pairing, with MAX / MIN
  / SUM / AVG evaluation modes and three tree‑sorting strategies (Cumulative,
  Highest Confidence, Counter Pick).
- **Seven WTC scenarios** (0–6), a **comments system** (per‑scenario annotations,
  2000‑char limit), **SQLite** storage, and **CSV / Excel** import‑export.

### Running it

Prerequisites: Python 3.7+ with Tcl/Tk. For best Windows reliability, use
python.org Python (not the Microsoft Store build).

```bash
git clone https://github.com/QTR-Games/QTR_pairing_process.git
cd QTR_pairing_process
pip install -r requirements.txt
python main.py
```

`entrypoint.py` is the packaged entry point, and `setup.py` remains the supported
build path.

### Runtime health (Windows)

On startup the app runs a **Tk preflight** so a partial/misconfigured Python‑Tk
install stops gracefully with an actionable message instead of a crash. If it
fails: install python.org Python with Tcl/Tk, recreate your virtual environment,
reinstall with `pip install -r requirements.txt`, and relaunch. Diagnostics are
written to `qtr_pairing_process.log`. Pytest runs the same preflight during
collection and skips Tk‑dependent tests when Tk is unavailable rather than
failing the suite.

### Legacy documentation

Detailed docs for the Tkinter tool live in [`docs/`](docs/), including
[Comments System](docs/COMMENTS_SYSTEM.md), [Tree Sorting](docs/SORTING_ANALYSIS.md),
and the legacy [User Guide](docs/USER_GUIDE.md) / [Full User Guide](docs/FULL_USER_GUIDE.md).

---

## Tournament format

Both apps target the **World Team Championship (WTC)** format: exactly 5 players
per team, team‑vs‑team, paired one player at a time under the nomination protocol.

## Contributing

Actively developed by Daniel P. Raven and Matt Russell. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

© Daniel P Raven and Matt Russell 2024. All Rights Reserved.

## Support

For questions, issues, or feature requests, contact the development team or open
an issue in the repository.

---

*Designed for competitive miniature‑wargaming tournaments following the World
Team Championship format.*
