# The Mathematics of QTR Pairing

*A technical derivation of the scoring system, written for a reader who wrote
the original math himself.*

---

## 0. What this document is

This is the proof-and-derivation companion to the scoring rework. It explains
what the pairing problem actually is, what the original scoring system was
implicitly computing, where that implicit model is exactly right, where it is
subtly wrong, and what the replacement computes instead.

Every quantitative claim here was measured or proved, not asserted. Where a
claim was initially wrong — and several were — the error and its correction are
recorded rather than quietly removed, because the errors are instructive.

---

## 1. The game

### 1.1 Structure

Five of our players are matched against five opponents. A round proceeds as an
alternating sequence of *offers* and *resolutions*:

| depth | node | kind |
|---|---|---|
| 1 | `Dan vs JVM (3/5) OR Brandon (4/5)` | offer |
| 2 | `JVM rating 3` | resolution |
| 3 | `Brandon vs Bokur (3/5) OR Kyle (3/5)` | offer |
| 4 | `Bokur rating 3` | resolution |
| … | | |
| 9 | `Jack vs Justin (4/5) OR Justin (4/5)` | forced final |

One side puts a player forward against a restricted set of possible opponents;
the other side chooses which of those actually happens. Control alternates. The
last pairing is forced, because by then only one player remains on each side.

This is a **finite, deterministic, perfect-information, zero-sum, sequential
game**. Every one of those adjectives earns its place:

- *finite* — the tree bottoms out after all five games are assigned;
- *deterministic* — no dice; a rating is a fixed number;
- *perfect information* — both sides can see the full ratings matrix;
- *zero-sum* — established in §1.3;
- *sequential* — players alternate, they do not move simultaneously.

Together these mean the game has a well-defined value under optimal play, by
Zermelo's theorem. That is what makes any of the rest of this meaningful.

### 1.2 The tree

At 5v5 the tree has **48,751 nodes** and **14,400 leaves**, with every leaf at
depth 9. The root has 50 children — the 50 distinct openers.

Nine nodes per path, not five. This matters enormously and is the subject of
§2.1.

### 1.3 Why it is zero-sum

A matchup rated `r` from our side is rated `lo + hi - r` from theirs. For the
1–5 system, a game we rate 4 they rate 2. Therefore, for any complete round,

$$
T_{\text{ours}} + T_{\text{theirs}} = \sum_{g=1}^{G} (lo + hi) = G\,(lo + hi)
$$

The two totals are constrained to a constant sum, so one side's gain is exactly
the other's loss. This is the formal justification for treating the opponent as
an adversary maximizing *their* total, which is identical to minimizing ours.

### 1.4 The win threshold

A round is won by finishing ahead of the opponent, i.e. \(T_{\text{ours}} >
T_{\text{theirs}}\). Substituting the zero-sum identity:

$$
T_{\text{ours}} > G\,(lo+hi) - T_{\text{ours}}
\quad\Longleftrightarrow\quad
T_{\text{ours}} > \frac{G\,(lo+hi)}{2}
$$

So the dead-even line is

$$
\boxed{\ \tau = \frac{G\,(lo + hi)}{2}\ }
$$

This is not a tuned constant; it falls out of the zero-sum property. It also
agrees with each shipped rating system's own documented "even" value, which is
in every case the midpoint of its range:

| system | range | documented even | \(\tau\) at \(G=5\) |
|---|---|---|---|
| 1–3 | (1, 3) | 2 | 10.0 |
| 1–5 | (1, 5) | 3 | **15.0** |
| 1–10 | (1, 10) | 5.5 | 27.5 |

Because totals are integers, the strict inequality \(T > \tau\) is exactly
\(T \ge \lfloor \tau \rfloor + 1\). Call that integer the **requirement**,
\(N = \lfloor \tau \rfloor + 1\). For 1–5 at five games, \(N = 16\). Working in
integers removes every floating-point boundary case from the decision rule.

---

## 2. What a path actually scores

### 2.1 The accumulation rule (and a bug it caught)

The natural assumption — sum `base` over every node on the path — is **wrong**,
and wrong in a way that is invisible until you check it against something.

Summing all nine nodes double-counts: the offer node and its resolution node
both carry a rating for the same game. The correct rule is:

> A node contributes its rating to the round total if and only if it is a
> **resolution** node, or it is the **forced final pairing** (a leaf, which
> resolves itself).

The evidence is an invariant rather than an argument. Because the leaf set is
closed under complement (§1.3), the mean total over all leaves must be *exactly*
half of \(G(lo+hi)\) — that is, exactly \(\tau\). Measured over all 14,400
leaves of a real matchup:

| accumulation rule | min | max | **mean** |
|---|---|---|---|
| sum all nodes | 20 | 36 | 28.64 |
| resolutions only | 8 | 16 | 12.00 |
| **resolutions + forced final** | **10** | **20** | **15.00** |
| offers only | 11 | 20 | 16.64 |

Only one rule produces 15.00. Not approximately — exactly, which is what the
zero-sum argument demands. The resulting distribution is symmetric about 15,
spans 10–20, and puts 38.9% of leaves above the line.

The failure mode this caught is worth stating plainly, because it is the kind
of bug that does not announce itself: with the double-counting rule, every
opener in every matchup reported a **100.0%** win probability. The algebra was
flawless; it was faithfully computing the wrong quantity.

### 2.2 Distributions, not scalars

The central change is what propagates up the tree. Instead of a scalar score
per node, we propagate the full **probability distribution over final totals**,
represented as a sparse map from integer total to probability.

Four operations suffice:

| operation | definition | meaning |
|---|---|---|
| point mass | \(\delta_v\) | a settled leaf |
| shift | \((S_c D)(x) = D(x - c)\) | add this node's own points |
| mixture | \(\sum_i w_i D_i,\ \sum_i w_i = 1\) | a choice we do not control |
| argmax | \(D_{i^\*},\ i^\* = \arg\max_i \rho(D_i)\) | a choice we do control |

Mixture and argmax are the only two combinators, and which one applies is
determined entirely by whose turn it is. That is the whole recursion.

---

## 3. The opponent model

### 3.1 What the original code was doing

The original scorer combined children at an opponent node as

```python
child_component = alpha * min_child + (1.0 - alpha) * mean_child   # alpha = 0.80
```

This is a *blend* between assuming a perfect opponent (`min`) and a random one
(`mean`). It is a reasonable instinct — real opponents are neither — but it has
three problems:

1. `alpha` is dimensionless and hand-tuned; there is no measurement that sets it.
2. It destroys the possibility of pruning (§5).
3. It produces a number in no units, which cannot be validated against anything.

Alongside it, `confidence2` computed

```python
mu = sum(child_scores) / len(child_scores)
sigma = sqrt(variance)
conservative = mu - (k * sigma) - (u / sqrt(n))     # k = 0.85, u = 12.0
regret2 = max(0, ceiling2 - floor2)
```

**This is the strongest argument for the whole redesign.** Mean, variance,
sigma, a lower confidence bound, a regret range — the original code was already
reconstructing a distribution, via a Gaussian approximation, using three
hand-tuned constants (`alpha = 0.80`, `k = 0.85`, `u = 12.0`). The instinct was
right. It was simply doing it approximately, in a form that could not be checked.

If you are already computing the first two moments and pretending they describe
a bell curve, you may as well carry the actual distribution — which is *cheaper*
than four separate scalar passes (§6).

### 3.2 Quantal response

Replace the blend with a single principled model. The opponent prefers replies
that hurt us, but is not perfect. Give reply \(i\) with value-to-us \(\rho_i\)
the probability

$$
w_i = \frac{e^{-\lambda \rho_i}}{\sum_j e^{-\lambda \rho_j}}
$$

This is the **quantal response** / softmax model, standard in behavioural game
theory. The single parameter \(\lambda\) is *skill*:

| \(\lambda\) | behaviour | replaces |
|---|---|---|
| 0 | uniformly random | `alpha = 0` |
| finite | plausibly fallible | `0 < alpha < 1`, plus `k`, `u` |
| \(\to\infty\) | perfect minimax | `alpha = 1` |

One interpretable parameter with units of skill replaces three dimensionless
tuned constants. And unlike `alpha`, \(\lambda\) is falsifiable — it can in
principle be fitted to observed opponent decisions.

### 3.3 Validation

Three independent checks, all passing:

1. **\(\lambda \to \infty\) reproduces minimax exactly.** Against a separately
   written, independently implemented minimax (deliberately *not* sharing code
   with the engine):

   | \(\lambda\) | expected | Δ vs minimax |
   |---|---|---|
   | 1 | 27.136237 | +1.136237 |
   | 5 | 26.013626 | +0.013626 |
   | 20 | 26.000000 | **+0.000000** |
   | 1000 | 26.000000 | **+0.000000** |

2. **\(\lambda = 0\) is never worse for us than perfect play**: 35.17 ≥ 26. A
   weaker opponent cannot hurt us.

3. **Monotonicity**: expected value is non-increasing in \(\lambda\).

Check 1 is the important one. Exact convergence to a value computed by
different code is strong evidence that the mixture, the shift and the
accumulation rule are all correct simultaneously.

---

## 4. Shift-invariance: which objective you can memoize

This section contains the subtlest result, and it was found by a contradiction
rather than by reasoning.

### 4.1 The property

Let \(X\) be the distribution of a subtree's total and \(c\) the points already
banked above it. Three candidate objectives behave differently under that shift:

| objective | rule | shift-invariant? |
|---|---|---|
| expected value | \(\arg\max \mathbb{E}[X + c] = \arg\max \mathbb{E}[X]\) | **yes** |
| floor | \(\arg\max \min(X + c) = \arg\max \min(X)\) | **yes** |
| win probability | \(\arg\max P(X + c \ge N) = \arg\max P(X \ge N - c)\) | **no** |

Expected value and floor are invariant because \(c\) is a constant added to
every candidate — it cannot reorder them. Win probability is *not*, because the
threshold is a fixed landmark: banking points moves you relative to it, which
changes whether you should play safe or gamble.

### 4.2 Consequence for the memo

The tree's 48,751 nodes collapse to **5,392 distinct game states** — a 9.0×
reduction, and memoizing on canonical state is provably optimal for the
shift-invariant objectives (misses equal distinct states exactly).

But for win probability, the canonical state is **not a sufficient key**. The
same state reached with 12 points banked versus 9 is a genuinely different
decision problem. The key must include the remaining requirement
\(N - c\). Empirically this widens the state space from 5,332 to 19,807 (collapse
9.1× → 2.5×) — a real cost, paid only by the objective that needs it.

### 4.3 How the error surfaced

The bug was not found by inspection. It was found because the numbers were
*impossible*:

| matchup | policy = max expected points | policy = max win probability |
|---|---|---|
| USA Jackrabbits | **82.1%** | 80.9% |

A policy that maximizes win probability cannot be beaten at win probability by
a policy optimizing something else. That is a contradiction, not a close call,
and it can only mean the "maximize win probability" policy was not doing that.

It was not: at interior nodes it compared a *subtree* total against the
*full-round* threshold, ignoring banked points — precisely the shift-invariance
violation above. After threshold-indexing the memo, the ordering is restored
everywhere (69.4 ≥ 62.3, 87.8 ≥ 82.1, 59.1 ≥ 45.3).

**The general lesson:** an internal consistency check that *must* hold is worth
more than a plausible-looking output. The four algebraic checks passed
throughout; only a cross-policy comparison exposed this.

---

## 5. Why alpha-beta pruning is invalid here

A natural optimization for a game tree is alpha-beta pruning. It is **unsound
for this scoring function**, and this is worth proving because it is not obvious.

Alpha-beta is valid when a node's value depends only on the *extremum* of its
children, since a branch that cannot affect the extremum can be skipped. The
blend

$$
V = \alpha \min_i(c_i) + (1-\alpha)\,\text{mean}_i(c_i)
$$

depends on the **mean**, which depends on *every* child. Skipping any child
changes the value.

**Counterexample.** Children \([10, 2, 2, 2]\), \(\alpha = 0.8\):

$$
V = 0.8(2) + 0.2\!\left(\tfrac{10+2+2+2}{4}\right) = 1.6 + 0.8 = 2.4000
$$

Prune one child, leaving \([10, 2, 2]\):

$$
V' = 0.8(2) + 0.2\!\left(\tfrac{10+2+2}{3}\right) = 1.6 + 0.9333 = 2.5333
$$

A discrepancy of 0.1333 **at a single node**, which then compounds up the tree.
Pruning is sound only at \(\alpha = 1.0\), i.e. pure minimax.

> A note on method: my first attempt to prove this was a script that reported
> "0 of 40 differing at every alpha" — suspiciously clean. It was broken: the
> cutoff compared against \(-\infty\), so pruning never fired. The result above
> is from a direct worked calculation instead. A test that cannot fail is not
> evidence.

**What this means going forward.** The *floor* axis is a pure minimum, so it
**is** prunable — branch-and-bound on floor is valid. Expectation is not. Any
future search-space reduction must target the floor, or accept exact
enumeration.

---

## 6. Cost

Carrying a distribution sounds more expensive than carrying a number. Measured:

| computation | time |
|---|---|
| one scalar pass | 5.12 ms |
| **four scalar passes (what the app did)** | **20.49 ms** |
| one distribution pass | 9.66 ms |

A distribution costs 1.89× a *single* scalar pass, but the app never ran a
single pass — it ran four (`cumulative2`, `confidence2`, `resistance2`,
`strategic3`). Against the real baseline the distribution is **0.47×**, i.e.
roughly twice as fast, while producing strictly more information.

This is the crux: the four scalar metrics are four lossy projections of one
underlying distribution. Computing the distribution once and reading the
projections off it is both cheaper and more truthful.

For context, the surrounding engineering work reduced end-to-end 5v5 scoring
from **27,564 ms to ~975 ms** (~28×), and traversal from **47.3 full passes
over the tree to 1.0**.

---

## 7. What the numbers say about the existing system

This is the part I got wrong first, and the correction matters more than the
original claim.

**Initial (incorrect) finding.** With the buggy win-probability policy, the
engine appeared to beat the app's existing pick by a mean of **+15.5%** win
probability, including +18.0% on USA Bison. That number was an artifact of the
bug in §4.3 and is **withdrawn**.

**Corrected finding.** With the threshold-indexed policy, on three real
matchups:

| matchup | app's pick (`strategic3`) | best available | gap |
|---|---|---|---|
| USA Condor | 69.4% | 69.4% | **0.0%** |
| USA Jackrabbits | 87.5% | 87.8% | **0.2%** |
| USA Bison | 59.1% | 59.1% | **0.0%** |

**The existing "smart sort" is essentially optimal for win probability.** The
hand-built heuristic, with its three tuned constants, is picking the right
opener. That is a genuinely impressive result for a hand-derived system and it
should be stated as such.

Two further observations from the same table:

- **Maximizing expected points is measurably the wrong objective.** It achieves
  45.3% on Bison where win-probability play achieves 59.1%. Above the threshold
  extra points are worthless, and a policy that keeps chasing them takes bad
  risks. Notably, `strategic3` tracks win probability *better* than pure
  expected points does — the original design instinct was sound.
- **Maximizing the floor is also wrong**, in the other direction: 72.2% versus
  87.8% on Jackrabbits. Pure safety costs wins.

### 7.1 A correction to an earlier conclusion

An earlier document in this series (`DECISION_SENSITIVITY_FINDINGS.md`)
concluded that real rosters are "flat" — about 1 point of spread across 17.
That is true **in points** and misleading overall. The same decisions span
roughly 60 percentage points of win probability. The flatness was an artifact of
the points scale, and it is exactly the artifact that motivates reporting
probabilities instead of unitless scores.

---

## 8. What is actually gained

Given §7, the honest value of this rework is **not** better picks. It is:

1. **Interpretable units.** "69.4% to win" instead of "strategic3 = −121". The
   second number cannot be sanity-checked by a human; the first can.
2. **Risk information that was being discarded.** Floor, ceiling, standard
   deviation and the 10th percentile all come free from a distribution. Two
   openers with the same expectation can have very different downside, and the
   old scalar could not distinguish them.
3. **Fewer free parameters.** One interpretable \(\lambda\) replaces `alpha`,
   `k` and `u`.
4. **Falsifiability.** A predicted 69.4% can be checked against outcomes. A
   `strategic3` of −121 cannot be checked against anything.
5. **Speed** — about 2× on the scoring pass, as a side effect rather than the goal.
6. **Confirmation.** There is real value in a rigorous demonstration that the
   system you built by hand is already making near-optimal decisions.

---

## 9. Summary of results

| result | status |
|---|---|
| \(\tau = G(lo+hi)/2\) generalizes across 1-3 / 1-5 / 1-10 | proved, matches documented values |
| Accumulation = resolutions + forced final | proved by exact mean = 15.00 |
| \(\lambda \to \infty\) reproduces minimax | verified exactly, independent implementation |
| Alpha-beta invalid under the alpha-blend | proved by counterexample |
| Floor axis remains prunable | follows from it being a pure minimum |
| Expected value and floor are shift-invariant | proved; memo on state alone is optimal |
| Win probability is not shift-invariant | proved; found via an impossible measurement |
| Distribution is 0.47× the four-pass baseline | measured |
| Existing `strategic3` is near-optimal | measured; mean gap 0.07% |
| Earlier "+15.5% improvement" | **withdrawn — artifact of a bug** |
| Earlier "rosters are flat" | **qualified — artifact of the points scale** |

---

## 10. Open questions

1. **Can \(\lambda\) be fitted from data?** Every completed round is an
   observation of an opponent decision. With enough history, \(\lambda\) becomes
   measured rather than assumed — and could be per-opponent.
2. **A 60-state discrepancy.** The engine computes 5,332 states where the app's
   memo finds 5,392. The difference involves root `base` handling and is not yet
   explained. It is small, but unexplained is unexplained.
3. **Three matchups from one team** is a thin evidence base for §7. The
   conclusion that `strategic3` is near-optimal deserves a wider test before it
   is treated as settled.
4. **Branch-and-bound on the floor axis** is valid and unexploited.
