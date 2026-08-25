"""The golden fixtures must only ever be captured from the widget engine.

`test_pairing_model_snapshot_matches_golden_master` checks the model engine
*against* the fixtures. If a model snapshot could be written as a fixture, that
test would become a comparison of the model with itself -- permanently green,
and checking nothing. Since `snapshot_path` is keyed only on scenario and sort
mode, it would happen silently, by overwrite.

No Tk here: these exercise the write guard directly, not tree generation.
"""

import pytest

from golden_master_harness import SOURCE_ENGINE_KEY, write_snapshot


def _snapshot(**extra):
    snapshot = {
        "metadata": {"scenario": "guard_probe", "sort_mode": "cumulative"},
        "fidelity": "full",
        "node_count": 1,
        "digest": "irrelevant",
        "tree": [],
    }
    snapshot.update(extra)
    return snapshot


def test_write_snapshot_refuses_a_model_engine_snapshot():
    with pytest.raises(ValueError, match="refusing to write"):
        write_snapshot(_snapshot(**{SOURCE_ENGINE_KEY: "model"}))


def test_write_snapshot_refuses_any_unrecognised_engine():
    with pytest.raises(ValueError, match="refusing to write"):
        write_snapshot(_snapshot(**{SOURCE_ENGINE_KEY: "something_new"}))


def test_write_snapshot_accepts_the_widget_engine(tmp_path, monkeypatch):
    # The guard must not be vacuous. If it rejected everything, the two tests
    # above would still pass and prove nothing.
    monkeypatch.setattr("golden_master_harness.SNAPSHOT_DIR", tmp_path)

    path = write_snapshot(_snapshot(**{SOURCE_ENGINE_KEY: "widget"}))

    assert path.exists()


def test_write_snapshot_accepts_an_untagged_snapshot(tmp_path, monkeypatch):
    # Snapshots captured before the tag existed carry no marker. Rejecting those
    # would break regeneration of every existing fixture.
    monkeypatch.setattr("golden_master_harness.SNAPSHOT_DIR", tmp_path)

    path = write_snapshot(_snapshot())

    assert path.exists()
