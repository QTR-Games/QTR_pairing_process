# WTC 2024 Ground Truth — What the Real Tournament Says About the Model

**Status:** Measured, not theorised. Every number below comes from the real event.
**Sources:**
- Outcomes: Longshanks event 10904 (Warmachine WTC 2024, Düsseldorf, 32 teams / 160 players),
  scraped in full and ingested to `wtc2024.db` — **400 games**, 5 rounds × 80.
- Ratings: `teamIrving2024_FinalDB.db` — the **5,425 ratings Team Irving assigned before the
  event**, covering all 5 of their players against all 155 opponents across 7 scenarios.

This is the first time in the project's history that the model's *inputs* can be checked against
the *outcomes they were meant to predict*.

---

## 0. Team Irving's actual run

| Round | Table | Opponent | Score | Result |
|---|---|---|---|---|
| 1 | 11 | Germany Fuchs | 3-2 | W |
| 2 | 1 | Norway Hugin | 4-1 | W |
| 3 | 3 | England Dragons | 4-1 | W |
| 4 | 3 | Mussels from Brussels | 3-2 | W |
| 5 | 1 | **Australia Thorny Devils** | **2-3** | **L** |

Individual records: Garbarini 4-1, VanMeter 4-1, Steve 3-2, Du 3-2, Coe 2-3 (**16-9 overall**).

---

## Finding 7 — The scenario dimension carries no information. None. Anywhere.

The engine models 7 scenarios. Every rating is stored per-scenario, the tree carries the
dimension, and data entry asks the user to fill it 7 times.

**In every real database ever produced, the rating is identical across all 7 scenarios.**

| Database | Matchup cells | Cells that vary by scenario |
|---|---:|---:|
| `teamIrving2024_FinalDB.db` | 775 | **0** |
| `SWINETASTIC.db` | 175 | **0** |
| `SWINETASTIC_20241030.db` | 175 | **0** |
| `default.db` | 25 | **0** |
| **Total** | **1,150** | **0** |

Maximum distinct ratings found in any cell, in any database: **1**.

### Why this matters on all three fronts

- **Speed.** Any scenario-aware expansion is a 7× multiplier over a constant. The
  scenario axis can be collapsed to a single plane with *provably identical* output on
  real data, and re-expanded only if a cell ever genuinely varies.
- **Data entry.** The user is asked for 5,425 numbers where 775 would be lossless — a
  **7× reduction in the most tedious part of using the app**.
- **Analysis.** There is no scenario signal to find. Nothing downstream should claim one.

### The honest caveat

This measures *what users actually enter*, not *what the game theoretically supports*.
Scenarios plausibly do matter in reality; nobody has ever expressed that belief through
this interface. That is a **UI finding as much as a math finding** — the per-scenario grid
is either too costly to fill differentially, or its value was never made visible.
**Recommendation: collapse by default, keep the capability, and make divergence cheap and
obvious to express.** Do not delete the dimension.

---

## Finding 8 — The ratings were flat, and flattest exactly where it mattered most

Distribution of all 5,425 WTC 2024 ratings:

| Rating | Count | Share |
|---:|---:|---:|
| 1 | 161 | 3.0% |
| 2 | 840 | 15.5% |
| 3 | **4,018** | **74.1%** |
| 4 | 406 | 7.5% |
| 5 | **0** | **0.0%** |

**A rating of 5 was never used once.** 89.6% of all input sits in just two adjacent levels.
The effective input alphabet is ~2 symbols on a 5-symbol scale.

Compare a different event from the same user:

| Database | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|
| `SWINETASTIC.db` | 6% | 7% | 50% | 34% | 3% |
| `teamIrving2024_FinalDB.db` | 3% | 16% | **74%** | 8% | **0%** |

So flatness is **not** a habit of the user. It is a property of *this* event: at a world
championship every opponent is genuinely competent, so honest ratings compress toward the
middle. **The tool must work hardest precisely where its input signal is weakest** — and today
it does the opposite, because near-uniform input makes every branch of the tree look alike.

This is the mechanism behind the "false coin flip" reported in
`DECISION_SENSITIVITY_FINDINGS.md`. It is not a bug in the search. It is the search
faithfully reporting that the input contains no preference.

---

## Finding 9 — Calibration: the ratings were pessimistic and non-monotonic

Every Team Irving game, joined to the rating assigned beforehand (23 of 25 matched; 2 lost to
a team-name encoding mismatch):

| Rating | Games | Won | Lost | **Actual win %** | Implied by scale |
|---:|---:|---:|---:|---:|---:|
| 2 | 4 | 3 | 1 | **75%** | 25% |
| 3 | 18 | 12 | 6 | **67%** | 50% |
| 4 | 1 | 1 | 0 | 100% | 75% |
| **All** | **23** | **16** | **7** | **70%** | **~45%** |

Two things are true here, and they carry very different confidence:

1. **The scale is not monotonic in this sample** — rating 2 outperformed rating 3.
   *n=4 at rating 2. This is not evidence of inversion; it is evidence of noise.*
   Do not act on it. It is recorded so nobody re-derives it and over-claims.
2. **The ratings were systematically pessimistic** — Irving won 70% while their own
   numbers implied ~45%. With 23 games this is suggestive, not conclusive, but it points
   the same direction as Finding 8: ratings crowd toward 3 regardless of true strength.

**Consequence for the engine.** Every scoring rule in `SCORING_MATHEMATICS.md` treats the
rating as a calibrated strength. On this evidence it is closer to an *ordinal hint with a
pessimistic bias*. That does not invalidate the search, but it does mean **absolute path
totals are not meaningful quantities** — only comparisons between lines are.

---

## Finding 10 — The Australia "bus", reconstructed

The unsolved problem: *"those madmen just threw out reason and 'bussed' a player to line up a
bunch of other favorable matchups and it kinda took our team for a ride."*

Here is the full 5×5 grid Team Irving built before that round (scenario 0; identical in all 7):

|  | House Kallyss<br>(Tacken) | Sea Raiders<br>(de Oliveira) | Exalted<br>(Delrogue) | Winter Korps<br>(Glavas) | Infernals<br>(James) |
|---|:--:|:--:|:--:|:--:|:--:|
| **Justin** | 3 | 3 | 3 | 2 | 3 |
| **Mike** | 3 | 3 | 2 | 2 | 3 |
| **Rick** | 3 | 3 | 3 | 3 | 3 |
| **Stephen** | 3 | 3 | 2 | 3 | **1** |
| **Jake** | 3 | 3 | 3 | **1** | 3 |

Mean 2.68. **Nineteen of twenty-five cells are the same number.**

And what actually happened:

| Our player | Prio | Score | Opponent | Faction | Rated | Result |
|---|---|---|---|---|:--:|---|
| Jake VanMeter | Attacker | 6-3 | Come What May – James | Infernals | 3 | **W** |
| Justin Du | Attacker | 8-7 | Delrogue | Exalted | 3 | L |
| Michael Garbarini | Attacker | 15-9 | Aleks Bison Glavas | Winter Korps | 2 | **W** |
| Rick Coe | Attacker | 5-8 | Daniel Nads Tacken | House Kallyss | 3 | L |
| **Steve** | **Defender** | **2-8** | **Robin de Oliveira** | **Sea Raiders** | 3 | **L** |

### What the reconstruction actually shows

**The bus was not the mechanism.** The two catastrophic cells in the grid — Stephen vs
Infernals (1) and Jake vs Winter Korps (1) — *never happened*. Australia did not steer Irving
into either of its own identified disasters.

**The mechanism was that the grid had nothing to say.** Australia assembled a board that
Irving's own numbers scored as five near-identical coin flips, and won it 3-2. There was no
trap to see, because with 19 identical cells there was no shape to the position at all. A
search over a near-uniform matrix returns near-uniform advice, and the team went in believing
the round was even when the truth was that they had **no information**.

The single decisive game — Steve losing 2-8 to Sea Raiders — was rated **3, dead even**.
Sea Raiders was, by the event-wide numbers below, the **strongest faction in the tournament**.
That gap between "rated even" and "objectively the best army in the room" is the actual failure,
and it is an *input* failure that no amount of search quality can repair.

> **This reframes the whole "protect us from being bussed" requirement.** The defence is not a
> better search over the grid. It is (a) telling the user *when their grid is too flat to
> support a recommendation*, and (b) supplying outside information — like the faction priors
> below — that the grid does not contain.

---

## Finding 11 — The terrain/table signal is real, and the app has never modelled it

Longshanks records an **Attacker / Defender** priority per player per game — the table and
terrain choice. Across all 400 games:

| Priority | Games | Win rate |
|---|---:|---:|
| Attacker | 398 | 51.0% |
| Defender | 398 | 49.0% |

Globally it is a **coin flip**, which looks like a dead end. It is not. Splitting by faction
(minimum 8 games in each role) shows large effects of *opposite sign* that cancel in aggregate:

| Faction | Att N | Att % | Def N | Def % | **Δ (Def − Att)** |
|---|---:|---:|---:|---:|---:|
| Dark Host | 15 | 26.7% | 25 | 48.0% | **+21.3%** |
| Dark Operations | 16 | 25.0% | 14 | 42.9% | **+17.9%** |
| Brineblood Marauders | 31 | 41.9% | 44 | 54.5% | **+12.6%** |
| Storm Legion | 29 | 34.5% | 16 | 43.8% | +9.3% |
| Exalted | 22 | 59.1% | 8 | 62.5% | +3.4% |
| Winter Korps | 31 | 45.2% | 54 | 48.1% | +3.0% |
| House Kallyss | 66 | 50.0% | 69 | 49.3% | −0.7% |
| Sea Raiders | 42 | **71.4%** | 42 | **64.3%** | −7.1% |
| Grymkin | 22 | **86.4%** | 12 | 75.0% | −11.4% |
| Infernals | 23 | 52.2% | 21 | 38.1% | −14.1% |
| Shadowflame Shard | 38 | 63.2% | 27 | 40.7% | **−22.4%** |

**This is the signal that was asked for, and it exists.** *"Bokur is the player whose army is
more dependent on the terrain… whenever he goes, I want him picking the table himself."*
That belief is measurable, per army, from public data — a 43-point spread separates
Dark Host (+21.3) from Shadowflame Shard (−22.4).

Two immediate consequences:

- **A per-army terrain-dependence prior can be derived from public results**, requiring no new
  data entry. It is exactly the kind of *actionable, non-tie-breaking* signal that was
  requested: not "these are equal", but *"these are equal on the grid — but this one wants the
  table and that one doesn't, so hold the one who needs it for the moment where he gets it."*
- **Absolute faction strength is also large and unmodelled.** Grymkin 86.4% as Attacker and
  Sea Raiders 71.4% are not close to even. The grid rated Sea Raiders a 3.

### Caveats, stated plainly

Sample sizes per cell are 8–69 games; the extremes (Grymkin n=34, Dark Operations n=30) have
wide intervals and no significance test has been run yet. Faction is also confounded with
player skill — good players may prefer certain armies. **Treat this as a located signal
worth measuring properly, not as a finished prior.** The next step is confidence intervals
and a check against a second event.

---

## Data quality notes (for anyone re-running this)

- **15 placeholder games removed.** They appear as 0–0 draws with both players credited a
  draw, in R4 (Germany Fuchs vs The Italian Job) and R5 (Norway Munin vs Canada Goose;
  France Caesar vs Team Poland). Each duplicates a real, played game at the same table with
  consecutive `game_id`s. After removal every round is exactly 80 games.
- **Team scores reconcile perfectly.** All 160 team-match scores equal the counted player
  wins — a full-database integrity check, 0 mismatches.
- **Victory Points do not decide games.** In 68 of 400 decided games (17.0%) the winner had
  *fewer* VP than the loser; Army Points break 69 of those 93 non-VP-decided games. So the
  ratings predict **win/loss**, not margin, and any future margin-based scoring would need a
  different target variable.
- **The `forced` flag remains undecoded.** It fires on 354/415 raw games and is not "not a
  draw" (46 decided games have `forced=0`). Excluded from all analysis above.
- **Two of Irving's 25 games are unjoined** — "Mussels with muscles" (results) vs
  "Brussels from Mussels" (ratings), plus three other teams with UTF-8 mismatches
  (Germany Eichhörnchen, Sweden Asgård, Sweden Utgård). 28 of 32 teams join exactly.
- **Opponents are keyed by faction/caster loadout**, not player name, in the rating database
  (e.g. `"Sea Raiders - Hor / Sab"`). Faction is the join key to results.

---

## Reproducing this

All scripts live in the session artifact folder
`C:\Users\Daniel.Raven\.copilot\session-state\b5a9a476-5975-467d-b251-0bbfeb2736b6\files\`
(they are deliberately **not** committed — they scrape a third-party site and build a
large local database):

| Script | What it does |
|---|---|
| `ingest_wtc2024.py` | Parses `wtc2024_raw\*.html` into `wtc2024.db` (`games`, `game_players`, `team_games`) |
| `resolve_dupes.py` | Identifies the placeholder games and runs the team-score integrity check |
| `clean_and_schema.py` | Deletes the 15 placeholders; dumps the rating-DB schema |
| `join_ratings_outcomes.py` | Builds the Australia 5×5 grid and the round-5 board |
| `calibrate_ratings.py` | Finding 9 — all 25 Irving games vs their pre-event rating |
| `signal_hunt.py` | Findings 8 and 11 — rating distribution, priority-by-faction |
| `parse_thorny.py` | Findings 13/14 — decodes all 771 cells of the Thorny Devils sheet to an ordinal scale; writes `thorny_ratings.json` |
| `mirror_test.py` | Findings 12/13 — the two-grid correlation and the 120-assignment enumeration |

Findings 12–14 additionally require a **user-supplied, read-only** source that is not in the
repository and is not reproducible from public data:
`C:\dev\QTR_pairing_process\Thorny DEvils WTC matchup sheet.xlsx` — the opposing team's own
preparation grid, sheet `Matchups`, 31 team blocks.

### Caveats on Findings 12–14, stated before anyone over-reads them

- **The correlation is over 25 cells, from one opposing team, at one event.** r = −0.049 is a
  strong refutation of *r = +1.00* — an axiom that strict admits no exceptions — but it is
  not a measurement of "how uncorrelated teams are in general." One more opponent grid would
  do far more for this than any amount of further analysis of this one.
- **The 120-assignment enumeration is exact, not statistical.** "0 of 120 better" and "6 vs 13
  distinct totals" are complete enumerations of a finite space. They carry no sampling error.
  They *do* depend on the scale decoding below.
- **The ordinal decoding is a working hypothesis.** `Red=0, Orange=1, Yellow=2, Green=3`, with
  a parenthetical lean worth ±0.5 toward the named colour. It is inferred from usage, not from
  their instructions sheet. `green(b)` and one `purple yellow` cell remain undecoded and are
  treated as green and yellow respectively. Findings 13 and 14 are robust to this — both
  survive any monotone relabelling — but the exact 13.5 total is not.
- **Per-game outcome accuracy is n=5** and is deliberately not reported as a win rate here.
  Finding 9 covers calibration on the larger 23-game sample.
- **Neither team's grid is "right."** Australia's finer grid steered better *in this round*.
  Their two Green cells that did get played went 1-1 in Irving's favour on one of them
  (Aleks rated Mike `Green - Ekat`; **Mike won 15-9**). Resolution helps you steer; it does
  not make the numbers true.

Raw HTML is preserved in `wtc2024_raw\` (`games_r1..r5.html`, `standings_team.html`,
`standings_player.html`, `stats.html`). The Longshanks AJAX endpoints, which need no
authentication, are:

```
/events/detail/panel_games.php?event=10904&round=N       (N = 1..5)
/events/detail/panel_standings.php?event=10904&section=team|player
/events/detail/panel_stats.php?event=10904
```

Intermittent 403s clear on retry with a `Referer` header of the event page.

---

## Finding 12 — The mirror axiom is false, and it failed on the game that lost the tournament

The most load-bearing assumption in the whole system, stated by the user:

> *"You also have to assume that the opponent would be writing numbers that are flipped
> around the midpoint from yours. If you're correct, and you think its a 5, then the opponent
> MUST also think that's a 1 for them."*

The app encodes this literally as `6 − r` (`ui_manager_v2.py:8219-8226`), and the whole
conservation framework in `SCORING_MATHEMATICS.md` §3.4 rests on it.

**We now have both teams' grids for the same 25 cells.** Correlation between Team Irving's
view and the Thorny Devils' view, after normalising both to "good for Irving":

```
r = -0.049
```

The mirror axiom predicts **r = +1.00**. Zero means the two teams saw **completely unrelated
boards**. Mean absolute disagreement was 0.253 on a 0–1 scale — a quarter of the entire range.

### The cell that decided the tournament

| Matchup | Irving said | Australia said | Actual |
|---|---|---|---|
| **Steve vs Robin (Sea Raiders)** | **3 — dead even** | **`Green horruskh` — "I want this"** | **Robin won 8-2** |
| Rick vs Nads (House Kallyss) | 3 — dead even | `Green Hellyth` — "I want this" | Nads won 8-5 |
| Mike vs Nads | 3 — dead even | `Green SCy` — "I want this" | *(not played)* |
| Jake vs Aleks (Winter Korps) | **1 — disaster for us** | `Orange - Ekat` — **bad for them too** | *(not played)* |

The largest single disagreement, `Jake vs Aleks`, is the most instructive: **both teams
believed they would lose it.** That is not a mirror, in either direction. It is two
independent estimates that happen to be mutually pessimistic — and it is the exact cell
Australia was steering *away* from.

### What this does and does not overturn

Be precise, because two different claims wear the same clothes:

- **Objective zero-sum is still true.** If the true win probability is 0.7 for you, it is 0.3
  for them. Tautology. Untouched.
- **Subjective mirror is false.** *Their estimate* is not the reflection of *your estimate*.
  That is the version the app implements, and it is what r = −0.049 refutes.

`test_zero_sum_conservation.py` uses the objective reading as an idealisation to test whether
a propagation rule is *symmetric*. That remains valid — it is a test of the rule, not of the
world. But the *interpretation* attached to it in §3.4 — that a conserving rule is therefore
unbiased in play — is now weaker than stated: a rule can be perfectly symmetric with respect
to a mirrored opponent and still be wrong, because the real opponent is not mirrored. **The
opponent's independent estimate is an unmodelled source of variance, and it is large.**

---

## Finding 13 — The bus was not chaos. It was a solved assignment problem.

> *"Those madmen just threw out reason and 'bussed' a player to line up a bunch of other
> favorable matchups."*

They did not throw out reason. Scoring the round-5 board against **Australia's own grid**,
across all 120 possible player assignments:

| | Score (their scale, higher = better for them) |
|---|---:|
| Worst possible assignment | 7.0 |
| Mean over all 120 | 9.7 |
| **What they achieved** | **13.5** |
| **Best possible assignment** | **13.5** |

**Zero of 120 assignments were better than the one they got.** They found the global optimum.
Of the 5 "Green — I will win this for my team" cells available anywhere in the 5×5, they
converted **3**: Nads onto Rick, Robin onto Steve, Aleks onto Mike.

That is what the "bus" actually was. Not a player thrown away — a maximiser run to
completion on a grid Irving could not see.

### And Irving's grid said the board was fine

Scoring the *same* board with Irving's grid:

| | Score (Irving's scale) |
|---|---:|
| Worst possible | 10.0 |
| Mean over all 120 | 13.4 |
| **What actually happened** | **14.0** |
| Best possible | 15.0 |

**Irving's own numbers rated the losing board as slightly above average — 14 out of a
possible 15.** The grid did not merely fail to warn. It gave reassurance about the worst
board on the table.

### Resolution: 6 outcomes versus 13

Across all 120 assignments, Irving's grid produced **6 distinct total scores**. Australia's
produced **13**. Australia's board had **2.2× the resolution** — more than twice as many
distinguishable futures to steer between.

That is the mechanism, stated plainly: **the team with the finer grid could see more distinct
boards, and therefore could steer.** The team with the flatter grid saw 120 assignments
collapse into 6 buckets and had nothing to steer with.

---

## Finding 14 — Australia's "3-colour" system was really a 7-level system

The Thorny Devils used green / yellow / red — the stoplight system, chosen because it is
easier to fill in at a glance. Their actual sheet, 771 decoded cells across 31 opponent teams:

| Level | Cells | Share |
|---|---:|---:|
| Red | 6 | 0.8% |
| Red → Orange | 2 | 0.3% |
| Orange | 122 | 15.8% |
| Orange → Yellow | 41 | 5.3% |
| Yellow | 370 | 48.0% |
| Yellow → Green | 54 | 7.0% |
| Green | 176 | 22.8% |
| **Distinct levels used** | **7** | |

They introduced **orange** — a fourth colour that is not in the stoplight system at all —
and then annotated **50.1% of all cells** with a parenthetical lean: `yellow(g)`,
`orange(Y)`, `yellow(o)`, `green(b)`. Half of every entry they made needed a modifier the
system did not provide.

> **This is the granularity argument, proven from the opposing team's worksheet.** A
> three-level scale was not sufficient to express what they knew, so they spontaneously
> invented half-steps until they had seven. The claim that "3 is easier for a human at a
> glance" is true and irrelevant: they did not use 3. Nobody does.

Two further columns exist in their sheet that this app does not model at all:

- **Caster choice per matchup.** Every cell records not just how good the matchup is but
  *which list they would bring* — `yellow(g) - hellyth` versus `green - scy`. The matchup
  rating and the list decision are entangled, and here they are stored together.
- **Explicit terrain flags.** Three cells carry `*Table` / `Sabbreth table` annotations,
  marking matchups whose evaluation is conditional on terrain — the same signal
  independently measured in **Finding 11**, here written down by hand by the opposing team.

---

## Finding 15 — The decision worth agonising over is not the opening

Every version of this app has put its best analysis on the **opening**: which
player to lead with. That is the screen the desktop app sorts, and it is the
question "smart sort" was built to answer.

On real data it is the flattest decision in the round.

`playerLeverage` answers the question asked for most often here — *hold Pete or
hold Bokur* — by searching the rest of the round twice per player, once
committing them and once refusing to, and reporting the difference. Measuring
the **spread** across our five players says whether that panel is telling the
user anything at all. A spread of zero means every player is worth the same to
hold, and the panel is confidently reporting noise.

Measured across all 31 WTC 2024 boards:

| Our decision | Boards where players separate | Mean spread | Median | Max |
|---|---|---|---|---|
| **Opening** (depth 0) | 15/31 — **48%** | 0.58 | **0.00** | 2.00 |
| **Second decision** (depth 1) | 26/31 — **84%** | **1.77** | **2.00** | 4.00 |

On the typical board, *who you hold at the opening does not matter* — the median
spread is literally zero. One decision later, the median is **2 points on a ~17
point total**, and the mean triples.

This corroborates the choice-versus-response decomposition, which found our
opening choice worth nothing on 16/31 boards. Same boards, same story, reached
from a different direction: **the opening is low-information, and the decision
immediately after their reply is where the round is actually won.**

What it changes:

- The app has been putting its heaviest analysis on its weakest decision.
- "Which opener?" deserves a small answer. "Now that they have replied, who do
  you spend and who do you keep?" deserves the screen.
- It gives a concrete answer to *"it is not clear when those decision points
  happen"*: they happen at your **second** decision, and on 84% of boards there
  is a real, measurable difference between holding one player and another.

Structural note: depths 0 and 1 are the only decisions we own. Verified, not
assumed — all 31 walks complete the full 5 pairings (`stopped by complete
31/31`). The remaining decisions are theirs or forced.

### A measurement error worth recording

The first version of this walk reported **only depth 0** and I nearly wrote it
up as "leverage does not deepen." It was wrong. `currentDecision` never returns
a `pick` — the offered pair lives in component state, not in `LiveState` — so
the walk hit the first offer, failed to match any branch, and silently stopped
one decision in. The "no deeper signal" reading was an artifact of my own walker
giving up, not a property of the game.

The fix was to resolve offers in two steps (the offering side proposes, the
attacking side takes the half that suits it) and, more importantly, to make the
walker **report why it stopped** and how many pairings it completed. The finding
above is only trustworthy because that instrumentation says `complete 31/31`.

Reproduce:

```bash
cd webapp
QTR_MEASURE=1 npx vitest run src/engine/measure.leverage.test.ts \
  --reporter=verbose --disable-console-intercept
```

---

## Finding 16 — Our "worst-case bound" *is* the mirror axiom, and it costs 1.4 points of pessimism

`protocol.ts:27-40` defends the webapp's opponent model as a bound rather than a
belief:

> *"The opponent here minimises OUR total on OUR OWN numbers. That is not a claim
> about their preferences; it is a bound ... `protocolFloor` is a guarantee that
> survives not knowing their grid at all."*

That defence is sound for the number. It is **not** sound for the advice built on
it, and the reason is one line of algebra:

```
a side maximising  O = 1 - M   maximises  sum(1 - M)
                               which is   minimising sum(M)
```

"The opponent minimises our total" and "the opponent's grid is our grid mirrored"
are **the same opponent**. The worst-case model and the mirror axiom that
Finding 12 refuted (r = −0.049 between two real teams' grids) are one model in two
sets of clothes.

This is not an argument — it is asserted as a CI test. `measure.opponent.test.ts`
plays a two-grid general-sum solver with their grid set to `1 − M` and checks it
reproduces single-grid minimax on **all 31 boards × all 5 openings, to 9 decimal
places**. It does. That test is not measurement-gated; it runs on every push.

### What the assumption actually costs

The null model Finding 12 supports: their grid is drawn *independently* of ours
from the same marginal distribution of real ratings. We then play the real
protocol as a general-sum game — we maximise our grid, they maximise theirs.

200 trials per board, 31 boards, repeated across 4 seeds:

| Quantity | Value | Stable across seeds? |
|---|---|---|
| Regret from following the floor ranking | **0.07 pts** | Yes — 0.069–0.074 |
| Floor understates realised score by | **1.40 pts** | Yes — 1.396–1.403 |
| Max understatement on a single board | **~2.5 pts** | Yes |
| "App picked the best opening" agreement | 29–39% | **No — do not quote** |

Two conclusions, and they pull in opposite directions:

- **The advice is safe.** Following the floor ranking costs **0.07 points**. The
  mirror axiom is theoretically refuted and practically almost harmless *for
  ranking*. Nothing needs to be ripped out.
- **The displayed number is not.** The floor runs **1.40 points pessimistic**
  against an opponent optimising their own board. The app shows 14 where 15.4 is
  the realistic expectation.

That gap is exactly the distinction asked for at the table — *"must win versus
must not lose."* The floor is the must-not-lose number. It has never been
labelled as one, and the must-win number has never been shown at all.

### The number I nearly published

The first run said the app picks a different opening from the trial-best on
**19 of 31 boards**, and the obvious headline was *"the recommendation is wrong
61% of the time."* Re-running under three more seeds moved agreement to 29%, 35%,
29% — the identity of the "best" opening is **not identifiable**, because the
openings are too close to separate at 200 trials. Regret and floor error did not
move at all.

The alarming number was the unstable one. This is the same lesson as Finding 15's
walker bug from the other direction: the harness now prints `SEED-UNSTABLE, do not
quote` next to it, and re-checking with `QTR_SEED` is a precondition for quoting
anything from this file.

It also independently corroborates Finding 15 — if the opening mattered, the best
opening would be identifiable. It isn't.

Reproduce:

```bash
cd webapp
QTR_MEASURE=1 npx vitest run src/engine/measure.opponent.test.ts \
  --reporter=verbose --disable-console-intercept
QTR_SEED=2 QTR_MEASURE=1 npx vitest run src/engine/measure.opponent.test.ts \
  --reporter=verbose --disable-console-intercept
```

---

## What this changes — revised

| Question originally asked | What the ground truth says |
|---|---|
| *Can the math be faster?* | Yes — the scenario axis is provably constant on all real data (**Finding 7**). Collapsing it is a 7× reduction with identical output. |
| *Can the analysis be more purposeful?* | Not from a flat grid. 74% of it is one number (**Finding 8**), and it rated the losing board 14/15 (**Finding 13**). |
| *Can we beat "smart sort"?* | Better ranking of a low-resolution matrix is not the win. **Resolution itself** is the win (**Findings 13, 14**), plus signals the grid does not contain (**Finding 11**). |
| *How do we avoid being bussed?* | **Stop modelling them as your mirror** (**Finding 12**). Assume an opponent who *maximises on a grid you cannot see* (**Finding 13**), and score your openings by how bad their best reply can be — not by your own optimistic total. |
| *Where should the analysis point?* | **Not at the opening.** Who you hold at the opening is worth nothing on the median board; one decision later it is worth 2 points (**Finding 15**). The heaviest analysis has been sitting on the weakest decision. |
| *Is the current advice actually wrong?* | **No — the ranking is safe** (0.07 pts of regret), but the number beside it is **1.4 pts pessimistic** and unlabelled (**Finding 16**). The fix is presentation — show the floor *as* a floor, and show the expected value next to it. |

---
