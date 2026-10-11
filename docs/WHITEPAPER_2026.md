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
be re-derived from artefacts held in this project. The catalogue comparison is the
strongest of them: the upstream table it reconciles against is committed as a test
fixture, so that claim is not merely reproducible but re-checked on every test run.

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
| Butcher | Khador *5th Division* / Orgoth *Sea Raiders* | **two different models** sharing a name **[reported]** |
| Gunnbjorn | Southern Kriels *Kithguard* / Trollbloods *United Kriels* | **two different models** sharing a name **[reported]** |
| Rahera | Cryx *Blackfleet* / Mercenaries *Talion Charter* | **one character** fielded in two factions **[reported]** |
| Khythos | Cryx *Necrofactorium* / Mercenaries *Dark Operations* | unruled; name shared across two factions |

The mechanism column is not decoration, and nothing in the catalogue supplies it
— all four rows look identical in the table, and the distinctions above come
from the upstream maintainer rather than from any field. That is the point: the
resolver cannot tell these cases apart either, which is why §8.1's gate refuses
all of them rather than trying to.

A fifth anomaly is a different mechanism — `Reznik` is a **prefix** of `Reznikova`,
so an unanchored substring match silently rewrites one caster as another. Scanning
the catalogue for containments under our *actual* word-anchored matching, rather
than naive substring, finds **exactly two cross-faction prefix hazards**:
`Reznik` ⊂ `Reznikova` and `Grim` ⊂ `Grimtusk` — the latter live in this event.
Apparent hazards like `Iona` ⊂ `Fiona` are artefacts of the naive scan and cannot
fire against a word-anchored matcher.

`Lylyth` is a different matter, and an earlier draft of this section dismissed it
wrongly as an intra-faction printing ambiguity. Legion of Everblight's Ravens of
War carries `Lylyth 1` and `Lylyth 3`; Khymaera's Shadowflame Shard carries a bare
`Lylyth`. The literal strings never match, so the enumeration behind the table
above — which counts repeated names *as written* — cannot see it, and the
collision appears only once Longshanks' reprint numbering is stripped. It is a
**fifth cross-faction collision**, found by hardening the resolver rather than by
reading the table. **The four above are confirmed instances, not a closed
enumeration.**

A sixth was claimed and is **withdrawn**. `Locke` is a suffix of `Athanor Locke`,
which the prefix-shadow rule does not catch, and upstream carries two `Locke`
rows in different factions — which looked like a collision waiting to happen.
It is not one. Athanor Locke is a single character who **moved** from Convergence
of Cyriss to Crucible Guard, so the two rows are her previous and current homes,
and the resolver answering `Locke @ Crucible Guard` is returning the right
answer rather than being saved by luck. **Cross-faction collisions stand at
five**; there was never a sixth.

No *suffix* hazard becomes live if upstream touches those rows either —
resolving `Athanor Locke` to Crucible Guard is correct under any state of 1239,
because it is the same person in both. But that is a narrower statement than
*nothing* changes, and an earlier draft of this paragraph made the wider one.
Carrying both rows at once would put one character in two factions, and §8.1's
gate would then refuse a name it resolves cleanly today. That hazard is
**suppressed by the retired-entry assertion of §9 rather than being absent** —
which is the second, independent reason that assertion earns its place.

That retraction is more useful than the claim would have been, because the
evidence to settle it was present the entire time. A migration and a collision
have different signatures in the table, and the distinction is mechanical:

| signature | meaning | instances |
|---|---|---|
| same code, one retired + one active | one character who changed faction | `locke`, `mortenebra` |
| same code, all rows active | **undetermined** | `butcher`, `gunnbjorn`, `rahera` |

The first clause is reliable: it recovers both migrations in the catalogue,
only those, and without any knowledge of the setting. It is what should have
been consulted before any of the `Locke` claims was written down.

The table is also not a curated selection. Grouping the 204 leader rows by code
and keeping every code that spans more than one faction returns exactly these
five, and the division between the table's two rows is nothing but the `active`
column. The partition is therefore recoverable by query; the rulings confirm it
rather than produce it, which is what makes it a property of the data instead of
a reading imposed on it.

**The second clause is deliberately empty, and an earlier draft of this table
filled it in wrongly.** It read *distinct characters*, which is a complement
rather than a finding — and it is false. Of the three groups, `Butcher` and
`Gunnbjorn` are each two different models, while `Rahera` is **one character
appearing in two factions** **[reported]**, all three looking identical in the
table. A signature that identifies migrations exactly and says nothing about
everything else is the honest form; extending it to a complete partition
repeated, in miniature, the error of §8.2's unfiltered-read mechanism — a rule
fitted to the cases checked and overreaching on the ones that were not.

**`code` is not a usable join key, and it fails as both kinds of key** — but the
evidence for each half is narrower than it first appears, and three of the five
shared-code groups are not evidence of anything wrong.

It fails as a **character** key on `butcher` and `gunnbjorn`. Each is a single
code spanning two confirmed-different models **[reported]**, so a join on code
merges two characters outright. It does *not* fail on `locke` or `mortenebra`,
where one code tracking one character across a faction change is precisely
correct behaviour, nor on `rahera`, where the shared code reflects a genuinely
shared character. Those three are the field working; only the first two are the
field breaking.

It fails as a **printing** key in the more awkward way — inconsistently, rather
than never. Longshanks encodes the reprint number in the code for some
characters and not others, in the same table:

```
1251 Skarre 1  skarre1      1292 Lylyth 1  lylyth1      1235 Aurora 1  aurora1
1252 Skarre 3  skarre3      1293 Lylyth 3  lylyth3      1236 Aurora 2  aurora2

1388 Caine     caine        1996 Caine 4   caine        2215 Caine 4   caine
```

Three characters whose codes distinguish their printings, and one — the one that
produced the Gravediggers defect — whose three rows, two of them different and
simultaneously legal cards, collapse to a single code. A key that follows a
convention most of the time is worse than one that never does, because it reads
as reliable right up to the case that matters. The `(name, army)` pair is what
this table actually supports.

There is a third failure, and this document caught it rather than catalogued it.
`Sparkhammer` leads Storm Legion and Gravediggers off one card, so his two rows
should share a code. They do not, because one carries a trailing space:

```
1347  Sparkhammer  Storm Legion   'sparkhammer '
2216  Sparkhammer  Gravediggers   'sparkhammer'
```

Grouping the 204 leader rows by code gives **14** duplicate groups; grouping by
*trimmed* code gives **15**, and the single group that appears is `sparkhammer`.
So the defect does not merely sit in the table being untidy — it removes a real
shared-leader pair from any census taken on the raw field. The enumeration of
"all 14 duplicate-code groups" earlier in this work was one short for exactly
that reason, and the shortfall went unnoticed because 14 is what the data
answers when the question is put carelessly.

The *direction* is what makes this worth separating from the other two, because
it is the reverse of `caine`'s. `caine` gives two different characters one key;
`sparkhammer` gives one character two keys. A normaliser repairs the second and
is powerless against the first, so a pipeline that trims and then trusts the
result is strictly more confident without being any more correct.

A smaller caution in the same vein: one of the five confirmed collisions avoids a
code clash only through a typo. `Khythos` is `kythos` under Cryx and `khythos`
under Mercenaries, so an analysis keyed on code treats them as distinct — and
would stop doing so the moment someone upstream fixes the spelling.

Khymaera's `Lylyth` is also misspelled, as `lytyth`, but correcting it collides
with nothing: Legion's rows are `lylyth1` and `lylyth3`, and a repaired `lylyth`
matches neither. The reason is the inconsistency just described. Those two rows
happen to follow the printing-encoding convention, and that is the only thing
keeping them clear of a bare `Lylyth` from another faction; under the `caine`
convention all three would collapse to one code. The same defect that caused the
Gravediggers failure incidentally prevents this one, which is a fair summary of
what an unreliable key is like to work with.

It is worth stating how little of this an automated audit can see. Of the 14
duplicated codes, exactly **one** — `caine` — carries more than one distinct
name, so a scan for *this code maps to two names* surfaces that collision and
no other. The rest are invisible to it, for different reasons. `butcher` and
`gunnbjorn` share a code *and* a name with their counterparts, so they read as
well-behaved duplicates, and they are indistinguishable on every column from
`rahera`, who genuinely is one character. `Khythos` never reaches the scan's
output at all: the typo gives the two rows different codes, so a code-keyed
join happens to hold them apart — and whether holding them apart is correct
depends on a question nobody has ruled on. One case is machine-detectable and
the rest are separable only by a ruling, which is this section's gate
justification restated as a count rather than an argument.

**The rule that follows: never infer faction from leader.** The badge names the army
or its parent faction and is stable; the leader is then searched *within that scope*,
so an ambiguous name never has to be resolved globally. This is what
`webapp/src/longshanks/factions.ts` already does, together with left-anchored
matching, prefix-shadow dropping, and card-title disambiguation for reprints sharing
an army. **[reported]**: the scoping key was independently measured as invariant —
**0 of 288 players changed army badge across five rounds**, while the leader-derived
faction flipped on exactly the rounds the shared-name caster was fielded.

The rule is now enforced on the path that previously escaped it. Where no badge is
available the resolver used to collapse a repeated name to a single answer, which
is right for one character fielded in two armies of the same faction —
`Sparkhammer` across Storm Legion and Gravediggers, `Sorscha` across 5th
Division and Armored Korps, each carrying the identical name in both rows — but
cannot be justified when the two armies sit in different factions.

This paragraph previously illustrated the rule with `Caine`, who is the one
Cygnar character it does not fit: First Army fields `Caine` and Gravediggers
fields `Caine 4`, so collapsing those two returns the wrong card. The example
was falsified by a fix earlier in this same work, and it survived here after
the identical claim had already been corrected in the resolver's comment and in
its tests — a third copy of a retracted premise, in a third file, found while
checking something unrelated. It is recorded rather than quietly amended
because §8.2 closes on exactly this, and an uncorrected instance sitting inside
the section that states the lesson is better evidence for it than the two that
were caught.
All five collisions above returned a confident army, and therefore a faction,
chosen on nothing better than table order. The collapse is now gated on
the candidates sharing a faction and returns nothing when they do not, which is
the module's own standard: a blank leader sends someone to the real list, a wrong
one does not. Badged lookups were always correct, which is why this survived —
the scoping rule was covering for it.

The refusal is correct for all five collisions, and for **two different reasons**
— which is the strongest argument for gating on ambiguity rather than on
identity. For `Butcher` and `Gunnbjorn`, two different models each, the old
behaviour named the **wrong character**. For `Rahera`, one character in two
factions, it named the **right** character and still invented an army and a
faction for her. A justification written around either case alone would have
been factually wrong about the other; nothing in an unbadged list distinguishes
the two armies, so in every case there is simply no answer to give. The gate
therefore keys on the faction being ambiguous, and needs no claim about who the
candidates are.

Enumerating the complete class confirms it end to end. Deriving every leader name
that appears in more than one army directly from the table — rather than
hand-listing the pairs the tests happen to cover — gives 15 repeated names, 5 of
them spanning two factions. **All five refuse when no badge is present**, and all
five resolve correctly when badged with either army. The five are `Butcher`,
`Gunnbjorn`, `Khythos`, `Rahera` and `Lylyth`, and the last is worth noting: it
is the collision §8.1 introduced as the one neither inventory had, and it is also
the one most easily missed when the class is listed by hand rather than derived,
because its rows carry printing numbers and never match as literal strings.

The ten remaining names repeat *within* a faction, where the collapse is by
design — but the answer still carries an army, and with no badge, or a badge
naming only the faction, that army is simply the first matching row in table
order. `settle()` is candid that only the attribution is uncertain. Nothing
downstream preserves that caveat: `parse.ts` assigns `declared?.army ?? found?.army
?? armyInfo(armyHint)?.army` to the list's army of record, so an inferred army
outranks even the faction the badge actually stated. For nine of the ten this
names the right caster in an arbitrary one of their two armies; for the tenth,
`Caine`, it names the wrong caster outright, as below. The uncertainty is real,
documented in the resolver, and unrepresentable in the value the resolver
returns — which is a type problem rather than a logic one, and is recorded here
because it bounds how much weight a downstream consumer should put on an
unbadged army.

Two caveats worth preserving. **Southern Kriels and Trollbloods are distinct
factions**, each with their own armies, and must not be merged as synonyms despite
sharing Gunnbjorn. And Longshanks' `Unlimited` is a catch-all whose "leaders" are
faction names rather than models; it is excluded from leader work deliberately.

Leader names are **not unique even within one faction**. Cygnar alone carries
`Caine` three times across First Army, Gravediggers and Storm Legion, plus `Jakes`
and `Sparkhammer` twice each; Khador has `Sorscha` and `Kovoskiy` doubled, Cryx
`Skarre`, Legion `Lylyth`, Southern Kriels `Bagadibawm`. Only the badge separates
them. Where the printing is undetermined the resolver returns the **unnumbered**
form rather than guessing one — answering `Caine`, never `Caine 4`, unless a card
title says which.

That is a safe widening in every case but one, and the exception is a live defect
rather than a hypothetical. It is safe for `Skarre`: no bare `Skarre` row exists,
so the collapsed form names a real caster, and a list reading `Skarre 1, Pirate
Queen` recovers `Skarre 1` from the title. It is **not** safe for `Caine`,
because there the collapsed form is itself a card — row 1388, First Army — so the
fallback stops widening and starts asserting. Measured on this branch:

```
"Caine 4"   no badge                 -> Caine @ First Army        wrong caster, wrong army
"Caine 4"   badge "Cygnar"           -> Caine @ First Army        wrong caster, wrong army
"Caine 4"   badge "Gravediggers"     -> Caine 4 @ Gravediggers    correct
"Skarre 1"  no badge                 -> Skarre @ Blackfleet       right caster, printing dropped
"Lylyth 1"  badge "Ravens of War"    -> Lylyth @ Ravens of War    right caster, printing dropped
```

The last two rows matter more than they look, and they correct the sentence
above. The fallback does not only fire where the printing is *undetermined* — it
fires wherever the badged army holds two printings of one character, **including
when the list text names the printing explicitly.** `Lylyth 1` and `Lylyth 3` are
both Ravens of War, so a list saying `Lylyth 1` is answered `Lylyth`; the number
the reader supplied is discarded. `Caine 4` badged Gravediggers survives only
because Gravediggers holds a single `caine` printing and the pool never widens.

So this is one mechanism at two severities, not two defects. Enumerating every
repeated leader name in the table and every badge for each gives 32 army-badged
cells: **30 return exactly what the list named, 4 of the remaining comparisons
drop a named printing** (`Skarre 1`, `Skarre 3`, `Lylyth 1`, `Lylyth 3`), and the
severe case — wrong caster *and* wrong army — appears only off the army-badged
path, where `Caine 4` resolves to `Caine @ First Army`.

There is a third face, and it is the mechanism's opposite symptom: **a refusal
where no ambiguity exists.**

```
"Lylyth 1"  no badge  -> undefined        globally unique, declined
"Lylyth 3"  no badge  -> undefined        globally unique, declined
"Lylyth"    no badge  -> undefined        an exact row exists, declined
"Skarre 1"  no badge  -> Skarre @ Blackfleet
```

`Lylyth 1` and `Lylyth 3` each appear in exactly one army in the entire
catalogue. Nothing about them is ambiguous and nothing needs a tie-break. They
are declined because `bare()` collapses them to `Lylyth`, which widens the pool
across Legion of Everblight and Khymaera, and the cross-faction gate — correctly,
on the question it was asked — refuses. The gate is not at fault; it is answering
a question about a stem the player never typed. Bare `Lylyth` is refused on the
same grounds even though Shadowflame Shard carries an exact row for it, because
literals are never compared before collapsing.

Which face appears is decided by something irrelevant to the input: how many
factions happen to share the collapsed stem.

| collapsed stem spans | outcome | example |
|---|---|---|
| one faction | `printing()` asserts | `Caine 4` → `Caine @ First Army`, wrong caster |
| two factions | the gate refuses | `Lylyth 1` → nothing, though it is unique |

**The false-refusal class is exactly two literals.** Of the five cross-faction
stems, only `lylyth` carries printing suffixes — `butcher`, `gunnbjorn`,
`khythos` and `rahera` are bare names in both factions, so their refusals are
genuine ambiguity and correct. Stating it as a closed set is deliberate: it
should fail loudly if a future printing-suffixed caster ever lands in a
cross-faction stem.

That changes the fix. Refusing when the collapsed form is itself a card addresses
the severe case alone and leaves the four lossy cells and both false refusals.
**Matching the literal name before falling back to the bare one addresses all
three**, because `Lylyth 1` then matches `Lylyth 1` and `Caine 4` matches
`Caine 4`, and neither pool ever widens far enough to need a tie-break or to
reach the gate. One change, three faces, which is a far easier thing to justify
than a special case for `Caine`. A second, independently written resolver over
the same catalogue runs exactly this exact-literal pass before any loose
matching, and **[reported]** does not exhibit the severe case at all — which is
evidence that the ordering, rather than the catalogue, is what produces it.

One cost should be taken deliberately rather than inherited from match order:
under literal-first, bare `Lylyth` would match Khymaera's real row and stop
refusing. That is arguable either way — it is a genuine exact match, but the
player may well have meant one of the Legion printings — and it is a decision,
not a side effect.

The faction-badged row is not a contrived input. The scoping note above records
that Longshanks titles the badge with an army for some players and with the parent
faction for others, and that a faction badge deliberately widens to every army
beneath it — so a Cygnar-badged `Caine 4` list takes exactly that path, and lands
on the one answer this document argues hardest against: a confident wrong one
where a blank was available.

It is **pre-existing and is not fixed here.** It predates this work; the
army-badged row above is the part this branch repaired, and a behavioural change
to the resolver wants its own branch and its own tests rather than a late commit
on a branch whose remaining purpose is documentation. It is recorded because the
alternative was to leave this paragraph describing a refusal the code does not
perform — which is precisely the failure §8.2 closes on, and which had already
been committed twice in this branch before being caught here a third time. The
shape of the fix is a signature rather than a `Caine` special case: refuse in that
fallback when the collapsed name is itself a leader somewhere in the table, which
keeps `Skarre` and refuses `Caine`.

The broader lesson is that a matcher which *writes* a
canonical name back into a record destroys evidence, so the write path warrants a
higher bar than the read path: a mis-resolved faction is recoverable from the
badge, an overwritten caster name is not.

### 8.2 Two armies were renamed, not added

Two badge titles — `Wicked Harvest` and `Clockwork Legions` — appear in WTC 2026 and
are absent from both catalogues, which broke leader inference for the players
carrying them. Before this event there are no game rows to read a leader from, so an
unrecognised army leaves the only available route blocked.

Transcribing the casters observed at one event would bake in a partial roster, so
the question is whether these are **new armies** or **retitled existing ones**. A
subset test against the casters fielded in 2026 found every one already present —
five of five for Wicked Harvest under Grymkin, four of four for Clockwork Legions
under Convergence of Cyriss.

Official card lists, obtained afterwards, confirm both as pure retitles:

| new title | existing entry | official roster | ours | verdict |
|---|---|---:|---:|---|
| Wicked Harvest | Grymkin | 6 | 6 | pure alias |
| Clockwork Legions | Convergence of Cyriss | 6 | 6 | pure alias |

Wicked Harvest resolves all six, including *Zevanna Agha, The Fate Keeper*
through the existing legacy alias `Old Witch`. Clockwork Legions resolves
Archnumen Aurora, Axis, Eminent Configurator Orion, Father Lucant, Forge Master
Syntherion and Iron Mother Directrix against the six Convergence already carries.
The names are therefore aliased onto the existing entries, which inherits each
complete roster — including casters nobody fielded in 2026 — and invents nothing.

**The conclusion held; the test that produced it should not have been trusted.**
A subset check over casters *observed at one event* cannot distinguish a retitle
from a retitle with additions, because a caster nobody brought is invisible to
it. It returned the right answer here and would have returned the same answer had
the roster genuinely grown. The authoritative list is what settles it, and an
intermediate draft of this section asserted a missing caster on the strength of a
roster that disagreed with ours. Attendance is a biased sample of a catalogue,
and no quantity of it establishes completeness — which is the same error, in the
same direction, as reading a strategy off five rounds of one team (§6.4).

**That disagreement turns out not to have been an error at all, and the reason
is worth more than the correction.** Athanor Locke is a real warcaster who
**changed faction**: Longshanks carries her former Convergence row as id 1239
(`active=0` — she is **not** currently legal in Convergence, whatever
third-party sources describing her as dual-faction may say) and her current
Crucible Guard row as id 1245 (`active=1`). A
Convergence card list naming her is enumerating the characters that faction has
had, not the ones it currently fields. Clockwork Legions has eight leader rows;
merge the two Aurora printings into the one character they represent and seven
remain, which is the published figure. Our six is the current active roster, and
the difference is Locke — who is **not missing from our table at all**. We carry
her under Crucible Guard, where she now belongs. Both numbers were right; the
two sources were answering different questions.

That makes the guard §9 asserts more pointed, not less. The plausible mistake
here is not inventing anyone — it is reading a Convergence card list, noticing
Locke absent from our Convergence roster, and adding her back **in good faith
with a published source to cite**. Doing so would both misfile a character who
moved and manufacture a cross-faction collision where none exists. An
*invents no leader upstream lacks* assertion refuses that on sight, which is why
it is a boundary rather than a formality.

The general distinction still holds and is worth keeping, because `active=0` is
a statement about current legality rather than about whether a card was ever
printed — `Asphyxious` is retired with no active home anywhere, and a catalogue
of what *exists* would carry him where a catalogue of what may be *fielded* must
not. This document is about pairing decisions at a tournament, so the active set
is the correct one throughout.

The mechanism matters because the claims that preceded it were wrong three times
over, about one character, in three different directions. She was reported as a
**seventh Convergence caster missing from our roster** (§8.2 — she had moved, and
we already carried her); as a **sixth cross-faction collision** (§8.1 — two rows,
one person); and as a **latent suffix hazard held off by her retirement** (§8.1 —
nothing to hold off). A fourth explanation, that someone had read the table
without filtering on `active`, was appealing precisely because it indicted a
discipline we had already adopted, and was wrong too: it predicts eight rows, not
seven.

Every one of those was a confident structural claim about a character none of the
analyses could field or look up, and every one was refutable from data already in
hand. The signature of a migration — a shared code with one row retired and one
active — was sitting in the table throughout. What was missing was not evidence
but the question: *are these two rows one person?*

**The same failure has a second, more mundane form.** The instances below were
all collected while writing this document, which bounds what they can be used
for: they establish that the error is easy, varied, and survives scrutiny, and
they establish nothing whatever about how often it happens. A ledger assembled
from a single piece of work cannot support a frequency, and claiming one would
commit, in the act of recording the mistake, the mistake being recorded. Each
entry is a count that described the rows someone had met rather than the rows
that exist:

| claim | actually | what was measured |
|---|---|---|
| the catalogue has 246 rows | 1722 in the payload, 246 after dedupe by id | a property of the reader's dictionary |
| same code and both active ⇒ different characters | `Rahera` is one character | the two cases checked |
| three whitespace defects in the table | six, across five rows | the three encountered during other work |

None of these was a limit on the available data. In all three the complete
record was already in the repository and the full scan cost a single command;
what was reported was the sample, and the sample was mistaken for the
population. That is the same error as reading a strategy off five rounds
(§6.4) or a roster off one event's attendance (§9), with the excuse removed —
there was no acquisition cost to plead. What the set supports is that this
failure is cheap to commit, cheap to prevent, and perfectly capable of
surviving in hands that are actively looking for it.

A fourth belongs with them but is a different species, and it is the only one
whose *detection* is instructive:

| claim | actually | what was measured |
|---|---|---|
| upstream has **204 active** leader records | 204 **total**, 200 active | the row count, correctly, under the wrong label |

Nothing here was miscounted. 204 is exactly the number of leader rows; only
the word *active* was wrong, and no amount of recounting would have found it,
because the count was right. What found it was arithmetic. The figure was used
as a completeness checksum against our 186, predicting a shortfall of
$204-186=18$; the reconciliation returned 14. The two did not agree, and the
disagreement is what sent someone back to the definition rather than to the
data. The correct subtraction is $200-186=14$.

> **A wrong number in prose is inert. The moment someone computes with it, it
> either reconciles or it does not.**

A fifth belongs to neither kind above, and the distinction is practical rather
than taxonomic. The first four are claims that were never true of the
population, and a measurement excludes them — which is exactly what the
reconciliation test of §9 does. This one was true when it was written and
*stopped* being true, and no test either repository could write would catch it,
because there is no assertion for *is this still the reason*.

Its source was also the closest to hand. Three justifications — in
`factions.ts`, in its tests, and in §8.1 of this document — were left
describing a world the fix in this very branch had removed. A test named
*treats one person shared
by two armies as a single answer* illustrated that rule with `Caine` — the one
character in the table for whom it is false, and false **because of a commit two
steps earlier in this PR**, which split Gravediggers' `Caine 4` from First
Army's `Caine`. Twenty lines away, `settle()`'s own comment named Caine as *the
exception that sets the rule's limit*. The file contradicted itself about the
distinction this document exists to establish. Separately, that comment
justified the cross-faction refusal as *it would name the wrong person*, which
`Rahera` falsifies in the same way she falsifies the signature rule above.

The third copy is the instructive one, because it was found last and by
accident. §8.1 went on using `Caine` as its example of a character shared by
two armies for two further rounds *after* the code and the tests had both been
corrected — the fix was applied where the problem had been noticed and not
where the premise had been used, which is the lesson this entry exists to
state, committed inside the section that states it.

Both assertions passed, and would have passed forever: each stated something
true for a reason that had stopped being true, and a green test cannot report
that. Nothing in CI can. The lesson is the one §8.1 arrived at from the other
direction — **a correction propagates to wherever its premise was used, not to
where it was found** — demonstrated here against our own work, by nobody
re-reading the comments our own rename had invalidated.

That is the one *detection* result among the five — it belongs to the
mislabelled count above, not to the stale premises just described — and it
argues for a specific practice: put figures into checksums rather than into sentences. A quoted
number is believed indefinitely; a number that participates in an equation is
tested every time the equation is evaluated. The reconciliation test of §9 is
that principle at its limit — every figure in it is computed on each run, so
no label in it can drift away from what it names without the suite going red.

The same episode supplies a caution about the discipline this document keeps
recommending. An attempt was made, after the fact, to overturn that very
correction: a third party asserted that no mislabelling had occurred and that
both figures had always been right, alongside a set of arithmetic — 204 rows,
200 active, 42 armies, 246 unique — that is entirely correct and verifies on
inspection. The correction was briefly withdrawn on the strength of it, and
then reinstated by the party who had originally issued it. The disclaimer that
should have governed the whole message was present in it: the third party
noted it had no record of the exchange in question, which is precisely the
visibility required to say that nothing had been retracted. **A checkable
claim and an uncheckable one travelled together, and verifying the first felt
like verifying the second.** *Verify before accepting* offers no protection
when the proposition verified is not the proposition in dispute — which is a
sharper statement of the §8.1 failure, where a shared surname was checked
against the catalogue repeatedly without anyone asking whether the two rows
were one person.

A separate defect in the same area did prove real and is fixed here. Longshanks
writes `di Morray`; the catalogue carried `Lukas`, the other half of Aurum Legate
Lukas di Morray's name, so lists naming him resolved to nothing at all. The
Longshanks string is now canonical with `Lukas` kept as an alias, so both forms
settle on one leader — the §8.1 principle applied to our own table rather than to
someone else's.

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

Four cautions specific to this supplement:

- **The 14,400-leaf figure is hand-derived and untested.** It should not enter
  published copy without a test asserting it, in the manner of
  `webapp/src/engine/adClaims.test.ts`.
- **Single-team, single-event.** Every §6 and §7 result describes one team across
  five rounds. They are offered as located hypotheses with explicit nulls, not as
  findings.
- **An event sample bounds nothing; only the upstream table does.** This is the
  generalisable finding of the exercise, and it is testable rather than a
  disclaimer. Longshanks ships its **own catalogue table embedded as JSON inside
  every event payload**, so our rows can be reconciled against the authoritative
  list instead of against attendance. Every gap found this cycle was invisible to
  event-derived scans and immediate in that table, three times over: a caster
  (`Harasheth`), a printing (`Caine 4` in Gravediggers), and — twice — **two
  entire armies**, `Covenant of the Flame` and `Dread Armada`, absent from *both*
  our catalogue and the sibling's independently, because no WTC 2026 player
  fielded either. The third instance is the one that settles the point: what was
  missing was not a record but a whole army with its full roster, and no amount
  of attendance could have revealed it. Those four gaps are **closed**.

  What makes this more than an anecdote is that the argument is now executable.
  `webapp/src/longshanks/catalogue.test.ts` reconciles our table against a
  fixture of that payload (event 37180, 246 rows deduped by id — the payload
  repeats the table verbatim about seven times, so an undeduped count is
  meaningless). Run against the table as it stood before this work, it names
  every defect listed above without being told what to look for: five missing
  armies, and twenty-five missing leaders including `di Morray`, `di Baro`,
  `Caine 4` under Gravediggers, `Harasheth`, and the full rosters of both
  absent armies. A day of argument, three reversals and several contradictory
  inventories were needed to find those by reasoning. The test rederives them
  in nine milliseconds, from the upstream record, without reference to who
  played what — which is the §8.2 lesson stated as a procedure instead of a
  regret.

  Reconciliation is accordingly **complete and mechanically enforced**, not
  outstanding:

  | | ours | upstream active | status |
  |---|---|---|---|
  | armies | 42 | 42 | reconciled; three carried under our names via `ARMY_ALIASES` |
  | leader entries | 186 | 200 | reconciled; 14 format markers knowingly omitted |
  | retired entries carried | 0 | 4 exist | asserted, not spot-checked |

  The fourteen are Longshanks' `X Unlimited` rows: it models the Unlimited
  *format* as an army and each faction's entry in it as a leader. They are not
  warcasters, so we carry the army with an empty roster and omit them by name,
  with the reason recorded at the point of omission. `Unlimited` is itself a
  genuine upstream army (id 1229, `code=z_unlimited`, a sort hack pinning it
  last in their menus), so the army totals agree as a real reconciliation
  rather than by coincidence — an earlier draft of this section hedged that
  they might not, and that hedge was wrong.

  The omissions match upstream's spelling **exactly**, including the double
  space in `Cygnar  Unlimited`. That is upstream's typo and is preserved rather
  than tidied, for the same reason the `Huxely` misspelling is kept: these
  strings are join keys, not prose, and a formatter that collapses the space
  breaks the check — which is the check working.

  A full scan of all eight fields of all 246 rows finds **six whitespace
  defects across five rows**, and the count is worth stating as a scan rather
  than as a list of encounters:

  ```
  1226  name  'Cygnar  Unlimited'   double inner space   (Unlimited)
  1347  code  'sparkhammer '        trailing             (Cygnar)
  1392  code  'absylonia '          trailing             (Legion of Everblight)
  1394  code  'asphyxious '         trailing             (Mercenaries)
  1400  code  'kaelyssa '           trailing             (Retribution of Scyrah)
  1402  code  'ragemonger '         trailing             (Southern Kriels)
  ```

  Five factions, non-contiguous ids, clean neighbours throughout — sporadic
  entry noise rather than one bad import, so there is no structural reason to
  expect the next payload stops at six. None of it changes a resolution today:
  we key on `(name, army)`, the `name` column is clean apart from 1226, and
  every one of these rows resolves correctly.

  It is not, however, inert. Grouping the leader rows by raw code finds 14
  duplicate groups; by trimmed code, 15. The difference is `Sparkhammer`, whose
  two rows are one character (§8.1). The defect is invisible to resolution and
  visible to counting, which is why it perturbed a figure in this document and
  no behaviour in the application. Anyone keying on `code` must therefore trim
  — while noting that trimming is a different normalisation from repairing a
  misspelling, and it is the latter that would merge `kythos` with `khythos`.

  Generalised, these are all one failure: **a census keyed on a rendered
  identifier is blind exactly where the rendering varies** — and the rendering
  varies precisely where the data is irregular, which is where the collisions
  are. The table carries three instances, each of which suppresses a true
  collision from the scan built to list collisions, so the audit returns clean
  and the count goes *up* under repair. Two are keyed on `code` — the trailing
  space on `sparkhammer `, and the `kythos`/`khythos` typo — and one is keyed
  on `name`: `Lylyth`, whose rows are `Lylyth 1` and `Lylyth 3`, so a scan
  comparing exact leader strings finds no collision at all.

  That last one produced the most instructive measurement in this work, because
  of how nearly it escaped. The same table, grouped two ways:

  | grouping | cross-faction | within-faction |
  |---|---|---|
  | exact leader literal | 4 | **10** |
  | printing-collapsed | 5 | **10** |

  The cross-faction figures disagree, which is the correction: the resolver
  collapses printings before it compares, so the collapsed grouping is the one
  that describes its behaviour, and `Lylyth` is a real fifth collision that the
  literal scan cannot see. But the within-faction figures **agree at ten while
  describing different sets**. The literal ten contains `Caine 4`, spanning two
  armies. The collapsed ten contains `Caine`, spanning three, because collapsing
  pulls the bare row 1388 into the same bucket — the §8.1 defect appearing as a
  *member* of the set rather than as a separate note. One member each, different
  rows, identical cardinality.

  So two measurements of different fields agreed on the count and disagreed
  about the population, and had the two been compared only on their numbers the
  agreement would have been read as corroboration. **The matching figure is the
  thing that stops anyone looking.** It is worth stating as a rule, because it
  inverts the usual instinct: when two independent methods produce the same
  number, that is evidence they measured the same field, not evidence the number
  is right — and the cheapest way to tell the difference is to diff the
  populations rather than compare the totals.

  One practical note on reporting these at all. A trailing space has no
  rendering, so `'sparkhammer '` and `'sparkhammer'` are distinguishable in
  prose only by a quoting convention and a reader's attention to one character
  of whitespace — which is presumably how six defects survived in a table that
  had been read many times, and how a correctly measured pair of them reached a
  written report as an identical pair. The cheap habit is to **state the field
  rather than the rendered value**: *1347 trailing, 2216 clean* cannot be
  mistyped into agreement, and `[sparkhammer ]` versus `[sparkhammer]` can.


  misfiled by faction, no leader is **invented** that upstream lacks, and none
  of the four retired entries (`Aurora 1`, `Locke`, `Mortenebra`, `Asphyxious`)
  has leaked in. The last two are the same property seen from both sides, and
  §8.2 is why it is worth asserting: a published card list can name a character
  who has since moved faction or been retired, so a roster built from one in
  good faith will file her in the wrong place or restore her outright. The check
  draws that line explicitly instead of leaving it to whoever is transcribing.

  **The guarantee is continuous, which is new.** Every other assurance in this
  document is of the form *we looked, on this date, and it was fine*. This one
  fails by itself when the catalogue drifts. The honest caveat is the other
  edge of that: the fixture is a point-in-time snapshot of one event's payload,
  so when upstream changes the test will fail, and the correct response is to
  refresh the fixture and reconcile against it — **never** to widen the
  exception list, which would convert the only check that can see a missing
  record back into one that cannot.

  There is a second kind of drift the reconciliation cannot see, and this PR
  committed it. **Adding an army can silently re-point an existing leader's
  armyless resolution.** Before `Covenant of the Flame` was added, `Feora`
  appeared in exactly one army, so a list naming her with no badge — or a badge
  reading only `Protectorate of Menoth` — resolved to Temple Guardians
  unambiguously. That was a certainty, not a guess. Adding the missing army gave
  her a second home, and because `printing()`'s last resort returns
  `pool[0].army` she now resolves to `Covenant of the Flame`, which wins only
  because it sorts earlier. `Malekus` and `Thyra` moved the same way, for the
  same reason, in the same commit — and so did `Aiakos`, by way of the other
  army that commit added, `Dread Armada`, which shares him with `Blackfleet`.

  The measurement worth publishing is not the list of names, which goes stale,
  but the size of the set the proposed guard would pin: **the leaders whose
  armyless resolution is ambiguous went from six to ten in this PR**, while the
  **cross-faction set was unchanged at five**. Two new armies therefore produced
  **zero new refusals and four new silent guesses**.

  That split is structural rather than a quirk of this commit. A new army is
  usually another printing of an existing faction's roster, so the names it
  repeats collide *within* a faction — the side with no gate. The guarded path
  rarely gains members; the quiet path absorbs nearly all catalogue growth, so
  the ratio degrades with every upstream release, and the number that grows is
  the one nothing reports.

  The army additions were still correct and would be made again: before them, a
  Covenant player's Feora was attributed to the Temple Guardians printing with
  no error raised, and one silently-wrong answer removed is worth an
  arbitrary-but-plausible one created. What is worth recording is that the
  change was **invisible** — every test stayed green, the counts did not move,
  and nothing in the suite asserts anything about the armyless path for these
  four. Reconciliation checks that we carry what upstream carries; it says
  nothing about a row appearing and changing the answer for a row that did not
  move.

  Two notes for whoever takes the resolver work, the second of which is a trap.
  The real protection is a guard that pins *which* leaders are ambiguous on the
  armyless path, so a future catalogue refresh that creates a new ambiguity
  fails rather than passes quietly — the same shape as the §8.1 fix, since both
  are about the fallback asserting where it should decline. That guard would
  have failed on the commit that added the two missing armies, because four
  leaders joined the ambiguous set — and an equivalent guard has since been
  shown to fail, on exactly its four newly-ambiguous leaders, against a second
  catalogue maintained independently of ours. **[reported]** It is the only
  measure proposed here that would have caught the change as it happened rather
  than described it afterwards.

  The trap is the obvious remedy. The tie-break is `pool[0]`, i.e. array order,
  and `ARMIES` is alphabetically sorted today — verified, all 42 entries — so
  the natural proposal is to assert the sort and convert a convention into a
  guarantee. **That assertion neither detects nor prevents this hazard; it
  mandates it.** Measured by moving `Covenant of the Flame` to the end of the
  array and changing nothing else: `Feora`, `Malekus` and `Thyra` all stay at
  Temple Guardians, and the other repeated names do not move at all. The three
  attributions shifted *because* the new army was inserted in sorted position.
  A sort assertion would have passed before that commit and after it, reporting
  nothing, while requiring the insertion discipline that caused it — under an
  enforced alphabetical rule, every future army sorting before an existing one
  silently re-points any leader the two share.

  What preserves existing answers is not *principled* order but *append-only*
  order, where nothing can displace an incumbent `pool[0]`. Those are different
  goods and they point opposite ways here: stateable and stable are not the
  same property. Nor is append-only a fix, which is the second half of the
  trap — under it a Covenant player's unbadged `Feora` returns Temple Guardians,
  which is precisely the silently-wrong attribution that adding the army
  removed. Append-only buys stability by freezing whichever attribution
  arrived first, right or wrong. Neither ordering rule has anything to say
  about which answer is correct, because the fallback's defect is that it
  answers at all. Only the ambiguous-set guard addresses that, which is why it
  is the one recommendation here.
- **A retired row is not a dead record; it is a record of a previous state.**
  Four entries upstream carry `active=0`, and the instinct is to treat them as
  one class of debris. They are not — they are four different relationships to
  the live table, and the differences decide what the no-retired assertion is
  actually for:

  | row | relationship to the active set |
  |---|---|
  | `Aurora 1` (1235) | superseded printing; `Aurora 2` (1236) is active in the same army |
  | `Locke` (1239) | **migrated faction**; retired under Convergence, active as Crucible Guard (1245) |
  | `Mortenebra` (1300) | **migrated faction**; retired under Mercenaries, recreated active as Cryx (2240) |
  | `Asphyxious` (1394) | no active counterpart anywhere, under any name or numbering |

  `Locke` and `Mortenebra` are the consequential pair, and they are the same
  phenomenon: neither was retired, both were **moved**. Upstream performs a
  faction change by retiring one row and creating another rather than by editing
  `parent_id`, so **re-parenting is invisible to anyone diffing only active
  rows**. That qualifies the reassurance that earlier additions were "purely
  additive with no re-parenting": true of those rows, but checked against a
  mechanism upstream does not use.

  It also gives the retired set a signature worth more than the four rows
  themselves. A shared code with one row retired and one active means a
  migration; a shared code with every row active means **nothing in
  particular** — it covers two different models as readily as one character in
  two factions, and §8.1 records that the table cannot separate those. The
  signature is useful in one direction only, which is the direction that
  matters here: both migrations are recovered by it mechanically, without any
  knowledge of the setting — exactly what was not done before three separate
  wrong claims were made about `Locke` (§8.2).

  This is also what the no-retired assertion is really defending, and it is not
  tidiness. Restoring either migration row would **manufacture a cross-faction
  collision that does not exist today**: `Locke` resolves cleanly to Crucible
  Guard and `Mortenebra` to Necrofactorium, and carrying their former homes
  alongside their current ones would make both ambiguous across factions, so
  §8.1's gate would begin refusing two casters it answers correctly now. The
  trigger is entirely plausible — someone notices `Asphyxious`, a major Cryx
  warcaster, is absent, finds his row in the export, and adds it in good faith
  with a source to cite. That is the §8.2 mistake exactly, and the assertion is
  what refuses it.

  The other two rows are harmless for different reasons, worth separating from
  luck. `Aurora 1` is a superseded printing and degrades gracefully: `bare()`
  strips the number, so a list naming the old card still identifies the
  character, and since `Aurora 2` is the only Aurora now live there is no second
  card to confuse it with. `Asphyxious` we match by accident rather than by
  judgement — we are right because we mirror the active set, not because anyone
  decided about him. The safe operation on the retired set is the one performed
  here — **assert its absence, and read it for history** — because treating it
  as uniformly restorable and treating it as uniformly discardable are both
  wrong, and only inspecting each row tells you which.

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
| Faction inferable from leader name | **refuted** | 5 cross-faction collisions; resolver now refuses unbadged |
| `Wicked Harvest` / `Clockwork Legions` are new armies | **refuted** | 6/6 and 6/6 against official rosters, active sets; retitles |
| Our catalogue matches Longshanks' | **reconciled** | 42/42 armies, 186/200 leaders, 0 retired carried; asserted continuously |
| Upstream re-parents by editing `parent_id` | **refuted** | `Mortenebra` retired under Mercenaries, recreated active under Cryx; invisible to an active-only diff |

---

## Sources

- `docs/WHITEPAPER.md` — the 2024 paper. Supplemented, not superseded.
- `docs/WTC2024_GROUND_TRUTH.md` — Findings 7–22, including Finding 11 (§4 here).
- `webapp/src/longshanks/factions.ts` — catalogue, resolution rules, and the §8.2 fix.
- `webapp/src/longshanks/catalogue.test.ts` and its fixture — Longshanks' own
  catalogue table for event 37180, and the reconciliation asserted against it (§9).
- `webapp/src/engine/protocol.ts` — the protocol engine whose shape §3.2 confirms.
- Five Pear Master navigation logs, USA Death Valley, WTC 2026 rounds 1–5, held as
  OCR transcripts outside the repository (§1).
- Rules references are to Warmachine Player Pack 2026 v1.1, p.20.
