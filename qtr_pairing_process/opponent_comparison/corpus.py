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
    "RELIABILITY_GRADES",
    "AS_SUPPLIED",
    "TRANSCRIBED",
    "RECONCILED",
    "UNRELIABLE_OCR",
    "PairingCell",
    "OpponentDecision",
    "RoundValue",
    "GuaranteeStep",
    "Corpus",
    "UngradedCorpusFile",
    "load_corpus",
    "available_corpora",
]

CORPORA_ROOT = Path(__file__).resolve().parent / "corpora"

#: Transcription grade for one corpus file.
#:
#: These live in ``manifest.json`` rather than only in a README because the
#: manifest is what a consumer actually loads. A caveat sitting in prose beside
#: the data is a caveat nobody sees at the point of use.
#:
#: ``UNRELIABLE_OCR`` is defined but carried by no file here, and that is
#: deliberate. An earlier revision graded ``guarantees.csv`` with it on the
#: strength of corrupt strings that turned out to come from a machine-OCR
#: ``.txt`` derivative of the screenshots, not from the screenshots -- which
#: are clean monospace text and were read directly. The grade described the
#: wrong artefact and would have retired 40 rows carrying 80 passing integrity
#: checks. The grade is kept because the referent is real: those ``.txt``
#: dumps are exactly the thing it should be applied to. It is simply not this
#: file. ``test_unreliable_ocr_is_defined_but_unused`` pins that, so applying
#: it to anything is a conscious act.
AS_SUPPLIED = "AS_SUPPLIED"
TRANSCRIBED = "TRANSCRIBED"
RECONCILED = "RECONCILED"
UNRELIABLE_OCR = "UNRELIABLE_OCR"
RELIABILITY_GRADES = (AS_SUPPLIED, TRANSCRIBED, RECONCILED, UNRELIABLE_OCR)


class UngradedCorpusFile(ValueError):
    """Raised when a corpus ships a data file with no transcription grade.

    Deliberately fatal rather than defaulting to "probably fine". A new corpus
    is exactly the moment someone knows how its files were produced, and the
    only moment they will remember.
    """


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

    @property
    def reliability(self) -> dict:
        """Per-file transcription grades, keyed by the manifest's file value."""
        return {
            key: value
            for key, value in self.manifest.get("reliability", {}).items()
            if not key.startswith("_")
        }

    def grade_of(self, filename: str) -> str:
        """Transcription grade for one corpus file."""
        try:
            return self.reliability[filename]["grade"]
        except KeyError:
            raise UngradedCorpusFile(f"{filename!r} has no reliability entry") from None

    @property
    def unreliable_files(self) -> tuple[str, ...]:
        """Files whose individual fields must not be fitted to.

        A file qualifies when nothing has independently checked it: either it
        was read by eye and not yet reconciled (``TRANSCRIBED``), or it is raw
        machine-OCR (``UNRELIABLE_OCR``). ``RECONCILED`` files carry an
        equation that breaks if a field is wrong, and ``AS_SUPPLIED`` files
        were not transcribed by us at all.

        Currently empty for the WTC 2026 corpus, which is the honest answer --
        see the note on :data:`UNRELIABLE_OCR`.
        """
        return tuple(
            sorted(
                name
                for name, entry in self.reliability.items()
                if entry.get("grade") in (TRANSCRIBED, UNRELIABLE_OCR)
            )
        )


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _split_choice_set(raw: str) -> tuple[str, ...]:
    if not raw.strip():
        return ()
    return tuple(part.strip() for part in raw.split("+") if part.strip())


def _require_grades(corpus_id: str, manifest: dict) -> None:
    """Every declared data file must carry a transcription grade.

    This is the rule "caveats die at the point of use, structure survives"
    applied to the corpus itself. A README saying a file is OCR-grade protects
    nobody who loads the manifest and starts fitting; refusing to load does.
    """
    reliability = {
        key: value
        for key, value in manifest.get("reliability", {}).items()
        if not key.startswith("_")
    }
    missing = sorted(set(manifest["files"].values()) - set(reliability))
    if missing:
        raise UngradedCorpusFile(
            f"corpus {corpus_id!r} declares files with no reliability grade: "
            f"{missing}. Add one of {list(RELIABILITY_GRADES)} to "
            "manifest.json['reliability'], with a reason."
        )
    for name, entry in reliability.items():
        grade = entry.get("grade")
        if grade not in RELIABILITY_GRADES:
            raise UngradedCorpusFile(
                f"corpus {corpus_id!r} file {name!r} has grade {grade!r}; "
                f"expected one of {list(RELIABILITY_GRADES)}"
            )
        if not entry.get("reason"):
            raise UngradedCorpusFile(
                f"corpus {corpus_id!r} file {name!r} is graded {grade} with no reason"
            )


def load_corpus(corpus_id: str, root: Path | None = None) -> Corpus:
    """Load a corpus directory by id."""
    base = (root or CORPORA_ROOT) / corpus_id
    manifest_path = base / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"no manifest.json in {base}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files"]
    _require_grades(corpus_id, manifest)

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
