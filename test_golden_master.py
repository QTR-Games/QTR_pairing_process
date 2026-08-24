"""Golden-master characterization tests for the TreeGenerator pairing solver."""

from __future__ import annotations

import os

import pytest

from golden_master_harness import (
    SORT_MODES,
    find_digest_snapshot_differences,
    find_snapshot_differences,
    generate_model_snapshot,
    generate_snapshot,
    read_snapshot,
    snapshot_path,
)
from golden_master_scenarios import SCENARIOS, SCENARIOS_BY_SLUG

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


def test_generate_snapshot_ignores_ambient_scoring_environment(monkeypatch):
    monkeypatch.setenv("QTR_ENGINE", "model")
    monkeypatch.setenv("QTR_RENDER", "lazy")
    monkeypatch.setenv("QTR_RISK", "1")
    monkeypatch.setenv("QTR_RISK_LAMBDA", "0.25")
    scenario = SCENARIOS_BY_SLUG["3v3_uniform_default_first"]
    sort_mode = "cumulative"
    expected_path = snapshot_path(scenario.slug, sort_mode)
    expected = read_snapshot(scenario.slug, sort_mode)

    actual = generate_snapshot(scenario, sort_mode)

    assert os.environ["QTR_ENGINE"] == "model"
    assert os.environ["QTR_RENDER"] == "lazy"
    assert os.environ["QTR_RISK"] == "1"
    assert os.environ["QTR_RISK_LAMBDA"] == "0.25"
    differences = find_snapshot_differences(expected, actual)
    if differences:
        diff_text = "\n".join(f"- {difference}" for difference in differences)
        pytest.fail(
            f"{expected_path} should ignore ambient scoring environment:\n{diff_text}"
        )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario.slug)
@pytest.mark.parametrize("sort_mode", tuple(SORT_MODES), ids=tuple(SORT_MODES))
def test_pairing_model_snapshot_matches_golden_master(scenario, sort_mode):
    expected_path = snapshot_path(scenario.slug, sort_mode)
    expected = read_snapshot(scenario.slug, sort_mode)

    actual = generate_model_snapshot(scenario, sort_mode)

    if expected.get("fidelity") == "digest":
        differences = find_digest_snapshot_differences(expected, actual)
    else:
        differences = find_snapshot_differences(expected, actual)

    if differences:
        diff_text = "\n".join(f"- {difference}" for difference in differences)
        pytest.fail(f"{expected_path} does not match model-derived tree:\n{diff_text}")
