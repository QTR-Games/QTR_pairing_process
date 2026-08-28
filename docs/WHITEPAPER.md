# The Mathematics of WTC 5v5 Pairing

*A consolidated technical whitepaper: model, methods, proofs, empirical
validation, and structural critique of the pairing process.*

---

## Abstract

The Warmachine WTC 5v5 pairing process is a finite, deterministic,
perfect-information, zero-sum, sequential game whose value is well defined under
optimal play. This paper derives that structure from first principles, shows what
the shipping scoring engine implicitly computes, and replaces a hand-tuned scalar
heuristic with an exact distribution-propagating solver whose single behavioural
parameter is falsifiable. Every quantitative claim is either proved or measured
against real data — the 400 games of WTC 2024 joined to the 5,425 ratings one team
recorded before the event.

Three results anchor the work. First, the correct per-round win threshold
$\tau = G(lo+hi)/2$ falls out of the zero-sum property rather than being tuned.
Second, the existing "smart sort" heuristic is empirically near-optimal for win
probability (mean regret 0.07 points), so the value of the rework is
*interpretability and honesty*, not better picks. Third, and most consequential
for anyone using or designing such a process, the pairing protocol contains
**structural asymmetries that turn several nominal choices into false ones** — the
sharpest being that securing matchup control weakly dominates securing table
control on every real board measured. These asymmetries, and the open research
they imply, are stated explicitly.

This document consolidates and supersedes the working notes in
`SCORING_MATHEMATICS.md`, `DECISION_SENSITIVITY_FINDINGS.md`,
`WTC2024_GROUND_TRUTH.md`, and `SCORING_DISTRIBUTION_PROPOSAL.md`. Where those
notes recorded a claim that was later corrected, this paper carries the corrected
result and cites the correction rather than re-deriving the error.

---

## Notation

| symbol | meaning |
|---|---|
| $G$ | games per round (5 at 5v5) |
| $lo,\ hi$ | minimum and maximum rating on the scale in use |
| $r$ | our rating of a matchup; the opponent rates it $lo+hi-r$ |
| $T_{\text{ours}},\ T_{\text{theirs}}$ | our / their round total |
| $\tau$ | dead-even round total, $G(lo+hi)/2$ |
| $N$ | integer win requirement, $\lfloor\tau\rfloor + 1$ |
| $D$ | a probability distribution over integer round totals |
| $\rho(D)$ | the objective value read from $D$ (floor, E-value, or $P(\text{win})$) |
| $\lambda$ | opponent rationality (quantal-response inverse temperature) |
| $c$ | points already banked above a subtree |

Scales in use are written `lo–hi`; the shipping default is `1–5`, where $3$ is
even.

---

## 1. Introduction

Every prior version of the tool scored a round by collapsing a game tree into a
single unitless number and sorting the openers by it. That number worked — this
paper shows *how well* it worked — but it could not be sanity-checked, carried no
risk information, and depended on three hand-tuned constants with no measurement
behind them.

The contributions consolidated here are:

1. A formal statement of the pairing game and the derivation of its win threshold
   from the zero-sum property alone (§2–§3).
2. The correct path-accumulation rule, established by an exact invariant rather
   than by argument (§4).
3. A distribution-propagating solver that subsumes the four scalar metrics the
   app previously computed, at lower total cost (§5–§6, §9).
4. A single, falsifiable opponent model replacing three tuned constants (§6).
5. Two structural results — shift-invariance of the memo, and the invalidity of
   alpha-beta pruning — that determine what can and cannot be optimised (§7–§8).
6. A turn-taking protocol solver that is tighter and more honest than the naive
   assignment bound, plus a decomposition of a decision into "our choice" and
   "their response" (§10).
7. Empirical validation against a real tournament (§11).
8. A structural critique identifying where the process itself makes options unfair
   or false, including the matchup-versus-table asymmetry (§12).
9. An explicit register of limitations and open research, with standing hypotheses
   for the questions current tooling cannot yet answer (§13).

---

## 2. The game and its formal structure

Five of our players are matched against five opponents. A round proceeds as an
alternating sequence of *offers* and *resolutions*: one side puts a player forward
against a restricted set of possible opponents, and the other side chooses which of
those actually happens. Control alternates. The last pairing is forced, because by
then only one player remains on each side.

This is a **finite, deterministic, perfect-information, zero-sum, sequential
game**, and each adjective earns its place: the tree bottoms out after five games
are assigned; there are no dice; both sides can see the full ratings matrix;
totals are constant-sum (§3); and players alternate rather than moving
simultaneously. By **Zermelo's theorem** the game therefore has a well-defined
value under optimal play, which is what makes the rest of this analysis meaningful.

**The tree.** At 5v5 the tree has **48,751 nodes** and **14,400 leaves**, every
leaf at depth 9, with 50 distinct openers at the root. There are nine nodes per
root-to-leaf path, not five — offer nodes and resolution nodes alternate — and that
distinction is the subject of §4.

---

## 3. Zero-sum structure and the win threshold

A matchup rated $r$ from our side is rated $lo+hi-r$ from theirs. Hence for any
complete round,

$$
T_{\text{ours}} + T_{\text{theirs}} = \sum_{g=1}^{G} (lo+hi) = G\,(lo+hi).
$$

The totals are constrained to a constant sum, so one side's gain is exactly the
other's loss. This justifies treating the opponent as an adversary maximising
*their* total, which is identical to minimising ours.

A round is won by finishing ahead, $T_{\text{ours}} > T_{\text{theirs}}$.
Substituting the identity gives the dead-even line

$$
\boxed{\ \tau = \frac{G\,(lo+hi)}{2}\ }.
$$

This is not a tuned constant; it is forced by the zero-sum property, and it agrees
with each shipped rating system's own documented "even" value:

| system | range | documented even | $\tau$ at $G=5$ |
|---|---|---|---|
| 1–3 | (1, 3) | 2 | 10.0 |
| 1–5 | (1, 5) | 3 | **15.0** |
| 1–10 | (1, 10) | 5.5 | 27.5 |

Because totals are integers, $T > \tau$ is exactly $T \ge N$ with the **win
requirement** $N = \lfloor\tau\rfloor + 1$ (so $N = 16$ at 1–5, $G=5$). Working in
integers removes every floating-point boundary case from the decision rule.

**A necessary scope limit on the identity.** The identity does two jobs and only
one survives contact with real data. *As a statement about outcomes* it holds — a
game one side wins, the other loses — and everything $\tau$ depends on is safe. *As
a statement about the opponent's beliefs* it is false: using $lo+hi-r$ to predict
what the opponent will **choose** assumes their grid is ours reflected, and against
a real opposing preparation sheet the two teams' views of the same 25 cells
correlate at $r = -0.049$ (§11, Finding 12). The adversarial *posture* is right;
inferring the opponent's *preference ordering* from our ratings is not.

---

## 4. What a path actually scores

The natural rule — sum every node's rating along a path — is wrong, because the
offer node and its resolution node both carry a rating for the same game and the
sum double-counts. The correct rule is:

> A node contributes its rating to the round total **iff** it is a *resolution*
> node, or it is the *forced final pairing* (a leaf, which resolves itself).

The evidence is an exact invariant, not an argument. Because the leaf set is closed
under complement (§3), the mean total over all leaves must be *exactly* $\tau$.
Measured over all 14,400 leaves of a real matchup:

| accumulation rule | min | max | **mean** |
|---|---|---|---|
| sum all nodes | 20 | 36 | 28.64 |
| resolutions only | 8 | 16 | 12.00 |
| **resolutions + forced final** | **10** | **20** | **15.00** |
| offers only | 11 | 20 | 16.64 |

Only one rule yields 15.00 — exactly, as the zero-sum argument demands. The
resulting distribution is symmetric about 15, spans 10–20, and puts 38.9% of leaves
above the line. The failure mode this caught is instructive: under the
double-counting rule *every* opener in *every* matchup reported a 100.0% win
probability. The algebra was flawless; it faithfully computed the wrong quantity.

---

## 5. Distribution propagation

The central change is what travels up the tree. Instead of a scalar score per node,
the solver propagates the full **probability distribution over final totals**,
stored as a sparse map from integer total to probability. Four operations suffice:

| operation | definition | meaning |
|---|---|---|
| point mass | $\delta_v$ | a settled leaf |
| shift | $(S_c D)(x) = D(x-c)$ | add this node's own points |
| mixture | $\sum_i w_i D_i,\ \sum_i w_i = 1$ | a choice we do **not** control |
| argmax | $D_{i^\*},\ i^\*=\arg\max_i \rho(D_i)$ | a choice we **do** control |

Mixture and argmax are the only combinators, and which applies is fixed entirely by
whose turn it is. That is the whole recursion. From one distribution the solver
reads floor, expected value, win probability, ceiling, standard deviation and the
10th percentile — the four scalar metrics the app used to compute separately are
four lossy projections of this one object.

---

## 6. The opponent model

**What the original code was doing.** The original scorer combined children at an
opponent node as a blend, `alpha*min_child + (1-alpha)*mean_child` with
`alpha = 0.80`, and separately reconstructed a Gaussian via
`mu - k*sigma - u/sqrt(n)` with `k = 0.85`, `u = 12.0`. This is the strongest
argument for the redesign: the original code was *already* rebuilding a
distribution — mean, variance, a lower confidence bound, a regret range — via a
Gaussian approximation using three hand-tuned constants. The instinct was right; it
was simply approximate and uncheckable.

**Quantal response.** Replace the blend with a single principled model. The
opponent prefers replies that hurt us but is not perfect, so reply $i$ with
value-to-us $\rho_i$ is played with probability

$$
w_i = \frac{e^{-\lambda \rho_i}}{\sum_j e^{-\lambda \rho_j}}.
$$

This is the standard **quantal-response / softmax** model. The single parameter
$\lambda$ is *skill*: $\lambda = 0$ is uniformly random (replacing `alpha = 0`),
finite $\lambda$ is plausibly fallible (replacing $0<\alpha<1$ plus `k`, `u`), and
$\lambda \to \infty$ is perfect minimax (replacing `alpha = 1`). One interpretable
parameter with units of skill replaces three dimensionless tuned constants, and
unlike `alpha`, $\lambda$ is falsifiable.

**Validation.** Three independent checks pass: (1) $\lambda\to\infty$ reproduces an
independently implemented minimax to $\pm 0.000000$ at $\lambda \ge 20$; (2)
$\lambda = 0$ is never worse for us than perfect play ($35.17 \ge 26$); (3)
expected value is monotone non-increasing in $\lambda$. Check (1) is the important
one: exact convergence to a value computed by unrelated code is strong simultaneous
evidence that the mixture, the shift and the accumulation rule are all correct.

**The conservation test.** On real data, the shipping `cumulative` sort metric
carries a measurable **cooperation bias of +1.67 points** — it scores as if the
opponent helps. The excess also gives an objective loss function against which
$\lambda$ could be fitted, since the true $\lambda$ should drive the excess to zero
(§13).

---

## 7. Shift-invariance and memoization

Let $X$ be a subtree's total distribution and $c$ the points banked above it. Three
objectives behave differently under that shift:

| objective | rule | shift-invariant? |
|---|---|---|
| expected value | $\arg\max \mathbb{E}[X+c] = \arg\max \mathbb{E}[X]$ | **yes** |
| floor | $\arg\max \min(X+c) = \arg\max \min(X)$ | **yes** |
| win probability | $\arg\max P(X+c \ge N) = \arg\max P(X \ge N-c)$ | **no** |

Expected value and floor are invariant because $c$ is added to every candidate and
cannot reorder them; win probability is **not**, because the threshold $N$ is a
fixed landmark and banking points moves you relative to it, changing whether to play
safe or gamble.

**Consequence for the memo.** For the shift-invariant objectives, memoizing on
canonical game state is provably optimal, collapsing 48,751 nodes to **5,332
distinct states** (9.1×). For win probability the key must additionally carry the
remaining requirement $N-c$; this widens the space to **13,415** $(\text{state},
need)$ pairs (3.6×) — a real cost paid only by the objective that needs it, and
verified to be threshold-invariant (the count is unchanged for $N$ from 10 to 35).

**How the violation surfaced.** The bug was found because the numbers were
*impossible*: a "maximize win probability" policy was being beaten at win
probability (82.1% vs 80.9%) by an expected-points policy — a contradiction, since
a win-probability-optimal policy cannot be out-won at its own objective. The cause
was exactly the shift violation: interior nodes compared a *subtree* total against
the *full-round* threshold, ignoring banked points. Threshold-indexing the memo
restored the ordering everywhere. The general lesson: an internal consistency check
that *must* hold is worth more than a plausible-looking output.

---

## 8. Why alpha-beta pruning is invalid here

Alpha-beta is sound only when a node's value depends on the *extremum* of its
children. The blend

$$
V = \alpha \min_i(c_i) + (1-\alpha)\,\text{mean}_i(c_i)
$$

depends on the **mean**, which depends on *every* child, so skipping any child
changes the value.

**Counterexample.** Children $[10,2,2,2]$ at $\alpha = 0.8$:
$V = 0.8(2) + 0.2(16/4) = 2.4000$. Prune one child to $[10,2,2]$:
$V' = 0.8(2) + 0.2(14/3) = 2.5333$. A discrepancy of $0.1333$ at a single node,
which compounds up the tree. Pruning is sound only at $\alpha = 1.0$, i.e. pure
minimax.

**What this leaves.** The *floor* axis is a pure minimum, so **branch-and-bound on
the floor is valid** — and currently unexploited (§13). Expectation is not
prunable; any future search-space reduction must target the floor or accept exact
enumeration.

---

## 9. Computational cost and near-optimality of the existing system

Carrying a distribution sounds costlier than carrying a number. Measured:

| computation | time |
|---|---|
| one scalar pass | 5.12 ms |
| **four scalar passes (what the app did)** | **20.49 ms** |
| one distribution pass | 9.66 ms |

A distribution costs 1.89× a *single* scalar pass, but the app never ran a single
pass — it ran four. Against the real baseline the distribution is **0.47×**, i.e.
roughly twice as fast, while producing strictly more information. Surrounding
engineering reduced end-to-end 5v5 scoring from **27,564 ms to ~975 ms** (~28×), and
traversal from 47.3 full passes to 1.0.

**The existing "smart sort" is near-optimal.** With the corrected
threshold-indexed policy, on three real matchups the app's `strategic3` pick scores
within 0.0–0.2% of the best available opener for win probability:

| matchup | app's pick (`strategic3`) | best available | gap |
|---|---|---|---|
| USA Condor | 69.4% | 69.4% | **0.0%** |
| USA Jackrabbits | 87.5% | 87.8% | **0.2%** |
| USA Bison | 59.1% | 59.1% | **0.0%** |

An earlier "+15.5% improvement" claim is **withdrawn** — it was an artifact of the
shift-invariance bug in §7. The honest value of the rework is therefore *not* better
picks. It is interpretable units ("69.4% to win" rather than "strategic3 = −121"),
recovered risk information (floor, ceiling, $\sigma$, P10 come free), fewer free
parameters (one $\lambda$ replaces `alpha`, `k`, `u`), falsifiability, ~2× speed,
and rigorous confirmation that the hand-built system was already deciding well.

---

## 10. The turn-taking protocol engine

Sections 2–9 describe the desktop engine, which bounds a round by minimising over
**every perfect assignment** of our five players to theirs. That bound is safe but
loose: many assignments are unreachable, because pairing is a turn-taking game, not
a free choice of permutation. The mobile `protocol.ts` plays the actual game.

**The protocol.** One side puts a player forward; the other offers **two** of
theirs; the putting-forward side picks which of the two plays; and the offered-but-
declined player is then put forward by their own side, with roles swapping. Two
decisions therefore exist at each step, belonging to **different sides**: *which
pair to offer* (the defending side) and *which of the pair plays* (the attacking
side). The leftover-becomes-next-attacker rule is what makes a **bus** possible — a
side can offer a pair knowing that whichever one is declined dictates the following
matchup. An assignment bound cannot represent this at all, because it has no notion
of turn order.

**The opponent, honestly.** Since the mirror axiom is false ($r\approx 0$, §11), the
engine does not infer what the opponent wants. It minimises **our** total on **our
own** numbers — not a claim about their preferences, but a bound: whatever they are
optimising, they cannot do worse to us than the worst that can be done to us.
`protocolFloor` therefore survives not knowing their grid at all. Finding 16 prices
this posture: it understates the realised total by 1.40 points on average (up to
2.5), so it is presented as a floor, never as a prediction.

**The option profile.** Minimax alone ties constantly: 28 of 31 real boards open
with two or more choices scoring identically. For each option the engine instead
examines *every reply the opponent has* and reports:

| quantity | meaning |
|---|---|
| `guaranteed` | value if they answer perfectly (the minimax value) |
| `ifTheyErr` | value under their *worst* reply |
| `punishingReplies` | how many replies actually hold us to the floor |
| `upside` | `ifTheyErr − guaranteed` |

`punishingReplies` is load-bearing: *one reply in ten is a different proposition
from three in ten*, though minimax scores them alike, and it separates 24 of the 28
tied boards. Ranking is **value-first** — upside never buys a lower floor — so the
profile only reorders options already tied and can never trade a guarantee for a
gamble.

**Choice versus response.** Measuring the two halves of a decision separately in
round points across 31 boards:

| | mean | median | max |
|---|---|---|---|
| our opening choice | 0.48 | **0.00** | 1.0 |
| their reply | 1.26 | 1.00 | 2.0 |

Their reply outweighs our choice on 20 of 31 boards, and our choice is worth
nothing at all on 16 of 31. The consequence is structural: **ranking openings
cannot be the product**, because on the median board there is nothing to rank. What
remains actionable is the error surface — how much upside is on the table and how
many replies remove it — which is exactly the profile above, reached independently.

---

## 11. Empirical validation against WTC 2024

Sections 2–10 reason about the model from the inside. This section checks it from
the outside, against **400 real games** of Warmachine WTC 2024 (Longshanks event
10904, 32 teams / 160 players) joined to the **5,425 ratings one team recorded
before the event** across all five of their players versus all 155 opponents. It is
the first time in the project's history that the model's *inputs* can be checked
against the *outcomes they were meant to predict*. That team went 16–9 and lost the
final round 2–3.

- **The scenario dimension carries no information.** Across every real database ever
  produced — 1,150 matchup cells — **zero** vary by scenario; the maximum distinct
  ratings found in any cell is 1. Every scenario-aware cost is a 7× multiplier over a
  constant. (This is as much a UI finding as a math one: users never expressed a
  scenario belief through the interface. The recommendation is to collapse by
  default, keep the capability, and make divergence cheap to express — not to delete
  the dimension.)
- **The rating is not a calibrated strength.** 74.1% of ratings are the single value
  `3`, the value `5` was never used once, and the team won 70% of games their own
  ratings implied they would win ~45% of. Ratings behave as a **pessimistic ordinal
  hint**, which means *absolute path totals are not meaningful — only comparisons
  between lines are.*
- **The decisive game was rated "dead even."** No search over that grid could have
  flagged it, at any $\lambda$, under any opponent model. With a near-uniform input
  matrix the honest output is "the grid is too flat to support a recommendation,"
  and the engine must be able to say so.
- **The mirror axiom is false.** Two teams' ratings of the same 25 cells correlate
  at $r = -0.049$; a jackknife over all 25 cells moves $r$ across $-0.128\ldots+0.132$.
  Read this as *indistinguishable from 0, decisively distinguishable from +1*.
- **The opening is the flattest decision in the round.** Its median leverage spread
  across 31 boards is literally **0** (players separate on only 15/31), while the
  *second* decision separates on **26/31** with a median spread of 2 points on a ~17
  point total. The app historically put its heaviest analysis on its weakest
  decision.
- **A real, unmodelled terrain axis exists.** Table/terrain priority is a global coin
  flip (51% vs 49%) but splits by faction into large effects of opposite sign — a
  43-point spread from Dark Host (+21.3% as defender) to Shadowflame Shard (−22.4%) —
  that cancel in aggregate. The signal is real, per-army, derivable from public
  results, and the process has never modelled it.

---

## 12. Structural asymmetries and false choices

The sections above analyse how to *play* the process well. This section asks a
different question: where does the **design of the process itself** make a nominal
choice unfair, degenerate, or false — a decision the rules present as open that is
in fact near-solved, noise, or unrepresentable? Six such asymmetries are
established; each is either proved or measured, and each is a caution for anyone
adopting a pairing scheme of this shape.

### 12.1 Matchup control weakly dominates table control (the central asymmetry)

The dice-off winner chooses to be Team A or Team B, and per Player Pack 2026 v1.1
p.20 that single choice *is* the matchup-versus-table trade. Team A gets three
matchup picks and two table picks; Team B gets two matchup picks and three table
picks. Working it through pairing by pairing, the last table is forced rather than
chosen, so the real split is two matchup picks and two table picks apiece, plus one
extra matchup pick for the receiving side traded against one extra table pick for
the opening side:

|          | pairing pick | table pick | tables remaining |
|----------|--------------|------------|------------------|
| matchup 1 | B | A | 5 |
| matchup 2 | A | B | 4 |
| matchup 3 | B | A | 3 |
| matchup 4 | A | B | 2 |
| matchup 5 | A | B | 1 ← forced, not a choice |

So **opening trades one matchup pick for one extra table pick.** Measured over all
31 real WTC 2024 boards, taking the matchup side (receiving) is better on **18**,
identical on **13**, and worse on **0**. A synthetic hunt over 16,000 random 5v5
boards found exceptions only where ratings tie — 0/5,000 on the 1–5 scale, and
roughly 1 in 300 on compressed 1–2 / 4–5 scales, each worth at most a single point.

The conclusion is that the rules present a *balanced-looking* trade — "3 matchups +
2 tables" against "2 matchups + 3 tables" — that is **not balanced**: the matchup
pick is worth strictly more than the table pick almost everywhere, so the A/B choice
is a **near-solved decision dressed as strategy**. This is the elephant in the room.
The exceptions are real but rare and small, and they cluster exactly among teams who
rate everything a 3 or a 4 — which is why the tool computes the answer per board
rather than printing "always receive."

> **Research gap — the table half is not priced.** This research has not yet been
> performed. The solver quantifies only the matchup half of the trade; the value of a
> table pick is never put on a common scale with the value of a matchup pick, so the
> dominance above is *demonstrated empirically and by community consensus, not proved
> from a joint model.* Based on other aspects of the current work, the standing
> hypothesis for how this factors into the WTC Pairing Process is: **a table pick is
> worth materially less than a matchup pick on all but rating-compressed boards,
> because (a) receiving already wins or ties 31/31 with the table half entirely
> excluded, and (b) the measured per-faction terrain swing (§11) is ±10–22% of a
> single game, whereas a matchup swing routinely moves a whole game.** A joint model
> would price a table pick as a conditional option — worth most for armies with high
> terrain-dependence, near-zero for terrain-agnostic armies — and would only overturn
> the dominance on boards where matchups are near-tied *and* one side fields a
> terrain-dependent army. That combination is expected to be vanishingly rare, but it
> has not been searched for.

### 12.2 The opening lead is a low-information false choice

The decision the UI has always foregrounded — which player to lead with — is the
flattest in the round. Its median leverage is exactly 0 (§11), and the
choice-versus-response decomposition finds it worth nothing on 16 of 31 boards
(§10). Presenting a single "best opener" with apparent precision **invites the user
to agonise over a coin flip** and mis-locates the decision that actually wins the
round, which is the second one. This is a false choice created by the *tool's
framing* rather than the rules, but it is structural: the flatness is a property of
where real ratings cluster, not of one dataset.

### 12.3 Turn order confers unrepresentable leverage (the bus)

Because the declined half of an offer becomes the next attacker, a side can steer
the following matchup by *how it offers* — the bus. A permutation/assignment view of
the round cannot represent this at all, and consequently overstates the guarantee:
the naive assignment floor is optimistic by 1.40 points on real data, up to 2.5 on
one board (§10, Finding 16). The asymmetry is that **sequencing itself is a resource
one side holds**, and a scheme scored as if pairings were chosen simultaneously will
systematically misprice it.

### 12.4 Scale compression manufactures false ties and false distinctions

The rating scale is a lossy instrument, and its losses cut both ways. On real
rosters 3–4 of 5 openers are *exactly* tied on the floor, so a scheme that reports a
single winner manufactures a **false distinction** from noise. Conversely, the same
1-point-of-17 spread that looks "flat" in points spans roughly **60 percentage
points of win probability** (e.g. USA Bison ranges 7.6%–70.6%) — so reporting the
unitless score manufactures a **false tie**, hiding a decision that genuinely
matters. Compression is worst precisely for the teams most affected: those who rate
everything 3–4, who are both most likely to hit the matchup-vs-table exception
(§12.1) and least well served by a single ranked column.

### 12.5 The mirror axiom is an unfounded certainty

Any heuristic that assumes the opponent values matchups as the exact inverse of your
own ratings is resting on a correlation of $r\approx 0$ (§11, Finding 12). Advice
premised on "they want the cells we fear" is therefore a **false certainty**: it
reads as knowledge but encodes an assumption the data refute. The honest posture is
the worst-case bound of §10, which is deliberately *not* a claim about their
preferences.

### 12.6 A real decision axis is discarded entirely

Terrain/table dependence is a measurable, per-army, publicly derivable signal with a
43-point spread (§11, Finding 11), and it is the *compensation* the rules hand the
side that concedes matchup control (§12.1). By modelling neither the axis nor its
value, the process throws away the one lever that could, in principle, make the
table pick worth taking — which both undervalues a genuine choice and leaves §12.1's
dominance provable only empirically.

> **Research gap — the terrain prior is located but not built.** This research has
> not yet been performed. Finding 11's per-faction effects rest on 8–69 games per
> cell, no significance test has been run, and faction is confounded with player
> skill. Based on other aspects of the current work, the standing hypothesis for how
> this factors into the WTC Pairing Process is: **a per-army terrain-dependence prior
> exists and is stable enough to be actionable — not as a tie-breaker on the grid but
> as a rule for *whom to hold for the table pick* — and once measured with confidence
> intervals against a second event it will convert the table pick from a
> near-worthless concession (§12.1) into a conditionally valuable one for a minority
> of terrain-dependent armies.** Until that measurement exists, the tool's honest
> move is to state *who holds each table pick* (derivable from the rules with no data
> entry) and leave the judgement to the player at the table.

---

## 13. Limitations and open problems

Several questions are genuinely unresolved, and a subset are beyond what the current
data and tooling can settle. Those are flagged with an explicit standing hypothesis
so the gap is on the record as an exploration rather than a silent omission.

**Resolved-but-narrow, and engineering-ready.**

- *Branch-and-bound on the floor axis* is valid (§8) and unexploited. This is
  implementation work, not research.
- *Whether the sort path should adopt the conserving rule.* The `cumulative`
  metric's +1.67-point cooperation bias is measured (§6); whether to change it is a
  product decision requiring a reviewed golden-master re-baseline, deliberately left
  open.

**Open research, within reach of existing tooling.**

- *Fitting $\lambda$ from data.* Every completed round is an observed opponent
  decision, and §6's conservation excess supplies a loss function against which
  $\lambda$ — possibly per-opponent — could be fitted.

  > **Research gap.** This research has not yet been performed. Based on other aspects
  > of the current work, the standing hypothesis for how this factors into the WTC
  > Pairing Process is: **$\lambda$ is low and opponent-specific — most opponents are
  > far from perfect minimax — so a fitted $\lambda$ will raise guaranteed-value
  > estimates above the worst-case floor for most opponents while leaving the *ranking*
  > of options essentially unchanged, since the floor already ranks within 0.07 points
  > of optimal.**

- *Whether the choice-versus-response ratio holds at later decisions.* The
  decomposition (§10) measures the opening; §11 shows the second decision is where
  leverage lives, but the two halves have not been separated *there*.

  > **Research gap.** This research has not yet been performed. Based on other aspects
  > of the current work, the standing hypothesis for how this factors into the WTC
  > Pairing Process is: **the response continues to outweigh the choice at every depth
  > we own, because the same mechanism — their reply caps our options equally — applies
  > recursively; the actionable signal at each of our decisions is therefore the error
  > surface (upside and count of punishing replies), not a point ranking of our
  > moves.**

**Open research, beyond current data.**

- *Confirming near-optimality of `strategic3` beyond three matchups.* The 0.07-point
  regret result (§9) rests on three matchups from one team; §10's other results use
  31 boards, but for different questions.

  > **Research gap.** This research has not yet been performed at scale. Based on other
  > aspects of the current work, the standing hypothesis for how this factors into the
  > WTC Pairing Process is: **`strategic3` remains near-optimal across a wider corpus,
  > because real ratings compress toward the middle (§11) and a compressed matrix leaves
  > little for any policy to gain; the expected failure case is not a systematically
  > worse pick but occasional divergence on the rare wide-spread board, which is exactly
  > where any sensible heuristic and the exact solver already agree.**

- *The opponent's true grid.* It is, in general, unknowable ($r\approx 0$), which is
  why the engine bounds rather than predicts.

  > **Research gap.** This research cannot be performed from our own ratings. Based on
  > other aspects of the current work, the standing hypothesis for how this factors
  > into the WTC Pairing Process is: **no useful estimate of the opponent's preference
  > ordering can be recovered from our grid, so the worst-case floor is not a
  > provisional stand-in for a better opponent model but the correct terminal posture;
  > any future improvement must come from *their* observed choices, not from *our*
  > numbers.**

---

## 14. Reproducibility

The desktop engine is additive and off by default; it never writes `sort_value`, so
existing rankings are byte-identical unless explicitly enabled:

```powershell
$env:QTR_ENGINE = "model"     # engine reads the Tk-free model tree
$env:QTR_RISK   = "1"         # adds P(win), Floor, P10 and sigma columns
$env:QTR_RISK_LAMBDA = "1.0"  # optional opponent rationality
python main.py
```

Every displayed figure is a **round total**, not a subtree total: each node's
distribution is shifted by the points banked above it before display, because the
raw subtree distribution of a deep node would report an impossible floor for a round
that cannot finish that low. Standard deviation needs no such correction — it is
shift-invariant.

The protocol engine's key measurements reproduce under `vitest` in `webapp/`, e.g.:

```bash
cd webapp
QTR_MEASURE=1 npx vitest run src/engine/measure.leverage.test.ts \
  --reporter=verbose --disable-console-intercept
# open-or-receive dominance:   src/engine/measure.openOrReceive.test.ts
# synthetic exception hunt:     src/engine/measure.openTheorem.test.ts
# choice vs response:           src/engine/measure.decompose.test.ts
# worst-case = mirror axiom:    src/engine/measure.opponent.test.ts
```

---

## 15. Summary of results

| result | status |
|---|---|
| $\tau = G(lo+hi)/2$ generalises across 1–3 / 1–5 / 1–10 | proved; matches documented values |
| Accumulation = resolutions + forced final | proved by exact mean = 15.00 |
| $\lambda\to\infty$ reproduces minimax | verified exactly, independent implementation |
| Alpha-beta invalid under the alpha-blend | proved by counterexample |
| Floor axis remains prunable | follows from it being a pure minimum |
| Expected value and floor are shift-invariant | proved; state-only memo is optimal |
| Win probability is not shift-invariant | proved; found via an impossible measurement |
| Distribution pass is 0.47× the four-scalar baseline | measured |
| Existing `strategic3` is near-optimal for $P(\text{win})$ | measured; mean gap 0.07% |
| Receiving (matchup control) weakly dominates opening | measured; better 18/31, level 13/31, worse 0/31 |
| Opening trades one matchup pick for one table pick | derived from Player Pack 2026 v1.1 p.20 |
| Opponent mirror axiom is false | measured; $r=-0.049$, robust under jackknife |
| Assignment floor is optimistic vs the protocol | measured; +1.40 pts mean, up to 2.5 |
| The opening is the round's flattest decision | measured; median leverage 0, second decision separates 84% |
| Scenario dimension carries no information | measured; 0 of 1,150 cells vary |
| Earlier "+15.5% improvement" | **withdrawn — artifact of a bug** |
| Earlier "rosters are flat" | **qualified — artifact of the points scale** |

---

## Sources

This paper consolidates the project's working notes. The originals are retained for
their derivations and their record of corrections:

- `docs/SCORING_MATHEMATICS.md` — the desktop derivation and the protocol engine.
- `docs/WTC2024_GROUND_TRUTH.md` — the empirical validation (Findings 7–22).
- `docs/DECISION_SENSITIVITY_FINDINGS.md` — sensitivity analysis on real rosters.
- `docs/SCORING_DISTRIBUTION_PROPOSAL.md` — the distribution-propagation proposal.
- `docs/TECHNICAL_ARCHITECTURE.md` — system architecture and data model.
- Rules references are to Warmachine Player Pack 2026 v1.1, p.20.
