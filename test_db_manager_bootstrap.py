#!/usr/bin/env python3
"""Regression tests for DB bootstrap and per-DB rating metadata."""

import sqlite3
import threading

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


def test_default_seed_ratings_start_at_one(tmp_path):
    db_name = "default_ratings_one.db"
    manager = DbManager(path=str(tmp_path), name=db_name)

    min_max = manager.query_sql("SELECT MIN(rating), MAX(rating) FROM ratings")[0]
    assert min_max == (1, 1)


def test_rating_system_metadata_persists_per_database(tmp_path):
    db_name = "rating_meta.db"

    manager = DbManager(path=str(tmp_path), name=db_name)
    assert manager.get_rating_system(default="1-5") in {"1-3", "1-5", "1-10"}

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


def test_secure_interface_is_thread_local_for_query_team_id(tmp_path):
    db_name = "thread_local_secure_interface.db"
    manager = DbManager(path=str(tmp_path), name=db_name)

    manager.upsert_team("Thread Team")
    main_interface = manager.get_secure_interface()

    result = {}

    def _worker():
        try:
            worker_interface = manager.get_secure_interface()
            result["thread_interface_id"] = id(worker_interface)
            result["team_id"] = manager.query_team_id("Thread Team")
        except Exception as exc:  # pragma: no cover - this is the failure path we guard against
            result["error"] = str(exc)

    thread = threading.Thread(target=_worker)
    thread.start()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert "error" not in result
    assert result.get("team_id") is not None
    assert result.get("thread_interface_id") != id(main_interface)


def test_secure_interface_cache_bulk_cleanup_removes_dead_threads(tmp_path):
    # REVIEW DECISION (2026-04): cleanup runs in periodic bulk sweeps for speed,
    # not aggressively on every access.
    db_name = "thread_local_secure_interface_cleanup.db"
    manager = DbManager(path=str(tmp_path), name=db_name)
    manager._secure_db_cleanup_interval = 1

    manager.upsert_team("Cleanup Team")
    manager.get_secure_interface()

    worker_meta = {}

    def _worker():
        manager.get_secure_interface()
        worker_meta["tid"] = threading.get_ident()

    worker = threading.Thread(target=_worker)
    worker.start()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert "tid" in worker_meta

    manager.get_secure_interface()

    cache_keys = list(manager._secure_db_by_thread.keys())
    assert all(key[0] != worker_meta["tid"] for key in cache_keys)
