# KLIK KLAK — claims sheet

Every factual claim we make in public about what this app does, with the
evidence behind it and the command that reproduces it.

The rule: **no number goes in public copy unless it is traceable to a named
assertion, derivation or measurement in this repository** — and the headline
numbers must be CI-pinned. Marketing claims rot quietly — the engine improves,
the fixture set grows, and a sentence written against one set of numbers keeps
being repeated against another. Tying each claim to an assertion means a claim
that stops being true breaks the build instead of staying on a page.

Each claim below is tagged with the strength of its backing:

- **[CI]** — asserted on every run. Cannot drift without failing the build.
- **[measured]** — produced by a `measure.*` harness, which is skipped by
  default because it is slow or stochastic. Re-run before quoting.
- **[derived]** — a structural result proved in the docs, not a measurement.

Reproduce the headline numbers:

```powershell
cd webapp
npx vitest run src/engine/adClaims.test.ts
```

Reproduce the demo boards those numbers describe:

```powershell
cd webapp
npx vitest run src/model/demoBoards.test.ts
```

Or press **See it working — load 3 examples** on the home screen of the app
itself, which installs the same three boards this document cites.

---

## The evidence base

31 real boards from WTC 2024, anonymised at capture, in
`webapp/src/engine/__fixtures__/wtc2024Boards.json`. Ratings are genuine; team
and player names were replaced at the point of capture, so nothing here
attributes an opinion about a matchup to a named player.

Two ways of reading the same board run throughout:

| | what it is | what it is worth |
|---|---|---|
| **Assignment ceiling** | best total over all 120 one-to-one matchings | the score of a matching nobody has agreed to |
| **Protocol floor** | the total that survives the real nomination-and-decline sequence against an opponent playing their best | what you can hold regardless of what they do |

The ceiling is reachable only with the opponent's cooperation. The difference
between the two is the part of a plan that depends on them being helpful.

---

## Claim 1 — the matching view overstates what you can hold **[CI]**

> Across 31 real WTC 2024 boards, the best-matching view overstates what you
> can actually hold by **1.45 points on average**, and by as much as **3**.

Asserted by `adClaims.test.ts` → *"the best-matching view overstates what you
can hold"*, as an exact triple: mean 1.45, max 3, min 0.

The floor used is the better of opening and receiving, because the dice-off
winner picks their side. Quoting one side only would overstate the gap.

## Claim 2 — most boards that look won are not secured **[CI]**

> **22 of 31** boards look like a win on the matching view and are not
> actually secured.

Asserted by `adClaims.test.ts` → *"counts the boards that look won on paper and
are not secured"*.

A board counts when its assignment ceiling is above the dead-even line of 15
while its protocol floor is at or below it. These are boards where a
permutation ranker shows a winning total and the guarantee is level or worse.
This is the specific failure the protocol view exists to catch, and it is the
common case rather than the exception.

## Claim 3 — the app plays the real protocol, not a permutation ranking **[derived]**

> KLIK KLAK solves the nomination-and-decline sequence the Player Pack
> actually specifies, including the dice-off, who opens, and what happens to a
> declined player.

Evidence is the engine itself: `webapp/src/engine/protocol.ts`
(`protocolFloor`, `solveProtocol`, `openingChoice`), exercised by
`measure.protocol.test.ts`, `measure.openOrReceive.test.ts` and
`measure.diceoff.test.ts`.

The structural point, derived in `docs/WHITEPAPER.md`: a five-a-side round has
**14,400 distinct protocol paths** against 120 matchings. A tool that ranks the
120 is not answering the question the captains are actually asked.

The 14,400 figure is a hand-derivation from the Player Pack sequence,
independently re-derived once. It is not pinned by a test — if it ever appears
in paid copy rather than explanatory writing, assert it first.

## Claim 4 — the dice-off is priced, not guessed **[measured]**

> Win the roll and the app tells you whether to open or receive, in points and
> in win probability.

`openingChoice` in `protocol.ts`; `measure.openOrReceive.test.ts` prices the
decision across the fixture set. The demo board *The optimistic matching* is
one where the two sides genuinely differ, so the decision is visible rather
than hypothetical.

## Claim 5 — it says when the choice does not matter **[CI]** / **[measured]**

> On a board that is genuinely level, the app says so instead of inventing a
> recommendation.

`Verdict.tsx` suppresses a verdict when the expected result sits within two
standard errors of even — the mechanism is CI-tested. Calibration: the true
result fell inside that interval on **29 of 31** boards, never outside. That
figure comes from a 4000-trial reference run (see the note at `Verdict.tsx`
line 301 and `opponent.test.ts`), is stochastic, and is therefore **[measured]**
rather than CI-pinned — re-run it before quoting the number itself. The demo
board *Too close to call* triggers the behaviour, and `demoBoards.test.ts`
asserts that it still does.

This one is a liability claim as much as a feature claim. It is the reason the
other four can be stated plainly.

---

## Copy rules

- **Do not name competing tools.** They are hobbyist projects. Claims are
  stated as capabilities of this app, never as deficiencies of a named other.
  Anything else reads badly and invites a response we would rather not have.
- **No speed claims without a fresh measurement.** Any timing figure must be
  re-measured on current hardware immediately before publication and added to
  `adClaims.test.ts` as a bound, not an exact value.
- **Quote the floor, not the ceiling.** Using a ceiling number in our own copy
  would be the exact error claim 1 complains about.
- **"Real WTC 2024 boards, anonymised"** is the correct provenance phrase. Do
  not imply we have named players' private ratings.

## Adding a claim

1. Write the assertion in `webapp/src/engine/adClaims.test.ts` first.
2. Run it. If it fails, the claim is wrong — fix the sentence, not the test.
3. Add a section here with the test name, so the claim can be traced back from
   the copy without reading the engine.
