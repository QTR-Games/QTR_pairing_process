# KLIK KLAK — User's Guide

*Play like you've got a pairing.*

KLIK KLAK is the pairing planner for 5v5 team miniature‑wargaming events (the
World Team Championship format). You rate your five players against their five
players, and the app tells you how the round is likely to go, which matchups you
can refuse, and — while you're at the table — what to nominate next.

It runs as one app on three platforms from the same code: a **desktop app**
(Windows, via the installer), an **iPhone/iPad home‑screen app**, and an
**Android app**. It works fully **offline** after the first open, and every board
is stored **on your device**.

> This guide covers the current KLIK KLAK app. The original Python/Tkinter
> desktop tool still ships for now and is documented separately (see
> [`USER_GUIDE.md`](USER_GUIDE.md) / [`FULL_USER_GUIDE.md`](FULL_USER_GUIDE.md)).

---

## Contents

1. [Installing](#installing)
2. [The three screens](#the-three-screens)
3. [Setting up a board](#setting-up-a-board)
4. [Reading the verdict](#reading-the-verdict)
5. [Running a live round](#running-a-live-round)
6. [Settings](#settings)
7. [Saved boards, backup & restore](#saved-boards-backup--restore)
8. [Importing an event from Longshanks](#importing-an-event-from-longshanks)
9. [Phone vs. desktop](#phone-vs-desktop)
10. [Your data & offline use](#your-data--offline-use)
11. [Glossary](#glossary)

---

## Installing

### Desktop (Windows)

1. Download the latest **`KLIK.KLAK_x.y.z_x64-setup.exe`** from the project's
   GitHub **Releases** page (the release tagged `desktop-v…`).
2. Run it. Because it isn't code‑signed yet, Windows SmartScreen may say
   *"Windows protected your PC."* Click **More info → Run anyway**.
3. The app installs to your account and adds a **KLIK KLAK** Start‑menu shortcut.
4. The desktop app **updates itself** — when a newer release is published it
   downloads and installs it in the background the next time you launch.

### iPhone / iPad

There's no App Store build. Open the project's web page in Safari, then use
**Share → "Add to Home Screen."** That icon launches a full‑screen app that
*"works with no signal after the first open."*

### Android

There is **no download link on purpose**. Ask whoever is running the event
laptop to install it: with your phone paired over Wi‑Fi they run
`npm run phone:install`, which pushes the app onto your phone.

---

## The three screens

The app is deliberately simple: three screens, no browser‑style navigation.

1. **Splash** — the launch screen showing **KLIK KLAK**, the tagline
   *"Play like you've got a pairing,"* and *"by GronkSoft."* Tap anywhere (or
   press any key) to skip straight through.
2. **Home menu** — your starting point. Its top button changes to match where
   you left off:
   - **Resume round vs [name]** — jumps back into a round already in progress.
   - **Open [opponent]** — reopens your most recent board.
   - **Start a new board** — when nothing is saved yet.
   - **Saved boards ([N])** — the list of everything you've saved.
   - **Back up and restore** — export/import your boards (see below).
   - The menu also holds all the **Settings** toggles.
3. **The app** — where the work happens. Get here from any menu button; the
   **Menu** button in the header takes you back.

On a **phone** the app has three tabs — **Board**, **Round**, **Saved**. On a
**wide/desktop** window it collapses to two — **Workspace** (board + round + the
verdict all at once) and **Saved**.

---

## Setting up a board

Open the **Board** tab (or **Workspace** on desktop).

- **Opponent team** — type the opposing team's name. It shows in the header and
  names the saved board. (Unnamed boards are listed as *"Untitled."*)
- **Us** / **Them** — your five players and their five players. Tap a name to
  edit it.
- **Who puts a player up first?** — which side nominates first (the "dice‑off"
  winner). Going first is usually an advantage because you control which of your
  players is exposed first.
- **Scale** — the rating scale you'll use. A one‑line hint explains each:
  | Scale | Range | Note |
  |-------|-------|------|
  | **Stoplight** | 1–3 | *"Red dodge, yellow even, green wanted."* |
  | **1‑5** *(default)* | 1–5 | *"The desktop app's default."* |
  | **1‑5, half steps** | 1–5 by 0.5 | *"Same habits, twice the resolution."* |
  | **1‑10** | 1–10 | *"The English convention."* |
  | **1‑20** | 1–20 | *"Fine enough to separate boards a 1‑5 sheet collapses."* |
  | **0‑100** | 0–100 by 5 | *"Win percentage, if you think in those terms."* |

### Rating the grid

The grid is your five players down the side, theirs across the top. **Tap a
cell** and pick a value. The picker reminds you which way it runs:
*"Worst matchup on the left, best on the right. The midpoint is an even game."*

Cells are colored **red → amber → green**: red is a matchup you'd want to dodge,
amber is roughly even, green is one you want. The scale blends *through* amber so
the middle reads as "even," not a muddy mix.

A board only counts as **rated** once you move at least one cell off dead‑even.
Until then the verdict shows *"Not rated yet"* — *"Every matchup is sitting on
dead even, so there is nothing to read yet. Tap a cell to rate it."* Rosters and
scale can be set any time.

**There is no Save button.** Edits persist automatically, so you never lose a
board (or a round you're standing in the middle of) to a reload.

---

## Reading the verdict

Once a board is rated, KLIK KLAK summarizes it. The headline **chip** tells you
the state of the round:

- **Not rated yet** — nothing to read.
- **Live** (amber) — still in play; your floor is below an even round and your
  ceiling is above it.
- **Already won** (green) — every remaining pairing wins the round. *"Anything
  further is bonus."*
- **Cannot be won** (red) — every remaining pairing loses. *"Play for the points
  you can still bank, not for the win."*
- **Too close to call** — shown when the typical result is a genuine coin flip
  (within the accuracy of the estimate).

### Three numbers: Guaranteed / Typical / Ceiling

The round is described as a **range**, not a single number:

- **Guaranteed** — the pessimistic floor: assumes the opponent has a perfect
  mirror of your grid and both sides play perfectly. *Use when you must not lose.*
- **Typical** — the realistic middle: assumes the opponent is playing their own
  board, not a mirror of yours. *Use when you must win.*
- **Ceiling** — the optimistic best still reachable with perfect play from your
  side.

### Two currencies

Numbers are shown in one of two **currencies**:

- **Round‑win %** *(default)* — your probability of winning 3+ of the 5 games,
  e.g. *"52% to take the round."*
- **Rating points** — the raw totals you wrote on the grid, e.g.
  *"18 guaranteed."*

They can disagree on close boards, and that's the point: two boards can total the
same yet sit on opposite sides of a coin flip, and the percentage catches it. You
can set the app‑wide default in Settings (**Show numbers as**), and several
verdict cards have their own toggle to flip currency just for that card.

### The insight cards

Depending on the board you may see cards such as:

- **Trade‑off (safest vs. boldest)** — appears only when your best *floor*
  opening differs from your best *ceiling* opening. *"Take the floor if you must
  not lose, take the ceiling if you must win"* — the one call the app leaves to
  you.
- **Dodge (price the worst matchup)** — your worst matchup, and whether the
  protocol lets you refuse it: **Forced** (can't — plan around it), **Free**
  (refuse it for nothing), or **Costly** (refuse it, but it costs X% of your
  round‑win chance).
- **Protect** — which of your players are **exposed** (their bad matchup repeats,
  so the opponent can force it) versus **shielded** (their bad matchup is a lone
  cell they can refuse). When two players tie for most‑exposed, you choose which
  to nominate first.
- **Dice‑off / initiative** — what going first (vs. second) is worth on this
  board.

On **desktop** you also get:

- **Reach** — the gap between what the grid promises and what the protocol can
  actually force: *"Best we can force on each of theirs"* and *"Worst they can
  force on each of ours."*
- **Currencies** — both currencies side by side.
- **Protocol tree** — the first three plies of the nomination game (opens →
  offers → picks) laid out with the totals at each leaf.

---

## Running a live round

Open the **Round** tab and start a round. KLIK KLAK walks you through the
nomination protocol one decision at a time, and the prompt at the top always
tells you exactly what to enter:

- **Put a player up** — when it's your side's turn to open.
- **Which player did they put up?** — record the opponent's opener.
- **Offer two against [their player]** — when you're the one offering a pair.
- **Which two did they offer against [your player]?** — record their offer, then
  pick one.
- **[Your player] vs [their player] — forced** — the last pair, which the rules
  leave no choice about.
- **Round complete** — every seat is filled.

As you commit pairings they lock in under **Tables set**, and their cells lock on
the grid so you can't rate them by accident. The verdict updates after every
decision, so you always know where the round stands. **Restart** (top‑right)
clears the round and starts over.

How much the app explains as you go is set by **Advice during a round**:

- **Full explanations** *(default)* — the reasoning behind each recommended pick.
- **Just the picks** — the recommendation with no commentary.
- **No advice** — record the round yourself with no guidance.

### Surprise‑pick alerts

Optionally, KLIK KLAK can flag when the opponent makes a move that gives up more
than you'd expect — a sign they're playing a different board than you predicted,
or protecting a player for a later round. Turn on **Surprise‑pick alerts**
(experimental) and set the **Surprise threshold (regret)** — the minimum number
of points "given up" before the alert fires.

### Table tracking

Once both players in a matchup are locked in, KLIK KLAK can pause and ask which
physical table the game was sent to — the thing that's easiest to forget in the
rush to the next nomination. **Table popup after a pairing** is **on** by
default; press **Skip** (or tap outside the popup) for any pairing you don't
want to record, or turn the setting off for an event that assigns tables another
way.

Tables you set appear beside each pairing under **Tables set** and in the final
result. The whole list can be copied to the clipboard with the **Copy** button,
a long press on a phone, or a right‑click on a laptop.

---

## Settings

All settings live in the **Home menu**. They're shared across phone and desktop
and saved immediately.

| Setting | Label | Options (default **bold**) |
|---------|-------|----------------------------|
| Dodge pricing | **Price the worst matchup** | **When I ask** / Always / Never |
| Advice | **Advice during a round** | **Full explanations** / Just the picks / No advice |
| Currency | **Show numbers as** | **Round‑win %** / Rating points |
| Surprise alerts | **Surprise‑pick alerts** | **Off** / On (experimental) |
| Surprise threshold | **Surprise threshold (regret)** | number (default **0**) |
| Table tracking | **Table popup after a pairing** | **On** / Off |

---

## Saved boards, backup & restore

Every board you name or rate is saved automatically and appears under **Saved**
(**Saved boards** in the menu). From there you can **New board**, open one, or
**Delete** one. Opening a board that had a round in progress drops you back into
that round.

> **Boards live on this device only. Installing a new build can clear them, so
> keep a copy somewhere else.** — this is why backup exists.

Backup/restore is in **Menu → Back up and restore**. It gives you three ways out
and three ways back in so it works on any platform:

**Export ("Save your boards")**
- **Save a copy** — write a `qtr-boards-YYYYMMDD-HHMMSS.json` file (a native Save
  dialog on desktop).
- **Copy** — copy the backup to the clipboard: *"Paste it somewhere you keep
  things."*
- **Show** — display the backup text so you can copy it by hand.

**Restore**
- **Choose a file** — pick a backup file.
- **Restore** — **merge** a pasted backup: adds new boards and updates existing
  ones by ID. You'll see *"[N] restored, [M] updated, [K] already current."*
- **Replace all** — **destructive**: after confirming *"Replace every board on
  this device with the backup?"* it clears everything first, then imports.

---

## Importing an event from Longshanks

Instead of typing every opposing roster, you can pull a whole event from
Longshanks (**Menu → Back up and restore → Import from Longshanks**, or the
import panel):

1. Enter the event and press **Fetch** to download the rosters.
2. Choose **Your team** from the event's team list.
3. Press **Build boards** to create one board per opposing team, pre‑filled with
   their players.

Teams without five named players are skipped, with a note like *"[N] team was
skipped for not having five named players. Add them by hand, or download the list
to check what was missing"* — use **Save the list** to export the skipped teams.

Longshanks import needs a network connection and works on the **desktop app** and
the **Android app** (both make direct requests). Once boards are built, rating
and running rounds is fully offline. On boards imported this way you can
**long‑press an opponent's name** to see their faction/lists.

---

## Phone vs. desktop

**Phone**
- Three tabs — **Board / Round / Saved** — one thing on screen at a time.
- **Long‑press a cell** to see that matchup's opening cost and dodge price.
- The grid stays pinned while you scroll the verdict cards below it.

**Desktop (wide window)**
- **Workspace** shows the board, the verdict, and the live round together.
- **Hover a cell** to reveal exposure/dodge heat instead of long‑pressing.
- Extra panels: **Reach**, **Currencies**, and the interactive **Protocol tree**.
- **Native Save/Open dialogs**, a native menu bar, and the window remembers its
  position and size between sessions.

---

## Your data & offline use

- Everything is stored **locally** — nothing is uploaded. On the desktop and
  Android apps that's a local database; on the web/iOS home‑screen app it's
  browser storage.
- After the first open the app runs **with no signal**. Only publishing a
  Longshanks event and (on desktop) checking for updates need a connection.
- Because storage is local and per‑device, **back up before installing a new
  build** and to move boards to another device.

---

## Glossary

- **Board** — one saved matchup sheet: opponent, both rosters, the ratings, the
  scale, and who goes first.
- **Currency / unit** — how numbers are shown: **round‑win %** or **rating
  points**.
- **Dice‑off / initiative** — who nominates first (decided by dice before the
  round).
- **Dodge** — refusing your worst matchup. The app tells you whether that's
  **forced**, **free**, or **costly**.
- **Exposed / shielded** — whether a player's worst matchup can be forced on them
  (exposed) or refused (shielded).
- **Guaranteed / Typical / Ceiling** — the pessimistic floor, the realistic
  middle, and the optimistic best of the round‑win range.
- **Protocol** — the turn‑taking nomination rules: open → offer two → pick one,
  repeated until all five are paired.
- **Rated** — a board with at least one cell moved off dead‑even.
- **Reach** *(desktop)* — the gap between what the grid promises and what the
  protocol can actually force.
- **Regret** — points a move gives up versus the best available move; drives the
  surprise alert.
- **Surprise** — an alert that the opponent gave up more than expected.
- **Trade‑off (safest vs. boldest)** — the choice between the best floor and the
  best ceiling opening.
- **Verdict** — the overall read of the round: **Live**, **Already won**, or
  **Cannot be won**.
