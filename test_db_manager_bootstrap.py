#!/usr/bin/env python3
"""Regression tests for DB bootstrap and per-DB rating metadata."""

import sqlite3

from qtr_pairing_process.db_management.db_manager import DbManager


def _table_exists(db_path, table_name):
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return cur.fetchone() is not None


def test_bootstrap_existing_empty_db_file(tmp_path):
    db_name = "empty_then_bootstrap.db"
    db_file = tmp_path / db_name

    # Simulate file being created before schema initialization.
    db_file.write_bytes(b"")

    manager = DbManager(path=str(tmp_path), name=db_name)

    assert _table_exists(str(db_file), "teams")
    assert _table_exists(str(db_file), "players")
    assert _table_exists(str(db_file), "scenarios")
    assert _table_exists(str(db_file), "ratings")

    teams_count = manager.query_sql("SELECT COUNT(*) FROM teams")[0][0]
    players_count = manager.query_sql("SELECT COUNT(*) FROM players")[0][0]
    scenarios_count = manager.query_sql("SELECT COUNT(*) FROM scenarios")[0][0]
    ratings_count = manager.query_sql("SELECT COUNT(*) FROM ratings")[0][0]

    assert teams_count >= 2
    assert players_count >= 10
    assert scenarios_count >= 7
    assert ratings_count > 0


def test_rating_system_metadata_persists_per_database(tmp_path):
    db_name = "rating_meta.db"

    manager = DbManager(path=str(tmp_path), name=db_name)
    assert manager.get_rating_system(default="1-5") == "1-5"

    manager.set_rating_system("1-3")

    reopened = DbManager(path=str(tmp_path), name=db_name)
    assert reopened.get_rating_system(default="1-5") == "1-3"


def test_normalize_ratings_to_1_3_clamps_existing_values(tmp_path):
    db_name = "normalize_to_1_3.db"
    manager = DbManager(path=str(tmp_path), name=db_name)

    # Force out-of-range values to simulate legacy/bad data.
    manager.execute_sql("UPDATE ratings SET rating = 5")
    updated_rows = manager.normalize_ratings_to_system("1-3")

    assert updated_rows > 0
    min_max = manager.query_sql("SELECT MIN(rating), MAX(rating) FROM ratings")[0]
    assert min_max == (3, 3)
