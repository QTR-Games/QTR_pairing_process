# The Mathematics of WTC 5v5 Pairing — 2026 Follow-Up

*A supplement to `docs/WHITEPAPER.md`. It records what the 2026 evidence confirms,
what it moves, and what it adds — in particular the first direct observation of an
**opponent's own matchup judgements**, which the 2024 paper identified as lying
beyond its data.*

---

## Abstract

The 2024 whitepaper derived the WTC 5v5 pairing process as a finite, deterministic,
perfect-information, zero-sum sequential game, validated the model against 400 real
games, and closed with a set of explicitly-flagged research gaps. Two of those gaps
were marked *beyond current data*: fitting the opponent-rationality parameter
$\lambda$, and recovering anything at all about an opponent's true grid.

The 2026 cycle supplies evidence against both, from a source the earlier work did
not anticipate: **a rival pairing tool's own navigation logs**, captured for all
five rounds of one team's event, in which every nomination, selection and forced
pairing is recorded *together with that tool's verdict on the decision*. This is not
a better estimate of an opponent's grid. It is a different and stronger object — a
**labelled record of how a competing engine values matchups, and of how a human
captain diverged from it**.

Four results anchor this supplement. First, the **bus** mechanism of §12.3, derived
in 2024 from the rules, is confirmed mechanically on 20 real nominations with zero
exceptions. Second, the per-round nomination structure is **more constrained than
the 2024 enumeration assumed**: the roster is necessarily carved $2{+}2{+}1$, so the
free parameter is *which* partition, not whether to partition. Third, the rival
engine's objective is recovered exactly — and it is a **lexicographic dodge-avoidance
proxy, not the round win condition**, which is a concrete and reproducible design
critique rather than a matter of taste. Fourth, the 2024 terrain finding (§11
Finding 11, §12.6) is **not withdrawn but is now known to be confounded**: the
Attacker/Defender flag cannot distinguish terrain choice from turn order, and a
direct 2026 turn-order measurement is small and at best marginal.

This document **supplements and does not supersede** `docs/WHITEPAPER.md`. Where the
two disagree, the disagreement is stated here explicitly and the original text is
left standing, so the record shows what was believed, on what evidence, and why it
moved.

---

## 0. How to read this alongside the 2024 paper

The 2024 paper remains the reference for the model, the proofs, and the engine. Its
section numbering is unchanged and is cited here as *§N (2024)*. Nothing in it has
been edited as a result of this work.

This supplement is organised by **what happened to each prior claim**:

| disposition | meaning |
|---|---|
| **Holds** | re-examined against 2026 evidence and unchanged |
| **Confirmed** | previously *derived*; now also *observed* |
| **Confounded** | not refuted, but a rival explanation is now known and untested |
| **New** | no counterpart in the 2024 paper |

---

## 1. Provenance — what is verified here and what is reported

The 2024 paper could treat its inputs as a single audited dataset. This one cannot:
the evidence arrives from two independent efforts, and the distinction matters for
every number below. It is therefore stated up front rather than in a footnote.

**Verified directly in this repository.** The five rival navigation logs, read from
screenshots by two independent OCR passes and cross-checked line by line; the
arithmetic reconciliation of all five rounds; the 25-cell label grid of §5.2; the
catalogue comparison of §8; and the leader-collision enumeration of §8.1. These can
be re-derived from artefacts held in this project.

**Reported by the sibling analysis effort and *not* independently verified here.**
The 600-game WTC 2026 corpus and its 120/120 fixture reconciliation; the
Bradley-Terry strength fit; the turn-order rate of §4.2; the badge-stability count of
§8.2; and the six-team nomination table of §6.3. These are credited inline and
marked **[reported]**. They are used because they bear on questions our own data
cannot reach, but a claim resting on them is weaker than one resting on the logs.

**A dependency worth naming.** The five logs exist only as screenshots. Both OCR
passes agree on every player name, nomination and verdict used here, and all five
rounds reconcile arithmetically under a single recovered utility (§5.1) — which is a
strong internal check, since an OCR error in any label would almost certainly break
the reconciliation. The passes do **not** agree on the engine's running spread
strings, where `1G`/`IG` and `0S`/`OS` confusions are frequent. **Every spread figure
in this document is re-derived from the labels, never parsed from those strings.**

---

## 2. What holds unchanged

Re-examined against the 2026 material and carried forward without amendment:

- **The win threshold.** $\tau = G(lo+hi)/2$ is a consequence of the zero-sum
  property (§3, 2024) and is untouched by anything here.
- **The mirror axiom is false** (§12.5, 2024). The 2026 evidence *strengthens* this:
  the rival engine's recovered utility (§5.1) is not the negation of any grid we
  hold, and its ordering diverges from a strength-based ordering (§6.4).
- **Matchup control weakly dominates table control** (§12.1, 2024). Nothing in the
  2026 logs bears on it; it stands on its 2024 measurement.
- **The assignment view overstates the guarantee** (§12.3, 2024). This is now
  reinforced — see §3.1.
- **Scale compression cuts both ways** (§12.4, 2024). The rival engine exhibits a
  severe instance of it in its own right (§5.3).

---

## 3. Confirmed: derived in 2024, observed in 2026

### 3.1 The bus is real, and it is not a pool

§12.3 (2024) derived the *bus*: the declined half of an offer becomes the next
attacker, so sequencing is itself a resource. The logs confirm the mechanism and
settle a question the derivation left implicitly open — **whether an unselected
nominee returns to a general pool**. It does not. The unselected player is carried
directly into the following pairing.

The test is clean. Across five rounds, both sides, there are **20 nominations
comprising 40 player-slots, and no player is ever nominated twice**. A replenishing
pool would produce repeats; a bus cannot. One apparent counterexample — a repeated
name in the Australia log — is the engine printing a *counterfactual*
("Engine preferred: …"), not a nomination that occurred.

This has a consequence the 2024 paper did not draw out, and §6.1 develops it.

### 3.2 The protocol shape

Each round's log runs **eight numbered decision steps and a forced final pairing**:
four pairings resolved by a nominate-then-select exchange, and a fifth that is
arithmetically determined once the other four are locked. This matches the structure
§10 (2024) implements, and the hand enumeration of the decision tree performed
earlier in this cycle, which terminates at **14,400 leaves**.

That figure is *not* asserted as a test here, and should not enter published copy
without one — see §9.

---

## 4. Confounded: the terrain axis

### 4.1 What the 2024 finding actually measured

Finding 11 (`WTC2024_GROUND_TRUTH.md`) and §12.6 (2024) report a per-army
terrain-dependence signal: Longshanks' Attacker/Defender priority is a global coin
flip (51% / 49% over 398 games each way) but splits by faction into effects of
opposite sign spanning **43 points**, from Dark Host $+21.3\%$ to Shadowflame Shard
$-22.4\%$.

The original text already carried the right caveats — 8–69 games per cell, no
significance test, faction confounded with player skill — and explicitly labelled it
*"a located signal worth measuring properly, not a finished prior."* **That framing
is correct and is not withdrawn.**

What is new is a *specific* rival explanation. Under the Player Pack the winner of
the roll-off chooses **either** table side **or** turn order. The Attacker/Defender
flag records the table/terrain axis; it does **not** record which option the winner
actually took. A per-army effect on that flag can therefore reflect terrain
dependence, a turn-order preference correlated with army, or the selection rule by
which certain armies more often win or decline the choice. The 2024 data cannot
separate these.

### 4.2 The direct turn-order measurement **[reported]**

WTC 2026 records turn order explicitly, which 2024 did not. On 587 games where it is
recorded, **the first player won 269, a rate of 45.8%**, with a fitted term
$\beta = -0.141$ and a two-sided binomial $p \approx 0.043$.

Two cautions, both agreed by the analyst who produced it. The test was **not
pre-specified**, which weakens $p$ considerably. And at this effect size the correct
reading is **"no detectable first-player advantage, with a possible small
disadvantage"** — not "going first is a disadvantage."

### 4.3 Disposition

> **Research gap — the terrain prior is located, confounded, and still not built.**
> This research has not been performed. Finding 11's per-faction effects remain
> unreplicated, and the variable they rest on cannot distinguish terrain from turn
> order. Based on other aspects of the current work, the standing hypothesis for how
> this factors into the WTC Pairing Process is: **a per-army terrain-dependence
> effect exists but is smaller than the 43-point spread suggests, because that
> spread aggregates at least two mechanisms and is unadjusted for player skill; a
> correctly-specified measurement — per army, conditioning on which option the
> roll-off winner took, with intervals, on a second event — will retain the sign
> ordering for the extreme armies and shrink the magnitudes substantially.** Until
> that exists, §12.6's practical advice is unchanged and remains the honest move:
> state *who holds each table pick*, which follows from the rules with no data
> entry, and leave the judgement to the player at the table.

---

## 5. New: an opponent's observed valuations

§13 (2024) closed with: *"any future improvement must come from **their** observed
choices, not from **our** numbers."* The logs are exactly that.

### 5.1 The rival objective, recovered exactly

The rival tool labels every locked pairing `GOOD`, `EVEN` or `SOFT DODGE` from its
user's perspective, and prints a round value. Solving for the three unknowns across
five rounds gives a single consistent assignment:

$$\text{GOOD} = +1, \qquad \text{EVEN} = 0, \qquad \text{SOFT DODGE} = -10$$

It reconciles every round with **zero residual**:

| round | opponent | labels | value |
|---|---|---|---:|
| 1 | Finland Sarvikellopöllö | 2 GOOD, 2 EVEN, 1 SOFT | $-8$ |
| 2 | South Africa Abelungu | 1 GOOD, 4 EVEN, 0 SOFT | $+1$ |
| 3 | England Lancelot | 0 GOOD, 4 EVEN, 1 SOFT | $-10$ |
| 4 | Canada Moose | 2 GOOD, 3 EVEN, 0 SOFT | $+2$ |
| 5 | Australia Salty Crocs | 2 GOOD, 1 EVEN, 2 SOFT | $-18$ |

Five equations, three unknowns, exact fit. This is the strongest identification in
the document and it rests only on the logs.

### 5.2 The 25-cell judgement grid

Every locked pairing carries a label, so one team's five rounds yield a complete
labelled grid — a captain's matchup judgement, written down rather than inferred:

| player | R1 FIN | R2 RSA | R3 ENG | R4 CAN | R5 AUS | mean | sd |
|---|---|---|---|---|---|---:|---:|
| Eikermann | GOOD | EVEN | EVEN | EVEN | GOOD | $+0.4$ | $0.49$ |
| McGeehan | GOOD | EVEN | SOFT | GOOD | GOOD | $-1.4$ | $4.43$ |
| Kosma | EVEN | GOOD | EVEN | GOOD | SOFT | $-1.6$ | $4.22$ |
| Du | EVEN | EVEN | EVEN | EVEN | SOFT | $-2.0$ | $4.00$ |
| Sennstrom | SOFT | EVEN | EVEN | EVEN | EVEN | $-2.0$ | $4.00$ |

### 5.3 Why a $-10$ matters: the proxy is not the win condition

A round is won by taking **3 of 5 games**. The recovered utility is a weighted sum in
which one `SOFT DODGE` outweighs ten `GOOD`s — effectively a lexicographic rule,
*eliminate soft dodges first, maximise good matchups second*.

These are different objectives, and they disagree on real boards. A line yielding
`4 GOOD, 0 EVEN, 1 SOFT` scores $-6$ and is ranked below `0 GOOD, 5 EVEN, 0 SOFT` at
$0$, despite the former winning four games outright. Avoiding catastrophe is a
defensible human heuristic, but it is **not** $P(\ge 3)$, and a model trained or
tuned against the scalar will inherit the inversion.

This is the same failure mode as §12.4 (2024) — a unitless score standing in for a
probability — observed independently in another tool. It generalises the 2024 claim
from a property of our scale to a property of the design pattern.

> **Research gap — $\lambda$ is now fittable but not fitted.** §13 (2024) listed
> fitting $\lambda$ as "within reach of existing tooling" but lacked observed
> opponent decisions. Twenty labelled decisions with the engine's own
> optimal/suboptimal verdict now exist. The obvious estimator — treat the 19/20
> agreement rate as a quantal-response likelihood — is **not** run here, because the
> verdicts are the *rival engine's* judgement, so "suboptimal" conflates captain
> error with disagreement between two models. Based on other aspects of the current
> work, the standing hypothesis is: **a $\lambda$ fitted against another engine's
> verdicts will be biased high — it will overstate opponent rationality, because it
> scores agreement with a specific model rather than with the win condition — and
> the honest use of this corpus is to fit $\lambda$ against *outcomes* while using
> the verdicts only to bound how often captains deviate from any explicit model at
> all.**

---

## 6. New: nomination structure, and what it does to the tree

### 6.1 The $2{+}2{+}1$ carve is forced

A direct consequence of §3.1. Each nomination removes **two** players from the
nominating side — one locked into the current pairing, one carried onto the bus —
so a five-player roster is necessarily consumed as $2 + 2 + 1$.

This corrects an over-reading made earlier in this cycle. "The team nominates intact
pairs" is **not** a behavioural observation; within a single round it is an identity.
What remains free, and genuinely informative, is **which** partition — and there are
exactly $15$ distinct $2{+}2{+}1$ partitions of five players.

### 6.2 One team held one partition across five rounds

USA Death Valley nominated the partition
$\{\text{Eikermann},\ \text{Kosma}\} \mid \{\text{McGeehan},\ \text{Sennstrom}\} \mid \{\text{Du}\}$
in **5 of 5 rounds**, against five different opponents, while varying *which block
went first* 3–2. Fixed partition, adaptive sequencing.

The sharpest single observation in the corpus is the one place they diverged from
their own tool. In Round 5 the engine preferred the nomination
$\{\text{Kosma},\ \text{McGeehan}\}$ — a pair that **crosses the partition** — and the
captain declined, taking the only `Suboptimal` verdict in 20 decisions. A pure
re-optimiser follows the engine; a pre-committed team does not.

**Stated with its weaknesses, because they are severe.** This is $n=1$ team and, for
the divergence, $n=1$ decision. "Suboptimal" is the rival engine's judgement, so the
captain may have disagreed with its model (§5.3 gives him reason to) rather than
obeyed a policy. A naive null — "a team redraws a partition uniformly each round" —
yields $(1/15)^4 \approx 2\times10^{-5}$, and that figure was **retired during this
cycle as a strawman**: nobody believes teams randomise, and the live alternative is
re-derivation from a stable roster, which predicts invariance just as strongly.

### 6.3 Two structural explanations tested and rejected

Both were proposed as mechanisms that would make the invariance a by-product of
roster composition rather than policy. Both fail.

**The same-faction hedge.** Nominating two players of one faction makes the
opponent's selection faction-neutral. USA's blocked pair are both Dusk, so the
hypothesis fits them — but it predicts the behaviour should be *general*. Across the
six teams in these logs, four had a same-faction pair available and **one took it**;
against a chance baseline of $3/15$ per available pair, expected blockings are
$0.93$ against $1$ observed **[reported]**. That is precisely coincidence. All ten
opponent blocks are mixed-faction.

**Variance minimisation.** The rule *"put your flattest player where you cannot
protect him"* would explain the singleton seat without pre-commitment. The grid of
§5.2 refutes it on its own terms: **Eikermann is the flattest player on both
dispersion and mean, and is the only one of the five who never took a `SOFT DODGE`**
— yet he was blocked, and the median player took the singleton seat.

The seat detail is decisive. Du's singleton was *unprotected* exactly once (Round 4,
where USA was Team A and he fell to the forced final game); he scored `EVEN` there.
His only `SOFT DODGE` came in a round where USA **chose his opponent from two**. A
variance rule predicts the reverse.

**The honest caveat**, which runs toward the rejected hypothesis rather than away
from it: these labels are realised outcomes of matchups the process selected, so they
are endogenous, and an unprotected seat should inflate observed spread. The
hypothesis fails despite that bias. Sennstrom — blocked and protected in all five
rounds — carries exactly Du's profile, which undercuts any clean correction.

### 6.4 Disposition

> **Research gap — partition invariance is observed at $n=1$ team.** Based on other
> aspects of the current work, the standing hypothesis for how this factors into the
> WTC Pairing Process is: **a minority of teams arrive with a pre-committed
> partition and hold it under engine pressure, which if true collapses the
> nomination nodes of the 14,400-leaf tree toward a far smaller identifiable set and
> makes *partition identity* a more valuable scouting target than any individual
> matchup rating; the test is cross-round partition invariance measured across many
> teams, which requires nomination-level logs that public results do not contain.**
> Final results alone cannot settle it — they record the matchups, not the carve.

---

## 7. New: the two singleton seats are not one seat

The singleton is structurally different depending on side, which the 2024 paper did
not separate:

- **As Team B** the singleton is **proffered first**. The opponent nominates two, and
  **our side selects** — the best-informed pick available.
- **As Team A** the singleton falls to the **forced final pairing**, with no choice at
  all on either side.

In this corpus USA proffered Du in four rounds and had him forced in one. Holding one
player in a seat whose value inverts with side is a stronger regularity than holding
a partition, and in Round 4 it cost two free nominations — from 10 available pairs,
then 3 — to arrange. It is also, on these logs, $n=1$ inversion.

---

## 8. New: identity resolution in the data layer

Not pairing mathematics, but it determines whether a corpus can be joined at all, and
it produced a live fix in this repository.

### 8.1 Faction cannot be inferred from a leader's name

A sibling import flagged 25 players carrying two different faction labels across one
event, initially read as data corruption. Enumerating every leader name appearing
under more than one faction in our catalogue produces **exactly four**, and they
account for the anomalies one-for-one:

| collision | factions | mechanism |
|---|---|---|
| Butcher | Khador *5th Division* / Orgoth *Sea Raiders* | one character, two factions |
| Khythos | Cryx *Necrofactorium* / Mercenaries *Dark Operations* | shared leader |
| Rahera | Cryx *Blackfleet* / Mercenaries *Talion Charter* | shared leader |
| Gunnbjorn | Southern Kriels *Kithguard* / Trollbloods *United Kriels* | shared leader |

A fifth anomaly is a different mechanism — `Reznik` is a **prefix** of `Reznikova`,
so an unanchored substring match silently rewrites one caster as another. Three
further prefix hazards are latent in the catalogue: `Iona` ⊂ `Fiona`,
`Grim` ⊂ `Grimtusk`, and `Lylyth` ⊂ `Lylyth 1`/`Lylyth 3`.

**The rule that follows: never infer faction from leader.** The badge names the army
or its parent faction and is stable; the leader is then searched *within that scope*,
so an ambiguous name never has to be resolved globally. This is what
`webapp/src/longshanks/factions.ts` already does, together with left-anchored
matching, prefix-shadow dropping, and card-title disambiguation for reprints sharing
an army. **[reported]**: the scoping key was independently measured as invariant —
**0 of 288 players changed army badge across five rounds**, while the leader-derived
faction flipped on exactly the rounds the shared-name caster was fielded.

Two caveats worth preserving. **Southern Kriels and Trollbloods are distinct
factions**, each with their own armies, and must not be merged as synonyms despite
sharing Gunnbjorn. And Longshanks' `Unlimited` is a catch-all whose "leaders" are
faction names rather than models; it is excluded from leader work deliberately.

### 8.2 Two armies were renamed, not added

Two badge titles — `Wicked Harvest` and `Clockwork Legions` — appear in WTC 2026 and
are absent from both catalogues, which broke leader inference for the players
carrying them. Before this event there are no game rows to read a leader from, so an
unrecognised army leaves the only available route blocked.

Transcribing the casters observed at one event would have baked in a partial roster.
The subset test shows it is unnecessary:

| new title | casters observed | already in our catalogue | novel |
|---|---:|---:|---:|
| Wicked Harvest | 5 | 5 (Grymkin) | **0** |
| Clockwork Legions | 4 | 4 (Convergence of Cyriss) | **0** |

Nine of nine, with no unrecognised caster. These are **renames of existing armies**,
so the names are now aliased onto the existing entries — which inherits the complete
roster, including casters nobody fielded in 2026, and invents nothing. The fix and
its regression tests ship with this document.

---

## 9. Revised limitations

Carried forward from §13 (2024), amended:

- **$\lambda$ fitting** moves from *beyond current data* to *within reach, with a
  named bias* (§5.3).
- **The opponent's true grid** remains unknowable from our ratings
  ($r \approx -0.049$). What changed is that a *different* object — their engine's
  objective — proved recoverable exactly. The 2024 posture, that bounding beats
  predicting, is unaffected.
- **Partition invariance** is new, and needs nomination-level logs across many teams
  (§6.4).
- **The terrain prior** needs a specification that separates terrain from turn order
  (§4.3).

Two cautions specific to this supplement:

- **The 14,400-leaf figure is hand-derived and untested.** It should not enter
  published copy without a test asserting it, in the manner of
  `webapp/src/engine/adClaims.test.ts`.
- **Single-team, single-event.** Every §6 and §7 result describes one team across
  five rounds. They are offered as located hypotheses with explicit nulls, not as
  findings.

---

## 10. Summary of 2026 results

| result | disposition | evidence |
|---|---|---|
| $\tau = G(lo+hi)/2$ | holds | proof, §3 (2024) |
| Mirror axiom is false | holds, strengthened | $r=-0.049$; rival utility is not our negation |
| Matchup control dominates table control | holds | 2024 measurement only |
| The bus: declined half becomes next attacker | **confirmed** | 20 nominations, 0 repeats |
| Unselected nominee returns to a pool | **refuted** | same test |
| 8 decision steps + forced final | confirmed | 5 logs |
| Terrain axis, 43-point per-army spread | **confounded** | A/D flag cannot separate turn order |
| First-player advantage | no detectable effect | 269/587 = 45.8%, $p\approx0.043$, not pre-specified **[reported]** |
| Rival utility GOOD $+1$ / EVEN $0$ / SOFT $-10$ | **new, exact** | 5 rounds, 3 unknowns, zero residual |
| Rival objective $\ne$ $P(\ge 3)$ | **new** | inversion exhibited, §5.3 |
| Roster is carved $2{+}2{+}1$ | **new, forced** | follows from the bus |
| "Nominates intact pairs" is informative | **withdrawn** | identity within a round |
| One partition held across 5 rounds | **new**, $n=1$ team | 5/5, one engine divergence |
| $(1/15)^4$ null for partition invariance | **retired** | strawman; re-derivation predicts it equally |
| Same-faction hedge explains the partition | **rejected** | expected 0.93 vs observed 1 **[reported]** |
| Variance minimisation explains the singleton | **rejected** | flattest player was blocked, not seated |
| Faction inferable from leader name | **refuted** | 4 cross-faction collisions enumerated |
| `Wicked Harvest` / `Clockwork Legions` are new armies | **refuted** | 9/9 casters already catalogued; renames |

---

## Sources

- `docs/WHITEPAPER.md` — the 2024 paper. Supplemented, not superseded.
- `docs/WTC2024_GROUND_TRUTH.md` — Findings 7–22, including Finding 11 (§4 here).
- `webapp/src/longshanks/factions.ts` — catalogue, resolution rules, and the §8.2 fix.
- `webapp/src/engine/protocol.ts` — the protocol engine whose shape §3.2 confirms.
- Five Pear Master navigation logs, USA Death Valley, WTC 2026 rounds 1–5, held as
  OCR transcripts outside the repository (§1).
- Rules references are to Warmachine Player Pack 2026 v1.1, p.20.
