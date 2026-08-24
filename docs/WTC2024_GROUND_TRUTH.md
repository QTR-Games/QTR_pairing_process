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

## What this changes

| Question originally asked | What the ground truth says |
|---|---|
| *Can the math be faster?* | Yes — the scenario axis is provably constant on all real data (**Finding 7**). Collapsing it is a 7× reduction with identical output. |
| *Can the analysis be more purposeful?* | The grid alone cannot be. 74% of it is one number (**Finding 8**) and the decisive game was rated "even" (**Finding 10**). Purpose has to come from signals the grid does not contain. |
| *Can we beat "smart sort"?* | Better ranking of a flat matrix is not the win. **Finding 11** shows a real, per-army, actionable signal exists in public data and is currently unmodelled. |
| *How do we avoid being bussed?* | Not by out-searching the opponent. By detecting that the grid is too flat to support a recommendation, and saying so, instead of ranking noise. |
