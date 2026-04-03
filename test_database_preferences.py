#!/usr/bin/env python3
"""Tests for database persistence feature."""

import os
import json
from pathlib import Path
import pytest

from qtr_pairing_process.database_preferences import DatabasePreferences


def test_database_preferences(tmp_path):
    """Validate database preference persistence using an isolated config file."""
    config_path = tmp_path / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=True, config_file=config_path)

    config = db_prefs.load_config()
    assert "database" in config

    # Save using full file path form and ensure normalization is preserved.
    test_db_file = tmp_path / "test.db"
    success = db_prefs.save_database_preference(str(test_db_file), "test.db")
    assert success is True

    saved_path, saved_name = db_prefs.get_last_database()
    assert saved_path == str(tmp_path)
    assert saved_name == "test.db"

    # UI preference updates should still persist in isolated config.
    db_prefs.set_welcome_message_preference(False)
    assert db_prefs.should_show_welcome_message() is False

    # Validation should fail when file does not exist and pass after creation.
    assert db_prefs.validate_database_exists(saved_path, saved_name) is False
    Path(test_db_file).write_text("", encoding="utf-8")
    assert db_prefs.validate_database_exists(saved_path, saved_name) is True

    # Backup and clear should operate on isolated config only.
    backup_path = db_prefs.backup_config()
    assert backup_path is not None

    cleared = db_prefs.clear_database_preference()
    assert cleared is True
    cleared_path, cleared_name = db_prefs.get_last_database()
    assert cleared_path is None
    assert cleared_name is None


def test_backup_config_deduplicates_and_prunes(tmp_path):
    config_path = tmp_path / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=False, config_file=config_path)
    db_prefs.max_config_backups = 3

    # Ensure config exists and first backup is created.
    db_prefs.save_database_preference(str(tmp_path), "one.db")
    first_backup = db_prefs.backup_config()
    assert first_backup is not None

    # Repeated backup without changes should reuse newest backup, not create a new file.
    second_backup = db_prefs.backup_config()
    assert second_backup == first_backup

    backup_pattern = "KLIK_KLAK_KONFIG.test.backup_*.json"
    backups_after_dedupe = list(tmp_path.glob(backup_pattern))
    assert len(backups_after_dedupe) == 1

    # Create more distinct states; backup count should remain capped at 3.
    for idx in range(1, 7):
        db_prefs.save_database_preference(str(tmp_path), f"{idx}.db")
        assert db_prefs.backup_config() is not None

    backups_after_prune = list(tmp_path.glob(backup_pattern))
    assert len(backups_after_prune) <= 3


def test_persistent_memo_enabled_defaults_to_true(tmp_path):
    config_path = tmp_path / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=False, config_file=config_path)

    prefs = db_prefs.get_strategic_preferences()
    assert prefs["strategic3"]["persistent_memo_enabled"] is True


def test_persistent_memo_toggle_persists_roundtrip(tmp_path):
    config_path = tmp_path / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=False, config_file=config_path)

    assert db_prefs.set_strategic_preferences({"strategic3": {"persistent_memo_enabled": False}})
    prefs_after_disable = db_prefs.get_strategic_preferences()
    assert prefs_after_disable["strategic3"]["persistent_memo_enabled"] is False

    assert db_prefs.set_strategic_preferences({"strategic3": {"persistent_memo_enabled": True}})
    prefs_after_enable = db_prefs.get_strategic_preferences()
    assert prefs_after_enable["strategic3"]["persistent_memo_enabled"] is True


def test_bus_advisory_defaults_present(tmp_path):
    config_path = tmp_path / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=False, config_file=config_path)

    prefs = db_prefs.get_strategic_preferences()
    bus = prefs["bus"]

    assert bus["label_mode"] == "extended"
    assert bus["degree_thresholds"] == {"light": 60, "moderate": 85, "hard_commit": 110}
    assert bus["outlier_detection_enabled"] is True
    assert bus["abort_rules"]["enabled"] is True
    assert bus["abort_rules"]["min_upset_chance"] == 0.20
    assert bus["abort_rules"]["max_downside_risk"] == 8


def test_bus_advisory_thresholds_and_abort_rules_clamped(tmp_path):
    config_path = tmp_path / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=False, config_file=config_path)

    db_prefs.set_strategic_preferences(
        {
            "bus": {
                "degree_thresholds": {"light": 90, "moderate": 40, "hard_commit": 10},
                "outlier_stdev_trigger": 8.0,
                "abort_rules": {
                    "enabled": True,
                    "min_upset_chance": 1.5,
                    "max_downside_risk": -3,
                },
            }
        }
    )

    prefs = db_prefs.get_strategic_preferences()
    bus = prefs["bus"]
    degree = bus["degree_thresholds"]

    assert degree["light"] == 90
    assert degree["moderate"] == 90
    assert degree["hard_commit"] == 90
    assert bus["outlier_stdev_trigger"] == 5.0
    assert bus["abort_rules"]["min_upset_chance"] == 1.0
    assert bus["abort_rules"]["max_downside_risk"] == 0


def test_normalize_database_reference_resolves_relative_path_against_config_dir(tmp_path):
    config_dir = tmp_path / "config_dir"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=False, config_file=config_path)

    path, name = db_prefs._normalize_database_reference("dbs/my_team.db", None)

    expected_db = Path(config_dir / "dbs" / "my_team.db").resolve()
    assert Path(path).resolve() == expected_db.parent
    assert name == expected_db.name


def test_normalize_database_reference_handles_mixed_separators_and_parent_segments(tmp_path):
    config_path = tmp_path / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=False, config_file=config_path)

    mixed_path = str(tmp_path / "folderA" / ".." / "folderB") + "\\sub/../team.db"
    path, name = db_prefs._normalize_database_reference(mixed_path, None)

    expected = Path(tmp_path / "folderB" / "team.db").resolve()
    assert Path(path).resolve() == expected.parent
    assert name == expected.name


def test_normalize_database_reference_name_only_db_file_path(tmp_path):
    config_path = tmp_path / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=False, config_file=config_path)

    db_file = tmp_path / "nested" / "edgecase.db"
    path, name = db_prefs._normalize_database_reference(None, str(db_file))

    assert Path(path).resolve() == db_file.parent.resolve()
    assert name == "edgecase.db"


def test_normalize_database_reference_relative_directory_with_name(tmp_path):
    config_dir = tmp_path / "cfg"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=False, config_file=config_path)

    path, name = db_prefs._normalize_database_reference("..\\db-store", "team.db")

    expected_dir = (config_dir.parent / "db-store").resolve()
    assert Path(path).resolve() == expected_dir
    assert name == "team.db"


def test_load_config_uses_cache_until_force_reload(tmp_path):
    config_path = tmp_path / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=False, config_file=config_path)

    initial = db_prefs.load_config()
    assert initial["version"] == "1.0"

    modified = dict(initial)
    modified["version"] = "2.0"
    config_path.write_text(json.dumps(modified), encoding="utf-8")

    cached = db_prefs.load_config()
    assert cached["version"] == "1.0"

    refreshed = db_prefs.load_config(force_reload=True)
    assert refreshed["version"] == "2.0"


@pytest.mark.parametrize(
    "path_input,name_input,expected_name",
    [
        (None, " nested/path/edge.db ", "edge.db"),
        ("  ", " nested/path/not_a_db.txt ", "not_a_db.txt"),
        ("team_dir", " nested/../team_main.db ", "team_main.db"),
        ("folderA/./folderB/TEAM.DB", "ignored.db", "TEAM.DB"),
    ],
)
def test_normalize_database_reference_parameterized_path_cases(
    tmp_path,
    path_input,
    name_input,
    expected_name,
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "KLIK_KLAK_KONFIG.test.json"
    db_prefs = DatabasePreferences(print_output=False, config_file=config_path)

    normalized_path, normalized_name = db_prefs._normalize_database_reference(path_input, name_input)

    assert normalized_name == expected_name
    if path_input is None or str(path_input).strip() == "":
        if str(name_input).strip().lower().endswith(".db") and ("/" in str(name_input) or "\\" in str(name_input)):
            assert Path(normalized_path).resolve() == (config_dir / "nested" / "path").resolve()
        else:
            assert normalized_path is None
    elif str(path_input).lower().endswith(".db"):
        assert Path(normalized_path).resolve() == (config_dir / "folderA" / "folderB").resolve()
    else:
        assert Path(normalized_path).resolve() == (config_dir / "team_dir").resolve()


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_database_preferences(Path(tmp_dir))