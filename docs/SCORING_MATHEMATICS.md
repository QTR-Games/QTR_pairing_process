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

> **Empirical correction (2026-08-24).** This section states one identity that
> does two different jobs, and only one of them survives contact with real data.
> See `WTC2024_GROUND_TRUTH.md` **Finding 12**, which compares Team Irving's grid
> against the opposing team's *own* preparation sheet for the same 25 matchups.
>
> - **As a statement about outcomes, it holds.** A game one side wins, the other
>   loses. The constant-sum identity above and the threshold \(\tau\) derived in
>   §1.4 depend only on this, and are unaffected. \(\tau\) is a threshold on
>   *our own* estimates and never required the opponent to agree with them.
> - **As a statement about the opponent's beliefs, it is false.** The engine uses
>   \(6-r\) to predict *what the opponent will choose* — i.e. it assumes their
>   grid is our grid reflected. Measured against the real opposing grid, the two
>   teams' views of the same 25 cells correlate at **r = −0.049**, with mean
>   absolute disagreement of 0.253 on a normalised 0–1 scale. The opponent
>   optimises against a board we cannot see, and it is not ours flipped.
>
> Consequence for this document: the adversarial treatment of opponent levels is
> still the right *modelling posture* — they do maximise, and their gain is our
> loss. What is **not** justified is inferring their preference ordering from our
> ratings. Everything in §3.4 that reasons about a mirrored opponent should be
> read as testing the *symmetry of a rule*, not as predicting real play.

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

### 3.4 The conservation test: measuring cooperation bias in points

The three checks above are internal — they compare the engine against other
things the engine believes. There is a stronger test available, because
§1.3 established that ratings are strictly zero-sum: the opponent's view of a
matchup is \(6 - r\), so across \(n\) games the two teams' round totals must
sum to exactly \(6n\). That is forced by the convention, not assumed.

So solve the **same game twice** — once from our seat, once from theirs, with
players swapped, every rating replaced by \(6-r\), and the "who chooses first"
flag inverted. Define

$$\text{excess} = V_{\text{us}} + V_{\text{them}} - 6n$$

A rule that neither flatters nor punishes us must give \(\text{excess}=0\).
A rule that lets each side assume the other cooperates makes **both** sides
overestimate, so the excess is positive — and it is denominated in tournament
points, which makes it interpretable rather than merely detectable.

> **Scope of this probe, after Finding 12.** The mirrored board constructed here
> is a *synthetic* opponent, generated by reflecting our own grid. Real opposing
> grids do not look like that (`WTC2024_GROUND_TRUTH.md` §Finding 12: r = −0.049
> against an actual opponent's sheet). That does **not** invalidate the probe —
> a mirrored board is exactly the right instrument for asking *"is this rule
> symmetric?"*, and asymmetry detected this way is a genuine property of the
> rule. But it bounds the conclusion: a conserving rule is symmetric, **not
> thereby unbiased in play.** The residual error against a real, independently
> estimating opponent is not measured by this probe and is not currently
> measured anywhere.

Measured on real event data (Team Irving 2024, six opponents, scenario 0,
\(n=5\), conserved total 30):

| rule | mean excess | min | max | reading |
|---|---|---|---|---|
| optimistic — `max()` at every level | **+1.667** | 0.000 | +4.000 | never below 0 |
| minimax — `min()` at their levels | **−1.833** | −3.000 | 0.000 | never above 0 |
| quantal — what the engine ships | **−0.181** | −1.040 | +1.089 | straddles 0 |

Two conclusions, and the second is the surprising one.

1. **The optimistic rule is provably biased.** It is what
   `tree_generator.calculate_all_path_values` does: `max()` over all children
   regardless of whose turn it is. Against England Dragons both sides conclude
   they will score 17 of a possible 30. On the synthetic 4v4 fixture the effect
   is starker still: both seats claim 16 points out of a possible 24, an excess
   of **+8.0**. (This function is *not* what the v2 sort column calls — see
   §3.4.1 below, which corrects an earlier claim in this document.)

2. **"Just flip `max` to `min`" is not the fix.** Pure minimax is wrong by
   about as much as pure optimism, in the opposite direction: both sides
   assume they will be held to their worst case, and both cannot be. Only the
   quantal rule straddles zero. This is the empirical justification for
   modelling opponent fallibility with \(\lambda\) rather than by assuming
   perfect adversarial play — and it was not obvious in advance.

The bias is a property of the *rule*, not of the data: the optimistic excess is
non-negative on every matchup tested, and the minimax excess non-positive on
every one. `test_zero_sum_conservation.py` pins **the optimistic half** of that
hermetically on a synthetic grid — weakly, then strictly on an uneven grid —
plus a guard that the mirror construction is faithful before any conclusion is
drawn from it, and a check that the quantal rule's conservation error is smaller
than the optimistic rule's. The minimax sign and all three real-data magnitudes
come from `probe_cumulative2_bias.py` against `teamIrving2024_FinalDB.db`, which
is deliberately not a test fixture; **no test exercises minimax.**

This does **not** close the wider p3c question. It establishes which rule is
self-consistent; whether the sort path should adopt it is a separate decision
that changes displayed scores and requires a reviewed re-baseline of the golden
master.

### 3.4.1 Correction — which rule the shipping sort column uses

An earlier revision of this document implied the `+1.667` optimism was the
number displayed in the v2 `cumulative` sort column. **That was wrong.**

`ui_manager_v2.py:5477` routes the `cumulative` sort mode to
`calculate_all_path_values_enhanced` — the `cumulative2` rule — not to
`calculate_all_path_values`. The pure-`max` function measured above is reachable
only from `ui_manager_v1_original.py:1095` and `golden_master_harness.py:33`.

`cumulative2` aggregates opponent levels with a blend
(`tree_generator.py:736-741`):

\[
V(s) \;=\; \text{base}(s) \;+\;
\begin{cases}
\alpha \cdot \min_{c} V(c) \;+\; (1-\alpha)\cdot \operatorname{mean}_{c} V(c) & \text{opponent chooses} \\[4pt]
\max_{c} V(c) & \text{we choose}
\end{cases}
\]

with \(\alpha = 0.80\) by default (`tree_generator.py:53`, preference key
`("cumulative2","alpha")`). Since \(\alpha=1\) is pure minimax and \(\alpha=0\)
is "the opponent moves at random", \(\alpha\) is a dial *between* the two biased
extremes — and conservation can locate the honest setting on it.

Sweeping \(\alpha\) over the same six real opponents (conserved total 30):

| \(\alpha\) | mean excess | min | max | reading |
|---|---|---|---|---|
| 0.00 | +0.554 | −0.640 | +1.813 | opponent moves at random |
| **0.20** | **+0.043** | −0.950 | +1.134 | **least biased on this data** |
| 0.40 | −0.455 | −1.242 | +0.818 | |
| 0.60 | −0.934 | −1.848 | +0.540 | |
| **0.80** | **−1.397** | −2.462 | +0.267 | **shipped default** |
| 1.00 | −1.833 | −3.000 | 0.000 | pure minimax |

Two consequences:

1. **The shipped sort column is pessimistically biased, not optimistically.** At
   \(\alpha=0.80\) its excess is **−1.397** — roughly three-quarters of the way
   to full minimax, the rule §3.4 shows is no more honest than optimism.
2. **\(\alpha\) is measurable, not hand-tuned.** Conservation supplies an
   empirical target of \(\alpha \approx 0.2\), moving the metric from −1.40 to
   +0.04 with no change to scoring logic — only to a preference already exposed
   at `database_preferences.py:149`. That this lands near the quantal engine's
   −0.181 is corroborating: two independently-derived rules agreeing near zero.

**Two caveats.** First, conservation is *necessary*, not *sufficient*: \(\alpha
= 0.2\) stops the model contradicting itself but does not prove it predicts real
opponents. Second, the shipped `cumulative2` accumulates `base` at every node
with no `contributes_to_total` filter, which is a separate known defect; the
sweep deliberately holds accumulation fixed so that only the propagation rule
varies, otherwise double-counting swamps the signal.

Reproduce with the α-sweep probe at
`C:\Users\Daniel.Raven\.copilot\session-state\b5a9a476-5975-467d-b251-0bbfeb2736b6\files\probe_cumulative2_bias.py`
(run from the repo root). The propagation-bias result it builds on is pinned
hermetically in-repo by `test_zero_sum_conservation.py`.

### 3.4.2 Decision — what happens to `cumulative` before the event

Asked to "drop this if prudent" and to decide rather than defer, the decision is
**leave the Python default at α = 0.80 and ship nothing**, because the metric has
already been dropped where it matters.

The reasoning, and the facts that constrain it:

1. **The phone app never had it.** `webapp/src` contains zero occurrences of
   `cumulative`. The React engine scores through `protocol.ts` and reports
   floor / guaranteed / ceiling. So the number that "always flatters" is absent
   from the tool that will actually be used at the event. Removing it from the
   Python app buys the event nothing.
2. **Changing the default is a re-baseline, not a bugfix.** The golden master's
   `enhanced_v3_scores` mode calls `calculate_all_path_values_enhanced`
   (`golden_master_harness.py:52`), which reads `cumulative2_alpha`. Moving the
   default therefore invalidates those fixtures *by design*. The Python app is
   the agreed stable fallback; destabilising it days before an event to fix a
   column the event will not use is the wrong trade.
3. **No code change is needed to get the honest number anyway.** α is a
   validated, clamped, persisted preference (`database_preferences.py:149`,
   validated at `:207`), read at `tree_generator.py:53`. Setting
   `strategic_preferences.cumulative2.alpha = 0.2` moves the metric from −1.40
   to +0.04 at runtime, per the sweep above, without touching code or fixtures.

**Correction to an earlier verbal claim.** This metric was previously described
in conversation as optimistic — "it always flatters, by ~1.7 points". That was
the wrong function. `+1.667` belongs to `calculate_all_path_values`, reachable
only from v1 and the golden-master harness (§3.4.1). The column actually
displayed in v2 is **pessimistic by −1.397**. The direction of the bias was
reported backwards, and the number quoted came from a different rule.

Revisit if the Python app outlives the phone app, in which case the change is
"set α = 0.2, re-baseline `enhanced_v3_scores`, review the diff" — a deliberate
maintenance task, not a hotfix.

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

The tree's 48,751 nodes collapse to **5,332 distinct game states** — a 9.1×
reduction, and memoizing on canonical state is provably optimal for the
shift-invariant objectives (misses equal distinct states exactly).

Two counts appear in earlier notes — 5,332 and 5,392 — and the difference is a
measurement artifact, not a defect. Enumerating `_canonical_key` over all 48,751
nodes yields 5,392; the engine's descent from the root computes 5,332. The
60-state gap is exactly the set of **presentation-order variants of offer
nodes**: `Vex vs Pulse (3/10) OR Rune (10/10)` and
`Vex vs Rune (10/10) OR Pulse (3/10)` are the same offer with the two options
listed in the opposite order, and the canonical key is not invariant to that
ordering. All 60 sit at depth 7 and span 720 nodes. The engine memoizes the
first ordering it encounters and skips the duplicate parent, so the reversed
children are never separately computed.

The collapse was verified rather than assumed, and the verified result is
narrower than "the two subtrees are identical." Across **both** the 4v4 and 5v5
scenarios and all three objectives, every affected parent state yields an
identical **objective value** (max gap \(0\)) — the quantity that drives ranking
and sorting is preserved exactly, which is what the memo needs.

The full distributions were *not* always identical. On 4v4 they differed by up to
0.26 (floor) and 0.73 (win probability); on 5v5 they happened to agree exactly.
The cause was tie-breaking: when two children tie on the objective,
`max(child_dists, key=...)` keeps the first in list order, so which
equally-good subtree survived depended on presentation order. The score was
unaffected by construction — tied means equal — but the displayed *spread*
shifted with the order an offer happened to be listed in.

**This is now fixed.** The comparison key is a pair,

$$\text{key}(d) = \bigl(\text{rank}(d),\; \text{pref}(d)\bigr), \qquad
\text{pref}(d) = \bigl(\max \operatorname{supp} d,\; \min \operatorname{supp} d,\;
\text{canonical}(d)\bigr)$$

so ties on \(\text{rank}\) are broken by a pure function of the distribution
rather than by sibling order. Among equally-ranked options the engine reports
the one with the **wider upside** first, then the **safer floor**, then a
canonical serialisation as a total-order backstop. Two consequences worth
stating plainly:

- The objective value is unchanged — the tie-break only runs when
  \(\text{rank}\) is already equal, so it can never override a ranking decision.
- The reported ceiling, floor and regret are now functions of the *decision*,
  not of the presentation. `test_distribution_tie_break_order.py` pins this by
  scoring the same tree with the children supplied in both orders; before the
  fix, one ordering reported a ceiling of 3 where the other reported 4.

Preferring upside on a tie is deliberate rather than arbitrary: when two lines
are genuinely equal on the objective, the one that keeps a better best case
alive is the one that preserves outs.

**5,332 is the true distinct-state count; 5,392 counts each order-variant twice.**

But for win probability, the canonical state is **not a sufficient key**. The
same state reached with 12 points banked versus 9 is a genuinely different
decision problem. The key must include the remaining requirement
\(N - c\). Measured on the same 5v5 scenario this widens the state space from
5,332 to **13,415** (collapse 9.1× → 3.6×) — a real cost, paid only by the
objective that needs it. The figure is threshold-invariant: raising or lowering
\(N\) shifts every \(need\) uniformly and does not change how many distinct
\((\text{state}, need)\) pairs exist (verified at \(N\) from 10 to 35).

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

> **Validated against a real tournament.** Sections 1–6 reason about the model
> from the inside. `docs/WTC2024_GROUND_TRUTH.md` checks it from the outside,
> against the 400 real games of Warmachine WTC 2024 joined to the 5,425 ratings
> Team Irving entered *before* that event. Three results there bear directly on
> the mathematics in this document:
>
> - **The scenario dimension is constant.** Across every real database ever
>   produced — 1,150 matchup cells — **zero** vary by scenario. Every
>   scenario-aware cost in §6 is a 7× multiplier over a constant.
> - **The rating is not a calibrated strength.** 74.1% of WTC ratings are the
>   single value `3`, the value `5` was never used once, and Irving won 70% of
>   games their own ratings implied they would win ~45% of. Every objective in
>   §2 treats the rating as calibrated. It is closer to an ordinal hint with a
>   pessimistic bias — so **absolute path totals are not meaningful quantities,
>   only comparisons between lines are.**
> - **The decisive game of the event was rated "dead even."** No search over
>   that grid could have flagged it, at any α, under any opponent model. This
>   bounds what §3 can achieve: with a near-uniform input matrix, a faithful
>   search correctly reports "no preference," and the honest output is to say
>   the grid is too flat to support a recommendation.

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

## 9.1 Using it

The engine is additive and **off by default**. It never writes `sort_value`, so
rankings are exactly what they were:

```powershell
$env:QTR_ENGINE = "model"   # required: the engine reads the Tk-free model tree
$env:QTR_RISK   = "1"       # adds P(win), Floor, P10 and sigma columns
$env:QTR_RISK_LAMBDA = "1.0"  # optional opponent rationality
python main.py
```

`QTR_RISK` silently stays off on the widget engine, mirroring how `QTR_RENDER=lazy`
already downgrades. With the flag off the projected values tuple is unchanged,
which is what keeps the golden-master digests byte-identical.

**Every figure is a round total, not a subtree total.** A node six games deep has
those games already banked, so its raw subtree distribution would report a floor
of 2 for a round that cannot finish below 14. Each node's distribution is shifted
by the points banked above it before display. Sigma needs no such correction --
it is shift-invariant.

---

## 10. Open questions

1. **Can \(\lambda\) be fitted from data?** Every completed round is an
   observation of an opponent decision. With enough history, \(\lambda\) becomes
   measured rather than assumed — and could be per-opponent. §3.4 sharpens this:
   the conservation excess gives an objective loss function to fit \(\lambda\)
   against, since the true \(\lambda\) should drive the excess to zero.
2. **Three matchups from one team** is a thin evidence base for §7. The
   conclusion that `strategic3` is near-optimal deserves a wider test before it
   is treated as settled. (§3.4 now uses six matchups, but for a different
   question.)
3. **Branch-and-bound on the floor axis** is valid and unexploited.
4. **Should the sort path adopt the conserving rule?** §3.4 measures the
   `cumulative` metric's cooperation bias at +1.67 points on real data. What it
   does *not* settle is whether to change it: doing so alters displayed scores
   and requires a reviewed re-baseline of the golden master. The measurement is
   done; the decision is deliberately not.
5. ~~**Separating "my choice" from "their response."**~~ **Answered — see §11.3
   and `DECISION_SENSITIVITY_FINDINGS.md` Finding 7.** Measured on 31 real
   boards: their reply is worth ~2.6x our opening choice, and our choice is
   worth *exactly zero* on 16 of 31 boards. The remaining open part is whether
   the same ratio holds at later decisions, not at the opening.

---

## 11. The protocol engine (mobile)

Sections 1-10 describe the desktop engine, which scores by enumerating
assignments. `webapp/src/engine/` takes a different route, and the difference is
mathematical rather than cosmetic.

### 11.1 Why the assignment bound is loose

The desktop floor minimises over **every perfect assignment** of our five
players to theirs. That is safe, but many of those assignments are unreachable:
WTC pairing is a turn-taking game, not a free choice of permutation. Bounding
over outcomes that cannot occur understates what we can guarantee.

`protocol.ts` plays the actual game instead. Two distinct decisions exist at
each step and **they belong to different sides**:

1. which pair to offer — the defending side's decision
2. which of the pair plays — the attacking side's decision

The player offered but not picked is then put forward by their own side. That
leftover rule is what makes a *bus* possible: a side can offer a pair knowing
that whichever one is declined dictates the following matchup. It is the
mechanic Team Irving lost to in 2024, and an assignment-based bound cannot
represent it at all, because it has no notion of turn order.

Exact minimax over that structure gives `protocolFloor`, which is **tighter
than the assignment floor and strictly more honest than assuming cooperation**.

### 11.2 The opponent model, and what it does not claim

Finding 12 measured the correlation between two teams' ratings of the same 25
matchups at **r = -0.049**. The mirror axiom — that their grid is ours
reflected — is false. We therefore cannot infer which matchups they *want*.

So the engine does not try. The opponent minimises **our** total on **our own**
numbers. This is deliberately not a claim about their preferences; it is a
bound. Whatever they are really optimising, they cannot do worse to us than the
worst that can be done to us. `protocolFloor` therefore survives not knowing
their grid at all — which is the only property worth having, given r ≈ 0.

### 11.3 The opportunity profile

Minimax alone ties constantly, because their best reply caps our options
equally: **28 of 31 real boards** open with two or more choices scoring
identically, and §11.3's companion measurement shows our opening choice is
worth *exactly zero* on 16 of them. A single number has nothing left to say,
and "it is a coin flip" is not advice anyone can act on at a table.

The tie is an artifact of asking one statistic to carry more than it can. For
each of our options, `optionProfile` examines **every reply they have**:

| quantity | meaning |
|---|---|
| `guaranteed` | what we hold if they answer perfectly (the minimax value) |
| `ifTheyErr` | what their *worst* reply gives us |
| `punishingReplies` | how many of their replies actually hold us to the floor |
| `upside` | `ifTheyErr − guaranteed` |

`punishingReplies` is the load-bearing one: **one reply in ten is a completely
different proposition from three in ten**, though minimax scores them alike.
This separates **24 of the 28** tied boards.

Ranking is **value-first**: upside never buys a lower floor. The profile only
ever reorders options that were already tied, so it cannot trade away a
guarantee in pursuit of a gamble.

### 11.4 Choice versus response

Measuring the two halves of a decision separately, in round points on the same
board (`measure.decompose.test.ts`, 31 boards):

| | mean | median | max |
|---|---|---|---|
| our opening choice | 0.48 | **0.00** | 1.0 |
| their reply | 1.26 | 1.00 | 2.0 |

Their reply outweighs our choice on 20 of 31 boards, and our choice is worth
nothing at all on 16 of 31.

The consequence is structural, not incremental: **ranking openings cannot be
the product**, because on the median board there is nothing to rank. What
remains actionable is the error surface — how much upside is on the table and
how many of their replies remove it. That is the profile in §11.3, and this
measurement is an independent argument for it, reached from the opposite
direction.

### 11.5 Summary

| result | status |
|---|---|
| Protocol floor is tighter than the assignment floor | proved by construction; the assignment bound includes unreachable outcomes |
| Mirror axiom is false | measured, r = -0.049 on 25 shared matchups |
| Opponent bound survives unknown opponent grids | follows from minimising our total, not modelling theirs |
| Top openers tie | measured, 28/31 real boards |
| Opportunity profile separates ties | measured, 24/28 |
| Their reply outweighs our choice | measured, 2.6x mean, dominates on 20/31 |
| Our opening choice is worth zero | measured, 16/31 boards |
