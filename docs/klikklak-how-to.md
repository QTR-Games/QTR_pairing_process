# KLIK KLAK — How‑to Guide

Task‑by‑task recipes. For concepts and definitions, see the
[User's Guide](klikklak-users-guide.md); for a one‑page cheat sheet, the
[Tip Sheet](klikklak-tip-sheet.md).

---

## Set up a board by hand

1. Open the **Board** tab (**Workspace** on desktop) — from the home menu use
   **Start a new board**, or **New board** on the Saved screen.
2. Type the **opponent team** name (this also names the saved board).
3. Fill in **Us** and **Them** — tap each of the five names to edit.
4. Set **Who puts a player up first?** to the side that won the dice‑off.
5. Pick a **Scale** (1‑5 is the default; Stoplight is fastest for a quick read).
6. **Tap each cell** and choose how good that matchup is —
   *worst on the left, best on the right, midpoint is even.*
7. There's nothing to save — the board is stored the moment you edit it.

---

## Import a whole event from Longshanks

1. Open the import panel (**Menu → Back up and restore → Import from
   Longshanks**).
2. Enter the event and press **Fetch**.
3. Choose **Your team** from the list.
4. Press **Build boards** — you get one board per opposing team, rosters
   pre‑filled.
5. If you see *"[N] team was skipped for not having five named players,"* press
   **Save the list** to export the skipped teams and add them by hand.
6. Rate each board's grid as usual. (Requires a connection; desktop and Android
   only. Rating and rounds afterward are offline.)

> Tip: on imported boards, **long‑press an opponent's name** to see their
> faction and lists.

---

## Read whether you should play safe or bold

1. Rate the board, then read the **verdict**.
2. Check the chip — **Live**, **Already won**, or **Cannot be won**.
3. Look at the three numbers:
   - Chase **Guaranteed** when you can't afford to lose the round.
   - Chase **Typical** when you need the win.
4. If a **Trade‑off (safest vs. boldest)** card appears, that's the one call the
   app won't make for you: **safest** opener protects your floor, **boldest**
   opener chases your ceiling.
5. Not sure the numbers agree? Toggle **Show numbers as** (or the card's own
   toggle) to compare **round‑win %** against **rating points**.

---

## Decide whether to dodge your worst matchup

1. Find the **Dodge (price the worst matchup)** card.
2. Read the price:
   - **Forced** — you can't refuse it; plan around it instead.
   - **Free** — refuse it at no cost.
   - **Costly** — refuse it, but it costs the shown % of your round‑win chance.
3. To make the app always/never show this, set **Price the worst matchup** in
   Settings to **Always** or **Never** (default **When I ask**).

---

## Run a round at the table

1. Open the **Round** tab and start the round.
2. Follow the prompt at the top for each decision:
   - **Put a player up** → nominate one of yours.
   - **Which player did they put up?** → record their opener.
   - **Offer two against [name]** → offer a pair of yours.
   - **Which two did they offer…?** → record their pair and pick one.
   - **… — forced** → the last, forced pair.
3. Each committed pairing appears under **Tables set** and locks on the grid.
4. Keep an eye on the verdict — it updates after every pick.
5. Made a mistake? **Restart** (top‑right) clears the round.

**Quieter or louder guidance:** set **Advice during a round** to **Full
explanations**, **Just the picks**, or **No advice**.

---

## Catch a surprise pick

1. In Settings, turn on **Surprise‑pick alerts (experimental)**.
2. Set **Surprise threshold (regret)** to the minimum points "given up" before an
   alert fires (start at a few points to avoid noise).
3. Run the round as normal — if the opponent gives up more than the threshold on
   a pick, KLIK KLAK flags it so you can reconsider what board they're playing.

---

## Back up before installing a new build

1. **Menu → Back up and restore.**
2. Export with whichever fits:
   - **Save a copy** → writes `qtr-boards-YYYYMMDD-HHMMSS.json`.
   - **Copy** → puts the backup on the clipboard.
   - **Show** → displays the text to copy by hand.
3. Install the new build.
4. Restore with **Choose a file** (or paste) → **Restore** to merge your boards
   back in.

> Do this every time — **boards live on this device only, and a new install can
> clear them.**

---

## Move your boards to another device

1. On the old device: **Menu → Back up and restore → Save a copy** (or **Copy**).
2. Get the file/text to the new device (AirDrop, email, cloud, clipboard).
3. On the new device: **Menu → Back up and restore → Choose a file** (or paste).
4. Press **Restore** to merge, or **Replace all** to make the new device an exact
   copy (this wipes anything already there — you'll be asked to confirm).

---

## Install the desktop app

1. Download **`KLIK.KLAK_x.y.z_x64-setup.exe`** from the GitHub **Releases** page
   (the `desktop-v…` release).
2. Run it. On *"Windows protected your PC,"* click **More info → Run anyway** (the
   installer isn't code‑signed yet).
3. Launch **KLIK KLAK** from the Start menu.

## Update the desktop app

Nothing to do — the desktop app checks for new releases and updates itself in the
background. Just relaunch it now and then; it installs the latest on the next
start.

---

## Install on iPhone / iPad

1. Open the project's web page in **Safari**.
2. Tap **Share → Add to Home Screen**.
3. Launch it from the new icon — it runs full‑screen and works offline after the
   first open.

## Install on Android

There's no public download by design. Ask the person with the event laptop to
run `npm run phone:install` with your phone paired over Wi‑Fi; it pushes the app
straight onto your phone.
