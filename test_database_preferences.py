#!/usr/bin/env python3
"""Tests for database persistence feature."""

from pathlib import Path

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


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_database_preferences(Path(tmp_dir))