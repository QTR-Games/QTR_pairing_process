#!/usr/bin/env python3
"""Tests for individual player import/export data-layer workflows."""

from qtr_pairing_process.db_management.db_manager import DbManager


def _create_db(tmp_path):
    return DbManager(path=str(tmp_path), name="individual_player_import_export.db")


def _get_player_id(db_manager, team_name, player_name):
    team_id = db_manager.query_team_id(team_name)
    assert team_id is not None
    player_id = db_manager.query_player_id(player_name, team_id)
    assert player_id is not None
    return team_id, player_id


def test_export_individual_player_ratings_includes_all_rows(tmp_path):
    db_manager = _create_db(tmp_path)

    team_id, player_id = _get_player_id(db_manager, "default_team_1", "default_player_1_1")
    payload = db_manager.export_individual_player_ratings(team_id, player_id)

    assert payload["source_team_id"] == team_id
    assert payload["source_player_id"] == player_id
    # default db seeds 7 scenarios (0-6) x 5 opponent players = 35 rows
    assert len(payload["rows"]) == 35


def test_replace_individual_player_ratings_overwrites_only_target_player(tmp_path):
    db_manager = _create_db(tmp_path)

    team_id, target_player_id = _get_player_id(db_manager, "default_team_1", "default_player_1_1")
    _, non_target_player_id = _get_player_id(db_manager, "default_team_1", "default_player_1_2")

    target_before = db_manager.query_sql_params(
        "SELECT COUNT(*) FROM ratings WHERE team_1_id = ? AND team_1_player_id = ?",
        (team_id, target_player_id),
    )[0][0]
    non_target_before = db_manager.query_sql_params(
        "SELECT COUNT(*) FROM ratings WHERE team_1_id = ? AND team_1_player_id = ?",
        (team_id, non_target_player_id),
    )[0][0]

    payload = db_manager.export_individual_player_ratings(team_id, target_player_id)
    import_rows = payload["rows"]
    import_rows[0]["rating"] = 5

    summary = db_manager.replace_individual_player_ratings(team_id, target_player_id, import_rows)

    target_after = db_manager.query_sql_params(
        "SELECT COUNT(*) FROM ratings WHERE team_1_id = ? AND team_1_player_id = ?",
        (team_id, target_player_id),
    )[0][0]
    non_target_after = db_manager.query_sql_params(
        "SELECT COUNT(*) FROM ratings WHERE team_1_id = ? AND team_1_player_id = ?",
        (team_id, non_target_player_id),
    )[0][0]

    assert target_before == 35
    assert target_after == 35
    assert non_target_before == 35
    assert non_target_after == 35
    assert summary["upserted_ratings"] == 35


def test_replace_individual_player_ratings_clears_empty_comments(tmp_path):
    db_manager = _create_db(tmp_path)

    team_id, target_player_id = _get_player_id(db_manager, "default_team_1", "default_player_1_1")

    payload = db_manager.export_individual_player_ratings(team_id, target_player_id)
    first_row = payload["rows"][0]

    db_manager.upsert_comment(
        target_player_id,
        first_row["opponent_player_id"],
        first_row["scenario_id"],
        "Original comment",
    )

    payload = db_manager.export_individual_player_ratings(team_id, target_player_id)
    payload["rows"][0]["comment"] = ""

    summary = db_manager.replace_individual_player_ratings(team_id, target_player_id, payload["rows"])

    comment_after = db_manager.query_comment(
        target_player_id,
        first_row["opponent_player_id"],
        first_row["scenario_id"],
    )

    assert comment_after is None
    assert summary["cleared_comments"] >= 1
