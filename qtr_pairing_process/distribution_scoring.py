"""Distribution-propagation scoring.

The existing scores collapse a subtree to a single number via
``alpha * min(children) + (1 - alpha) * mean(children)``. That number is a
blend no opponent behaviour actually produces, its ``mean`` term makes
alpha-beta pruning mathematically invalid, and it is measured in points --
a scale that compresses badly near a win threshold.

This module propagates the whole *distribution over final round totals*
instead. From one traversal you can read floor, ceiling, expected value,
variance, win probability and any quantile, so the four separate scalar
passes collapse into one.

It also replaces three hand-tuned constants (``cumulative2_alpha``,
``confidence2_k``, ``confidence2_u``) with a single parameter that has a
real-world meaning: ``lam``, the opponent's rationality.

    lam -> infinity : opponent always makes their best move (pure minimax)
    lam == 0        : opponent picks uniformly at random
    lam ~ 1         : opponent is good but fallible

Unlike the constants it replaces, ``lam`` is calibratable -- fit it to
recorded opponent choices.

Nothing here touches Tk, and nothing here changes existing scores. This is
an additional, opt-in axis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# A distribution is a mapping {final_total: probability}. Support stays small
# because totals are bounded integers: for N games on a lo-hi rating scale the
# support can never exceed N * (hi - lo) + 1 distinct values.
Distribution = dict


def win_threshold(rating_range: tuple[int, int], games: int) -> float:
    """Total you must EXCEED to win the round.

    Ratings are symmetric: a matchup you rate ``r`` the opponent rates
    ``lo + hi - r``, so the two teams' totals always sum to
    ``games * (lo + hi)``. Half of that is the dead-even line.

    This matches every rating system the app ships, whose own documented
    "even" value is exactly the midpoint of its range: 1-3 -> 2, 1-5 -> 3,
    1-10 -> 5.5. For the standard 1-5 system over 5 games the threshold is
    15.0, so 16+ wins.
    """
    lo, hi = rating_range
    return games * (lo + hi) / 2.0


def contributes_to_total(node) -> bool:
    """Does this node's ``base`` count toward the final round total?

    The tree alternates two kinds of node along every path::

        depth 1  Dan vs JVM (3/5) OR Brandon (4/5)   <- an OFFER
        depth 2  JVM rating 3                        <- the RESOLUTION
        depth 3  Brandon vs Bokur (3/5) OR Kyle (3/5)
        depth 4  Bokur rating 3
        ...
        depth 9  Jack vs Justin (4/5) OR Justin (4/5)  <- forced final game

    Only resolutions are played games. An offer states what is on the table;
    the resolution says what actually happened. The final pairing is forced
    (both options are the same player), so it resolves itself and is counted
    directly.

    Summing every node instead double-counts each game -- an error that
    inflated round totals from ~15 to ~28 and made every opener look like a
    guaranteed win.

    Verified by an invariant: with complementary ratings the two teams' totals
    always sum to ``games * (lo + hi)``, and the leaf set is closed under
    complement, so the mean total across all leaves must be exactly half that.
    Only this rule yields 15.00 on the 1-5 five-game data; summing all nodes
    yields 28.64.
    """
    explicit = getattr(node, "counts_toward_total", None)
    if explicit is not None:
        return bool(explicit)
    if not node.children:
        return True
    return " rating " in str(node.text)


def prob_at_least(dist: Distribution, need: int) -> float:
    """P(total >= need).

    Totals are integers, so a strict threshold like "win if total > 15.0"
    is exactly "win if total >= 16". Working in integers keeps the choice
    rule free of floating-point boundary cases.
    """
    return sum(p for v, p in dist.items() if v >= need)


def point_mass(value: int) -> Distribution:
    return {value: 1.0}


def shift(dist: Distribution, offset: int) -> Distribution:
    """Add a fixed contribution to every outcome."""
    if not offset:
        return dict(dist)
    return {value + offset: prob for value, prob in dist.items()}


def mix(dists: list[Distribution], weights: list[float]) -> Distribution:
    """Weighted mixture -- used where the opponent chooses.

    The opponent's move is uncertain, so the outcome is a genuine mixture
    over what they might do, not a single collapsed number.
    """
    total_weight = sum(weights)
    if total_weight <= 0.0:
        weights = [1.0] * len(dists)
        total_weight = float(len(dists))
    merged: Distribution = {}
    for dist, weight in zip(dists, weights, strict=False):
        if weight <= 0.0:
            continue
        scale = weight / total_weight
        for value, prob in dist.items():
            merged[value] = merged.get(value, 0.0) + prob * scale
    return merged


def softmax(values: list[float], lam: float) -> list[float]:
    """Quantal-response weights: P(choice) proportional to exp(lam * value).

    Overflow-safe via the standard max-subtraction trick. ``lam <= 0`` gives
    a uniform (coin-flip) opponent; large ``lam`` approaches pure argmax.
    """
    if not values:
        return []
    if lam <= 0.0:
        return [1.0] * len(values)
    largest = max(values)
    exps = [math.exp(lam * (value - largest)) for value in values]
    total = sum(exps)
    if total <= 0.0:
        return [1.0] * len(values)
    return [e / total for e in exps]


@dataclass(frozen=True)
class Outcome:
    """Summary statistics of a distribution over final totals.

    Every field below comes from the SAME traversal. Under the current
    scheme each would need its own pass, and ``conservative`` would be a
    Gaussian approximation rather than an actual quantile.
    """

    dist: Distribution
    threshold: float

    @property
    def floor(self) -> int:
        """Worst reachable total. This axis IS safely alpha-beta prunable."""
        return min(self.dist)

    @property
    def ceiling(self) -> int:
        return max(self.dist)

    @property
    def expected(self) -> float:
        return sum(value * prob for value, prob in self.dist.items())

    @property
    def variance(self) -> float:
        mean = self.expected
        return sum(prob * (value - mean) ** 2 for value, prob in self.dist.items())

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)

    @property
    def win_probability(self) -> float:
        """Probability of finishing strictly above the dead-even line.

        This is the quantity points systematically hides: near a threshold,
        large swings in win probability can correspond to fractions of a
        point.
        """
        return sum(p for value, p in self.dist.items() if value > self.threshold)

    @property
    def regret(self) -> int:
        """Ceiling minus floor -- the spread the current code approximates."""
        return self.ceiling - self.floor

    def quantile(self, q: float) -> int:
        """Exact quantile, replacing the ``mu - k*sigma`` normal approximation."""
        cumulative = 0.0
        last = self.floor
        for value in sorted(self.dist):
            cumulative += self.dist[value]
            last = value
            if cumulative >= q:
                return value
        return last

    def summary(self) -> dict[str, float]:
        return {
            "floor": self.floor,
            "ceiling": self.ceiling,
            "expected": self.expected,
            "std": self.std,
            "win_probability": self.win_probability,
            "regret": self.regret,
            "p10": self.quantile(0.10),
        }


class DistributionScorer:
    """Propagate outcome distributions bottom-up over an existing tree.

    Deliberately walks the tree the app already builds rather than
    re-deriving the game, so the game semantics cannot drift from the rest
    of the application.

    Memoized on canonical game state, which is what makes this affordable:
    at 5v5 the 48,751-node tree contains only 5,392 distinct states.
    """

    def __init__(
        self,
        threshold: float,
        lam: float = 1.0,
        objective: str = "win_probability",
    ) -> None:
        if objective not in ("win_probability", "expected", "floor"):
            raise ValueError(f"unknown objective: {objective!r}")
        self.threshold = threshold
        # Smallest integer total that wins. "total > 15.0" means "total >= 16";
        # "total > 27.5" means "total >= 28". floor()+1 covers both.
        self.win_need = int(math.floor(threshold)) + 1
        self.lam = lam
        self.objective = objective
        self._memo: dict[tuple, Distribution] = {}
        self.states_computed = 0
        self.memo_hits = 0

    def _canonical_key(self, node) -> tuple:
        return (
            node.state_attacker,
            node.state_attacker_side,
            node.state_choosing_side,
            node.state_our_pool,
            node.state_opponent_pool,
            node.state_choice_pool,
            str(node.text),
            0 if node.parent is None else int(node.base),
        )

    def _rank(self, dist: Distribution, need: int | None) -> float:
        """Value we attribute to a distribution when a side must choose.

        ``need`` is the smallest subtree total that still wins the round given
        the points already banked above this node. It matters only for the
        win-probability objective -- see ``distribution_for``.
        """
        if self.objective == "win_probability":
            assert need is not None
            return prob_at_least(dist, need)
        if self.objective == "floor":
            return float(min(dist))
        return sum(v * p for v, p in dist.items())

    def distribution_for(self, node, need: int | None = None) -> Distribution:
        """Distribution of subtree totals reachable from ``node``.

        Iterative post-order: the tree is ~200 levels deep at 5v5 and
        Python's recursion limit is 1000 by default, so recursion is a
        latent crash on larger scenarios.

        Shift-invariance and why the memo key differs by objective
        ----------------------------------------------------------
        A node contributes ``own`` points, so a parent's distribution is its
        child's shifted by ``own``. For choosing a child that shift matters
        only if the objective is sensitive to it:

        * expected value -- ``argmax E[X + c] == argmax E[X]``: shift-invariant
        * floor          -- ``argmax min(X + c) == argmax min(X)``: shift-invariant
        * win probability -- ``argmax P(X + c > T) == argmax P(X > T - c)``,
          which DOES depend on ``c``

        So for expected and floor the canonical game state is a sufficient
        memo key and the full 9.1x state collapse applies. For win probability
        it is NOT: the same state reached with a different number of banked
        points is a genuinely different decision problem, and the key must
        include the remaining requirement.

        Getting this wrong is not academic. Keying win probability on state
        alone compares a partial subtree total against the full-round
        threshold, which produced a policy that lost to the expected-points
        policy at its own objective (80.9% vs 82.1% on USA Jackrabbits) -- an
        impossibility that is only explicable as a bug.
        """
        if need is None:
            need = self.win_need

        def memo_key(n, nd: int) -> tuple:
            state = self._canonical_key(n)
            # Only the win-probability objective is shift-sensitive, so only
            # it pays the price of a wider key.
            return (state, nd) if self.objective == "win_probability" else state

        root_key = memo_key(node, need)
        cached = self._memo.get(root_key)
        if cached is not None:
            self.memo_hits += 1
            return cached

        stack = [(node, need, False)]
        while stack:
            current, cur_need, children_done = stack.pop()
            current_key = memo_key(current, cur_need)

            if current_key in self._memo:
                continue

            # Offer nodes announce what is on the table; resolution nodes record
            # what was actually played. Counting both double-counts every game.
            if current.parent is None or not contributes_to_total(current):
                own = 0
            else:
                own = int(getattr(current, "base_for_our_team", current.base))
            child_need = cur_need - own

            if not children_done:
                stack.append((current, cur_need, True))
                for child in current.children:
                    if memo_key(child, child_need) not in self._memo:
                        stack.append((child, child_need, False))
                continue

            if not current.children:
                self._memo[current_key] = point_mass(own)
                self.states_computed += 1
                continue

            child_dists = [
                self._memo[memo_key(c, child_need)] for c in current.children
            ]

            if current.children[0].is_opponent_choice:
                # The opponent moves next. They are trying to hold our total
                # DOWN, so their preference is the negation of our ranking,
                # and their fallibility is captured by lam rather than by an
                # arbitrary blend between min and mean.
                ranks = [-self._rank(d, child_need) for d in child_dists]
                combined = mix(child_dists, softmax(ranks, self.lam))
            else:
                # We move next, and we get to actually choose. No blending:
                # we take the child we would really pick.
                best = max(child_dists, key=lambda d: self._rank(d, child_need))
                combined = dict(best)

            self._memo[current_key] = shift(combined, own)
            self.states_computed += 1

        return self._memo[root_key]

    def outcome_for(self, node) -> Outcome:
        return Outcome(self.distribution_for(node), self.threshold)

    def opener_report(self, root) -> list[tuple[str, Outcome]]:
        """Rank the top-level choices -- the decision the user actually makes.

        The root itself banks no points (see ``distribution_for``), so an
        opener's own subtree total is the whole round total and the ranking
        threshold is simply ``win_need``. Passing it explicitly matters: the
        win-probability objective is not shift-invariant, so ``_rank`` cannot
        be called without a threshold.
        """
        report = [(str(child.text), self.outcome_for(child)) for child in root.children]
        report.sort(key=lambda pair: -self._rank(pair[1].dist, self.win_need))
        return report


def annotate_risk(root, scorer: DistributionScorer) -> int:
    """Write per-node risk figures onto an existing model tree.

    Returns the number of annotated nodes.

    Reported in ROUND totals, not subtree totals
    -------------------------------------------
    ``distribution_for`` returns the distribution of the total accumulated
    *from this node downward*. Displaying that raw would be misleading: a node
    six games deep would show a floor of 2 even though six games are already
    banked above it.

    So each node's distribution is shifted by the points banked on the way to
    it (``win_need - need``), turning it into a distribution over final round
    totals. Every figure is then directly comparable across depths and reads
    as "if play reaches here, this is how the round ends".

    Standard deviation needs no adjustment -- it is shift-invariant.
    """
    if root is None:
        return 0

    annotated = 0
    stack = [(root, scorer.win_need)]
    while stack:
        node, need = stack.pop()

        if node.parent is not None:
            dist = scorer.distribution_for(node, need)
            banked = scorer.win_need - need
            outcome = Outcome(shift(dist, banked), scorer.threshold)
            node.risk_win_prob = outcome.win_probability
            node.risk_floor = outcome.floor
            node.risk_p10 = outcome.quantile(0.10)
            node.risk_std = outcome.std
            annotated += 1

        own = 0
        if node.parent is not None and contributes_to_total(node):
            # Must match distribution_for's accumulation exactly. The generator
            # stores the OPPONENT's rating in `base` for opponent-side
            # resolutions and the complement in `base_for_our_team`; banking
            # raw `base` here would shift 41.8% of contributing nodes into the
            # wrong perspective (max observed error 18 points on 1-10 5v5).
            own = int(getattr(node, "base_for_our_team", node.base))
        child_need = need - own
        for child in node.children:
            stack.append((child, child_need))

    return annotated
