"""Loading labelled pairing corpora.

A corpus is a directory containing a ``manifest.json`` that names its CSVs.
Adding an event or a team means dropping a directory into ``corpora/``; it does
not mean editing this file.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "CORPORA_ROOT",
    "PairingCell",
    "OpponentDecision",
    "RoundValue",
    "GuaranteeStep",
    "Corpus",
    "load_corpus",
    "available_corpora",
]

CORPORA_ROOT = Path(__file__).resolve().parent / "corpora"


@dataclass(frozen=True)
class PairingCell:
    """One locked pairing, with the rival tool's label for it."""

    round: int
    opponent_team: str
    usa_side: str
    pairing: int
    usa_player: str
    opponent_player: str
    label: str
    usa_seat: str
    opponent_seat: str
    engine_verdict_our_step: str


@dataclass(frozen=True)
class OpponentDecision:
    """One decision made by the OPPONENT, with the choice set they faced.

    ``verdict`` is the rival tool's judgement of that choice:
    ``strongest_line`` when they took the option worst for us, ``slipped``
    when they left us better off than they had to. That makes it a direct
    observation of how adversarial the opponent actually was -- which is the
    assumption our own engine encodes and has never been able to check.
    """

    round: int
    opponent_team: str
    usa_side: str
    step: int
    decision_type: str
    choice_set: tuple[str, ...]
    chosen: str
    verdict: str
    forced: bool

    @property
    def is_free_choice(self) -> bool:
        return not self.forced

    @property
    def took_adversarial_line(self) -> bool:
        return self.verdict == "strongest_line"


@dataclass(frozen=True)
class RoundValue:
    """A round's label counts and the value the rival tool PRINTED for it.

    ``printed_value`` is the identifying observable. Without it the weights are
    only determined up to an additive constant, because every round holds
    exactly five cells and so ``GOOD + EVEN + SOFT = 5`` identically.
    """

    round: int
    opponent_team: str
    usa_side: str
    good: int
    even: int
    soft_dodge: int
    hard_dodge: int
    printed_value: int
    our_decisions_optimal: int
    our_decisions_total: int
    opponent_slips: int

    @property
    def label_counts(self) -> dict[str, int]:
        return {
            "GOOD": self.good,
            "EVEN": self.even,
            "SOFT DODGE": self.soft_dodge,
            "HARD DODGE": self.hard_dodge,
        }


@dataclass(frozen=True)
class GuaranteeStep:
    """The guaranteed label vector before and after one protocol step."""

    round: int
    step: int
    actor: str
    before: tuple[int, int, int, int]
    after: tuple[int, int, int, int]

    @property
    def changed(self) -> bool:
        return self.before != self.after


@dataclass(frozen=True)
class Corpus:
    corpus_id: str
    event: str
    team: str
    rival_tool: str
    manifest: dict
    cells: tuple[PairingCell, ...]
    opponent_decisions: tuple[OpponentDecision, ...]
    round_values: tuple[RoundValue, ...]
    guarantees: tuple[GuaranteeStep, ...]

    @property
    def free_opponent_decisions(self) -> tuple[OpponentDecision, ...]:
        return tuple(d for d in self.opponent_decisions if d.is_free_choice)

    @property
    def caveats(self) -> tuple[str, ...]:
        return tuple(self.manifest.get("caveats", ()))


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _split_choice_set(raw: str) -> tuple[str, ...]:
    if not raw.strip():
        return ()
    return tuple(part.strip() for part in raw.split("+") if part.strip())


def load_corpus(corpus_id: str, root: Path | None = None) -> Corpus:
    """Load a corpus directory by id."""
    base = (root or CORPORA_ROOT) / corpus_id
    manifest_path = base / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"no manifest.json in {base}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files"]

    cells = tuple(
        PairingCell(
            round=int(row["round"]),
            opponent_team=row["opponent_team"],
            usa_side=row["usa_side"],
            pairing=int(row["pairing"]),
            usa_player=row["usa_player"],
            opponent_player=row["opponent_player"],
            label=row["label"],
            usa_seat=row["usa_seat"],
            opponent_seat=row["opponent_seat"],
            engine_verdict_our_step=row["engine_verdict_our_step"],
        )
        for row in _read(base / files["pairing_cells"])
    )

    decisions = tuple(
        OpponentDecision(
            round=int(row["round"]),
            opponent_team=row["opponent_team"],
            usa_side=row["usa_side"],
            step=int(row["step"]),
            decision_type=row["decision_type"],
            choice_set=_split_choice_set(row["choice_set"]),
            chosen=row["chosen"].strip(),
            verdict=row["verdict"],
            forced=row["forced"].strip().lower() == "yes",
        )
        for row in _read(base / files["opponent_decisions"])
    )

    round_values = tuple(
        RoundValue(
            round=int(row["round"]),
            opponent_team=row["opponent_team"],
            usa_side=row["usa_side"],
            good=int(row["good"]),
            even=int(row["even"]),
            soft_dodge=int(row["soft_dodge"]),
            hard_dodge=int(row["hard_dodge"]),
            printed_value=int(row["printed_value"]),
            our_decisions_optimal=int(row["our_decisions_optimal"]),
            our_decisions_total=int(row["our_decisions_total"]),
            opponent_slips=int(row["opponent_slips"]),
        )
        for row in _read(base / files["round_values"])
    )

    guarantees = tuple(
        GuaranteeStep(
            round=int(row["round"]),
            step=int(row["step"]),
            actor=row["actor"],
            before=(
                int(row["g_before"]),
                int(row["n_before"]),
                int(row["s_before"]),
                int(row["h_before"]),
            ),
            after=(
                int(row["g_after"]),
                int(row["n_after"]),
                int(row["s_after"]),
                int(row["h_after"]),
            ),
        )
        for row in _read(base / files["guarantees"])
    )

    return Corpus(
        corpus_id=manifest["corpus_id"],
        event=manifest["event"],
        team=manifest["team"],
        rival_tool=manifest["rival_tool"],
        manifest=manifest,
        cells=cells,
        opponent_decisions=decisions,
        round_values=round_values,
        guarantees=guarantees,
    )


def available_corpora(root: Path | None = None) -> tuple[str, ...]:
    base = root or CORPORA_ROOT
    if not base.is_dir():
        return ()
    return tuple(sorted(p.name for p in base.iterdir() if (p / "manifest.json").is_file()))
