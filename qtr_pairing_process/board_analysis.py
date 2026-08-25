"""Board-level outlook: what is guaranteed, what is reachable, what is at stake.

Motivation
----------
The engine has always scored a pairing decision with a single number derived
from how good the board *can* be. Measured against real event data that number
ties across candidate decisions on 100% of boards, because it reports the same
ceiling for many different choices (``docs/WTC2024_GROUND_TRUTH.md``, Finding
13). What separates those choices is the **floor** -- how bad the round can
still become once the decision is made.

Two facts from WTC 2024 motivate the design:

* **Finding 12** -- the opponent does not rate the board as your ratings
  mirrored. Two teams' views of the same 25 matchups correlated at r = -0.049.
  So we cannot predict *which* assignment they will steer toward.
* **Finding 13** -- they do, however, optimise. The opposing team achieved the
  single best assignment available to them out of all 120.

Together those say: model the opponent as an optimiser whose objective you
cannot see. The defensible response is not prediction but a **guarantee**. The
floor computed here is a hard lower bound on your round total over every
completion of the board. It holds regardless of the pairing protocol, and
regardless of what the opponent believes, because it minimises over *all*
remaining assignments -- a superset of those any protocol can actually reach.

That makes the floor conservative by construction: the true worst case under a
specific protocol is never lower, and may be higher. It is a floor you are
guaranteed to clear, not a prediction of where you will land.

Terminology
-----------
floor
    Worst round total over every completion. Guaranteed.
ceiling
    Best round total over every completion. Requires the opponent to cooperate.
spread
    ``ceiling - floor``. How much the remaining pairing decisions are worth at
    all. A spread of zero means the round is already determined.
tau
    The dead-even line, ``games * (rating_min + rating_max) / 2``. Derived in
    ``docs/SCORING_MATHEMATICS.md`` section 1.4. A round is won strictly above it.

Both extremes are exact solutions of a linear assignment problem, solved with
the Kuhn-Munkres/Jonker-Volgenant O(n^3) method. No third-party dependency.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "Outlook",
    "CellChoice",
    "DecisionReport",
    "even_threshold",
    "assignment_extremes",
    "board_outlook",
    "cell_outlooks",
    "decision_report",
]

Matrix = Sequence[Sequence[float]]

UNWINNABLE = "unwinnable"
SECURED = "secured"
LIVE = "live"


def even_threshold(games: int, rating_min: float = 1.0, rating_max: float = 5.0) -> float:
    """The dead-even line for a round of ``games`` games on the given scale.

    Scale-independent: a 1-5 board and a 0-100 board both resolve correctly,
    which is what lets the app offer several rating systems over one engine.
    """
    if games < 0:
        raise ValueError("games must be non-negative")
    return games * (rating_min + rating_max) / 2.0


def _hungarian_min(cost: Matrix) -> tuple[float, list[int]]:
    """Minimum-cost perfect assignment. Returns (total, col_for_row).

    Standard O(n^3) shortest-augmenting-path formulation with potentials.
    Rows must not outnumber columns.
    """
    n = len(cost)
    if n == 0:
        return 0.0, []
    m = len(cost[0])
    if n > m:
        raise ValueError("assignment needs at least as many columns as rows")

    inf = float("inf")
    u = [0.0] * (n + 1)
    v = [0.0] * (m + 1)
    p = [0] * (m + 1)
    way = [0] * (m + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [inf] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = inf
            j1 = 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1

    col_for_row = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            col_for_row[p[j] - 1] = j - 1
    total = sum(cost[i][col_for_row[i]] for i in range(n))
    return total, col_for_row


def assignment_extremes(matrix: Matrix) -> tuple[float, float]:
    """Exact (floor, ceiling) over every perfect assignment of ``matrix``."""
    if not matrix:
        return 0.0, 0.0
    lo, _ = _hungarian_min(matrix)
    hi, _ = _hungarian_min([[-x for x in row] for row in matrix])
    return lo, -hi


@dataclass(frozen=True)
class Outlook:
    """What is guaranteed, what is reachable, and whether the round is live."""

    floor: float
    ceiling: float
    tau: float

    @property
    def spread(self) -> float:
        """How much the remaining pairing decisions can move the result."""
        return self.ceiling - self.floor

    @property
    def floor_margin(self) -> float:
        """Guaranteed margin over the dead-even line. Negative means at risk."""
        return self.floor - self.tau

    @property
    def ceiling_margin(self) -> float:
        """Best reachable margin. Negative means the round cannot be won."""
        return self.ceiling - self.tau

    @property
    def verdict(self) -> str:
        if self.ceiling <= self.tau:
            return UNWINNABLE
        if self.floor > self.tau:
            return SECURED
        return LIVE

    @property
    def is_decided(self) -> bool:
        """True when no remaining pairing decision can change the outcome."""
        return self.verdict != LIVE


def board_outlook(matrix: Matrix, tau: float, committed: float = 0.0) -> Outlook:
    """Outlook for a board, optionally with ``committed`` points already banked.

    ``matrix[i][j]`` is our rating for our player *i* against their player *j*,
    higher being better for us. ``committed`` carries the value of pairings that
    are already locked in, so partial boards work without reshaping the caller's
    data.
    """
    lo, hi = assignment_extremes(matrix)
    return Outlook(floor=lo + committed, ceiling=hi + committed, tau=tau)


def _submatrix(matrix: Matrix, drop_row: int, drop_col: int) -> list[list[float]]:
    return [
        [value for j, value in enumerate(row) if j != drop_col]
        for i, row in enumerate(matrix)
        if i != drop_row
    ]


def cell_outlooks(
    matrix: Matrix, tau: float, committed: float = 0.0
) -> dict[tuple[int, int], Outlook]:
    """Outlook for every individual pairing, assuming that pairing is taken.

    The key is ``(our_index, their_index)``. Each value answers: *if this
    matchup happens, what is then guaranteed and what is still reachable?*
    """
    result: dict[tuple[int, int], Outlook] = {}
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            rest = _submatrix(matrix, i, j)
            result[(i, j)] = board_outlook(rest, tau, committed + value)
    return result


@dataclass(frozen=True)
class CellChoice:
    """One candidate pairing, with the outlook that follows from taking it."""

    ours: int
    theirs: int
    value: float
    outlook: Outlook

    def dominates(self, other: CellChoice) -> bool:
        """At least as good on both bounds, and strictly better on one."""
        at_least = (
            self.outlook.floor >= other.outlook.floor
            and self.outlook.ceiling >= other.outlook.ceiling
        )
        strictly = (
            self.outlook.floor > other.outlook.floor or self.outlook.ceiling > other.outlook.ceiling
        )
        return at_least and strictly


@dataclass(frozen=True)
class DecisionReport:
    """The safe choice, the opportunistic choice, and what separates them.

    Measured across 31 real event boards, 89% of candidate pairings are
    *strictly dominated* -- another pairing is at least as good on both bounds
    and better on one. A metric that reports only the ceiling cannot see this,
    and rates a dominated choice identically to the one that dominates it.
    """

    board: Outlook
    safest: CellChoice
    boldest: CellChoice
    frontier: tuple[CellChoice, ...]
    hidden_floor_cost: float

    @property
    def choice_matters(self) -> bool:
        """True when protecting the floor genuinely costs ceiling.

        False means a single pairing dominates: it is the safest *and* the most
        opportunistic, so taking it gives up nothing. That is the common case
        (30 of 31 real boards), and it is precisely the case a ceiling-only
        metric cannot distinguish from giving away several points of floor.
        """
        return len({(c.outlook.floor, c.outlook.ceiling) for c in self.frontier}) > 1

    @property
    def floor_at_stake(self) -> float:
        """Guaranteed points given up by taking the bold choice over the safe one."""
        return self.safest.outlook.floor - self.boldest.outlook.floor

    @property
    def ceiling_at_stake(self) -> float:
        """Upside given up by taking the safe choice over the bold one."""
        return self.boldest.outlook.ceiling - self.safest.outlook.ceiling


def decision_report(matrix: Matrix, tau: float, committed: float = 0.0) -> DecisionReport:
    """Rank pairings by guaranteed floor and by reachable ceiling.

    ``hidden_floor_cost`` is the headline number: among the pairings that a
    ceiling-only metric rates as equally good, it is the spread in guaranteed
    floor between the best and the worst of them. On real boards this averages
    2.39 points and is never zero.

    Ties are broken deterministically -- by the opposite bound, then by index --
    so the recommendation never depends on the order candidates are presented in.
    """
    if not matrix or not matrix[0]:
        raise ValueError("decision_report needs a non-empty board")

    cells = [
        CellChoice(ours=i, theirs=j, value=matrix[i][j], outlook=o)
        for (i, j), o in cell_outlooks(matrix, tau, committed).items()
    ]
    safest = max(cells, key=lambda c: (c.outlook.floor, c.outlook.ceiling, -c.ours, -c.theirs))
    boldest = max(cells, key=lambda c: (c.outlook.ceiling, c.outlook.floor, -c.ours, -c.theirs))

    frontier = tuple(
        sorted(
            (c for c in cells if not any(o.dominates(c) for o in cells)),
            key=lambda c: (-c.outlook.floor, -c.outlook.ceiling, c.ours, c.theirs),
        )
    )

    best_ceiling = max(c.outlook.ceiling for c in cells)
    tied_on_ceiling = [c for c in cells if c.outlook.ceiling == best_ceiling]
    hidden = max(c.outlook.floor for c in tied_on_ceiling) - min(
        c.outlook.floor for c in tied_on_ceiling
    )

    return DecisionReport(
        board=board_outlook(matrix, tau, committed),
        safest=safest,
        boldest=boldest,
        frontier=frontier,
        hidden_floor_cost=hidden,
    )
