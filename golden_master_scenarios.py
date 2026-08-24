"""Deterministic pairing-solver scenarios for golden-master characterization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from qtr_pairing_process.constants import DEFAULT_RATING_SYSTEM


RatingMatrix = dict[str, dict[str, int]]


@dataclass(frozen=True)
class GoldenScenario:
    slug: str
    description: str
    our_players: tuple[str, ...]
    opponent_players: tuple[str, ...]
    our_ratings: RatingMatrix
    opponent_ratings: RatingMatrix
    our_team_first: bool = True
    rating_system: str = DEFAULT_RATING_SYSTEM


THREE_V_THREE_UNIFORM = GoldenScenario(
    slug="3v3_uniform_default_first",
    description="3v3 near-uniform 1-5 ratings with our team choosing first.",
    our_players=("Aegis", "Blaze", "Cipher"),
    opponent_players=("Hydra", "Ion", "Jade"),
    our_ratings={
        "Aegis": {"Hydra": 3, "Ion": 4, "Jade": 3},
        "Blaze": {"Hydra": 2, "Ion": 3, "Jade": 4},
        "Cipher": {"Hydra": 4, "Ion": 3, "Jade": 2},
    },
    opponent_ratings={
        "Hydra": {"Aegis": 3, "Blaze": 4, "Cipher": 2},
        "Ion": {"Aegis": 2, "Blaze": 3, "Cipher": 4},
        "Jade": {"Aegis": 4, "Blaze": 2, "Cipher": 3},
    },
)


FOUR_V_FOUR_COUNTER_FIRST = GoldenScenario(
    slug="4v4_counter_default_first",
    description="4v4 1-5 ratings with strong counter-matchup structure.",
    our_players=("Atlas", "Beacon", "Comet", "Drift"),
    opponent_players=("Ember", "Frost", "Gale", "Havoc"),
    our_ratings={
        "Atlas": {"Ember": 5, "Frost": 2, "Gale": 1, "Havoc": 4},
        "Beacon": {"Ember": 1, "Frost": 5, "Gale": 4, "Havoc": 2},
        "Comet": {"Ember": 2, "Frost": 1, "Gale": 5, "Havoc": 4},
        "Drift": {"Ember": 4, "Frost": 3, "Gale": 2, "Havoc": 5},
    },
    opponent_ratings={
        "Ember": {"Atlas": 1, "Beacon": 5, "Comet": 4, "Drift": 2},
        "Frost": {"Atlas": 4, "Beacon": 1, "Comet": 5, "Drift": 3},
        "Gale": {"Atlas": 5, "Beacon": 2, "Comet": 1, "Drift": 4},
        "Havoc": {"Atlas": 2, "Beacon": 4, "Comet": 3, "Drift": 1},
    },
)


FOUR_V_FOUR_COUNTER_OPPONENT_FIRST = GoldenScenario(
    slug="4v4_counter_default_opponent_first",
    description="Same 4v4 counter matrix with opponent team choosing first.",
    our_players=FOUR_V_FOUR_COUNTER_FIRST.our_players,
    opponent_players=FOUR_V_FOUR_COUNTER_FIRST.opponent_players,
    our_ratings=FOUR_V_FOUR_COUNTER_FIRST.our_ratings,
    opponent_ratings=FOUR_V_FOUR_COUNTER_FIRST.opponent_ratings,
    our_team_first=False,
)


FIVE_V_FIVE_COUNTER_TEN_POINT = GoldenScenario(
    slug="5v5_counter_1_10_first",
    description="5v5 production-size 1-10 ratings with strong counter lanes.",
    our_players=("North", "Orion", "Pulse", "Quill", "Rune"),
    opponent_players=("Sable", "Talon", "Umber", "Vex", "Warden"),
    rating_system="1-10",
    our_ratings={
        "North": {"Sable": 10, "Talon": 3, "Umber": 2, "Vex": 7, "Warden": 5},
        "Orion": {"Sable": 2, "Talon": 9, "Umber": 6, "Vex": 4, "Warden": 8},
        "Pulse": {"Sable": 4, "Talon": 2, "Umber": 10, "Vex": 8, "Warden": 3},
        "Quill": {"Sable": 7, "Talon": 5, "Umber": 3, "Vex": 10, "Warden": 2},
        "Rune": {"Sable": 5, "Talon": 8, "Umber": 4, "Vex": 2, "Warden": 9},
    },
    opponent_ratings={
        "Sable": {"North": 1, "Orion": 9, "Pulse": 7, "Quill": 4, "Rune": 6},
        "Talon": {"North": 8, "Orion": 2, "Pulse": 10, "Quill": 6, "Rune": 3},
        "Umber": {"North": 9, "Orion": 5, "Pulse": 1, "Quill": 8, "Rune": 6},
        "Vex": {"North": 4, "Orion": 7, "Pulse": 3, "Quill": 1, "Rune": 10},
        "Warden": {"North": 6, "Orion": 3, "Pulse": 8, "Quill": 9, "Rune": 2},
    },
)


SCENARIOS: tuple[GoldenScenario, ...] = (
    THREE_V_THREE_UNIFORM,
    FOUR_V_FOUR_COUNTER_FIRST,
    FOUR_V_FOUR_COUNTER_OPPONENT_FIRST,
    FIVE_V_FIVE_COUNTER_TEN_POINT,
)


SCENARIOS_BY_SLUG: Mapping[str, GoldenScenario] = {
    scenario.slug: scenario for scenario in SCENARIOS
}
