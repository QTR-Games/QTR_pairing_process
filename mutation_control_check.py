"""Mutation controls: break each guarded invariant, confirm the test fails.

A test that has never been seen to fail is not evidence that anything is
guarded. Every test added alongside the opponent-model layer has an entry here,
and each entry was run and observed to fail before the test was trusted.

    python mutation_control_check.py

WARNING: this rewrites source files in place while it runs. It restores each
file in a ``finally`` and asserts the restored content matches byte for byte,
but if the process is killed mid-run, check ``git status`` before committing.

Two findings came out of building this, both recorded because the failures were
not what they looked like:

* Three mutations first reported "not guarded" and only one of them really was.
  ``min``->``max`` and ``0.80``->``0.50`` preserve file size, and CPython keys
  its bytecode cache on (mtime seconds, size), so a same-size edit written
  inside the same second was served from a stale ``.pyc`` and never ran. Hence
  ``-B``, ``PYTHONDONTWRITEBYTECODE`` and ``_purge_pycache``.
* The genuinely unguarded one was ``SoftenedMirror.__init__``'s default alpha:
  every test constructed it with an explicit value, so the default itself was
  free to change. That hole is now closed.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

MUTATIONS = [
    (
        "SOFT DODGE weight -10 -> -9",
        "qtr_pairing_process/opponent_models.py",
        "soft: float = -10.0",
        "soft: float = -9.0",
        "test_opponent_corpus.py",
    ),
    (
        "HARD DODGE silently scored as 0 instead of refused",
        "qtr_pairing_process/opponent_models.py",
        'if label == HARD_DODGE:\n            raise UnidentifiedLabel(',
        'if label == HARD_DODGE:\n            return 0.0\n        if False:\n            raise UnidentifiedLabel(',
        "test_opponent_models.py test_opponent_corpus.py",
    ),
    (
        "Wilson replaced by the normal approximation",
        "qtr_pairing_process/opponent_comparison/stats.py",
        "    p = successes / trials\n    denom = 1.0 + z * z / trials",
        "    p = successes / trials\n    _h = z * (p * (1.0 - p) / trials) ** 0.5\n    return (p - _h, p + _h)\n    denom = 1.0 + z * z / trials",
        "test_opponent_backtest.py",
    ),
    (
        "adversarial verdict inverted",
        "qtr_pairing_process/opponent_comparison/corpus.py",
        'return self.verdict == "strongest_line"',
        'return self.verdict == "slipped"',
        "test_opponent_backtest.py",
    ),
    (
        "forced decision left in the denominator",
        "qtr_pairing_process/opponent_comparison/backtest.py",
        "    for decision in corpus.opponent_decisions:\n        if decision.forced:\n            result.not_evaluable[\"forced: not a choice\"] = (\n                result.not_evaluable.get(\"forced: not a choice\", 0) + 1\n            )\n            continue\n        result.evaluable += 1",
        "    for decision in corpus.opponent_decisions:\n        result.evaluable += 1",
        "test_opponent_backtest.py",
    ),
    (
        "confidence guard made a no-op",
        "qtr_pairing_process/opponent_comparison/report.py",
        "    text = repr(payload).lower()",
        "    return\n    text = repr(payload).lower()",
        "test_opponent_backtest.py",
    ),
    (
        "SoftenedMirror default alpha 0.80 -> 0.50",
        "qtr_pairing_process/opponent_models.py",
        "def __init__(self, alpha: float = 0.80) -> None:",
        "def __init__(self, alpha: float = 0.50) -> None:",
        "test_opponent_models.py",
    ),
    (
        "HardMirror returns max instead of min",
        "qtr_pairing_process/opponent_models.py",
        "    def combine(self, child_scores: Sequence[float]) -> float:\n        return min(child_scores)",
        "    def combine(self, child_scores: Sequence[float]) -> float:\n        return max(child_scores)",
        "test_opponent_models.py",
    ),
    (
        "RivalLabelUtility.combine stops refusing ratings",
        "qtr_pairing_process/opponent_models.py",
        "    def combine(self, child_scores: Sequence[float]) -> float:\n        raise LabelsUnavailable(",
        "    def combine(self, child_scores: Sequence[float]) -> float:\n        return min(child_scores)\n        raise LabelsUnavailable(",
        "test_opponent_models.py",
    ),
    (
        "opponent collapse ignores whose choice level it is",
        "qtr_pairing_process/tree_generator.py",
        "        if is_opponent_level:\n            return model.combine(child_scores)\n        return max(child_scores)",
        "        return model.combine(child_scores)",
        "test_opponent_model_identity.py",
    ),
    (
        "cumulative2 alpha complement tidied to a 0.20 literal",
        "qtr_pairing_process/opponent_models.py",
        "        return self.alpha * min_child + (1.0 - self.alpha) * mean_child",
        "        return self.alpha * min_child + 0.20 * mean_child",
        "test_opponent_model_identity.py",
    ),
]


def run(tests):
    env = dict(os.environ)
    # Mutations like min->max and 0.80->0.50 preserve file size. CPython's
    # bytecode cache keys on (mtime seconds, size), so a same-size edit inside
    # the same second can be served from a stale .pyc and the mutation silently
    # never runs. That produced two false "not guarded" results before it was
    # tracked down, so bytecode writing is off here.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", *tests.split(), "-q", "--no-header", "-x"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


def _purge_pycache():
    for cache in ROOT.rglob("__pycache__"):
        for pyc in cache.glob("*.pyc"):
            pyc.unlink()


def main():
    failures = []
    for label, rel, old, new, tests in MUTATIONS:
        path = ROOT / rel
        original = path.read_text(encoding="utf-8")
        if old not in original:
            print(f"SKIP  {label}: anchor not found in {rel}")
            failures.append(label)
            continue
        path.write_text(original.replace(old, new, 1), encoding="utf-8")
        _purge_pycache()
        try:
            result = run(tests)
        finally:
            path.write_text(original, encoding="utf-8")
            _purge_pycache()
            assert path.read_text(encoding="utf-8") == original, f"restore failed {rel}"
        if result.returncode == 0:
            print(f"NOT GUARDED  {label}  -- tests still passed!")
            failures.append(label)
        else:
            last = [ln for ln in result.stdout.splitlines() if "failed" in ln]
            print(f"guarded      {label}  -- {last[-1] if last else 'failed'}")

    print()
    baseline = run(
        "test_opponent_models.py test_opponent_corpus.py test_opponent_backtest.py "
        "test_opponent_model_identity.py"
    )
    print("after restore:", baseline.stdout.strip().splitlines()[-1])
    if failures:
        print("UNGUARDED:", failures)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
