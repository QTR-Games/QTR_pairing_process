"""Golden-master characterization tests for the TreeGenerator pairing solver."""

from __future__ import annotations

import pytest

from golden_master_harness import (
    SORT_MODES,
    find_digest_snapshot_differences,
    find_snapshot_differences,
    generate_snapshot,
    read_snapshot,
    snapshot_path,
)
from golden_master_scenarios import SCENARIOS


pytestmark = pytest.mark.requires_tk


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario.slug)
@pytest.mark.parametrize("sort_mode", tuple(SORT_MODES), ids=tuple(SORT_MODES))
def test_tree_generator_matches_golden_master(scenario, sort_mode):
    expected_path = snapshot_path(scenario.slug, sort_mode)
    expected = read_snapshot(scenario.slug, sort_mode)

    actual = generate_snapshot(scenario, sort_mode)

    if expected.get("fidelity") == "digest":
        differences = find_digest_snapshot_differences(expected, actual)
    else:
        differences = find_snapshot_differences(expected, actual)

    if differences:
        diff_text = "\n".join(f"- {difference}" for difference in differences)
        pytest.fail(f"{expected_path} does not match regenerated tree:\n{diff_text}")
