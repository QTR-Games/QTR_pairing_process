"""Small-sample interval estimates.

Wilson rather than the normal approximation, because the normal approximation
is actively misleading at the sample sizes this package deals with: at n = 20 it
can produce bounds outside [0, 1], and at k = 0 or k = n it collapses to a
zero-width interval, which would report certainty from the least informative
data possible.
"""

from __future__ import annotations

from math import sqrt

__all__ = ["wilson_interval", "Z_95"]

#: Two-sided 95% normal quantile.
Z_95 = 1.959963985


def wilson_interval(successes: int, trials: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    ``trials == 0`` returns ``(0.0, 1.0)`` -- the honest statement that no
    observation constrains the proportion at all. It is deliberately not an
    error, because "we have no evaluable decisions" is a result this package
    expects to report rather than an exceptional condition.
    """
    if trials < 0:
        raise ValueError(f"trials must be non-negative, got {trials}")
    if not 0 <= successes <= trials:
        raise ValueError(f"successes {successes} out of range for {trials} trials")
    if trials == 0:
        return (0.0, 1.0)

    p = successes / trials
    denom = 1.0 + z * z / trials
    centre = p + z * z / (2.0 * trials)
    margin = z * sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
    return ((centre - margin) / denom, (centre + margin) / denom)
