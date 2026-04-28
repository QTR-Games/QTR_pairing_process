from types import SimpleNamespace
from typing import Any, cast

import pytest

from qtr_pairing_process.data_validator import DataValidator
from qtr_pairing_process.db_management.db_manager import DbManager
from qtr_pairing_process.ui_manager_v2 import UiManager


class _DummyCombo:
    def __init__(self):
        self.value = ""

    def set(self, value):
        self.value = value


def test_name_validation_allows_common_punctuation_and_unicode():
    samples = [
        "O'Brien",
        "King's Guard, West",
        "Jean-Luc",
        "Team/One",
        "François Müller",
        "Москва United",
    ]
    for sample in samples:
        assert DataValidator.validate_player_name(sample) == sample
        assert DataValidator.validate_team_name(sample if len(sample) >= 2 else f"X{sample}")


def test_name_validation_rejects_disallowed_chars_with_specific_detail():
    with pytest.raises(ValueError) as exc_info:
        DataValidator.validate_player_name('Name"Quote')
    message = str(exc_info.value)
    assert "invalid characters" in message
    assert '"' in message


def test_name_validation_no_false_positive_sql_keyword_blocking():
    assert DataValidator.validate_team_name("Union City") == "Union City"
    assert DataValidator.validate_player_name("Drop Bears") == "Drop Bears"


def test_safe_export_filename_token_substitutes_path_separators():
    dummy = SimpleNamespace()
    token = UiManager._safe_export_filename_token(cast(Any, dummy), "A/B\\C:Name*?")
    assert "/" not in token
    assert "\\" not in token
    assert ":" not in token
    assert "*" not in token
    assert "?" not in token


def test_upsert_comment_uses_parameterized_sql_for_apostrophes():
    captured = {}

    def _execute(sql, parameters=None):
        captured["sql"] = sql
        captured["parameters"] = parameters
        return 1

    dummy = SimpleNamespace(execute_sql=_execute, delete_comment=lambda *args, **kwargs: None)

    DbManager.upsert_comment(cast(Any, dummy), 1, 2, 0, "O'Brien's note")

    assert "VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)" in captured["sql"]
    assert captured["parameters"] == (1, 2, 0, "O'Brien's note")


def test_upsert_row_uses_placeholders_and_bound_parameters():
    captured = {}

    def _execute(sql, parameters=None):
        captured["sql"] = sql
        captured["parameters"] = parameters
        return 1

    dummy = SimpleNamespace(execute_sql=_execute)

    DbManager.upsert_row(
        cast(Any, dummy),
        values=(0, "Neutral's Edge"),
        columns=["scenario_id", "scenario_name"],
        table="scenarios",
        constraint_columns=["scenario_id"],
        update_column="scenario_name",
    )

    assert "VALUES" in captured["sql"]
    assert "(?,?)" in captured["sql"]
    assert "ON CONFLICT(scenario_id)" in captured["sql"]
    assert captured["parameters"] == (0, "Neutral's Edge")


def test_fetch_team_data_for_load_uses_parameterized_player_query():
    calls = []

    def _query_sql_params(sql, parameters=None):
        calls.append((sql, parameters))
        return [(11, "O'Brien"), (12, "Anne-Marie")]

    dummy = SimpleNamespace(
        db_manager=SimpleNamespace(
            query_team_id=lambda team_name: 7,
            query_sql_params=_query_sql_params,
        )
    )

    data = UiManager._fetch_team_data_for_load(cast(Any, dummy), "King's Guard, West")

    assert data == {
        "team_id": 7,
        "players": [{"id": 11, "name": "O'Brien"}, {"id": 12, "name": "Anne-Marie"}],
    }
    assert len(calls) == 1
    assert "WHERE team_id = ?" in calls[0][0]
    assert calls[0][1] == (7,)


def test_fetch_grid_snapshot_uses_parameterized_in_clause_query():
    captured = {}

    def _query_sql_params(sql, parameters=None):
        captured["sql"] = sql
        captured["parameters"] = parameters
        return []

    team_data = {
        "Alpha": {"team_id": 1, "players": [{"id": 101, "name": "A1"}, {"id": 102, "name": "A2"}]},
        "Beta": {"team_id": 2, "players": [{"id": 201, "name": "B1"}, {"id": 202, "name": "B2"}]},
    }

    dummy = SimpleNamespace(
        db_manager=SimpleNamespace(query_sql_params=_query_sql_params),
        _fetch_team_data_for_load=lambda name: team_data[name],
    )

    snapshot = UiManager._fetch_grid_snapshot(cast(Any, dummy), "Alpha", "Beta", 3)

    assert snapshot is not None
    assert "team_1_player_id IN (?,?)" in captured["sql"]
    assert "team_2_player_id IN (?,?)" in captured["sql"]
    assert captured["parameters"] == (101, 102, 201, 202, 1, 2, 3)


def test_import_csv_header_and_ratings_supports_commas_apostrophes_and_slashes():
    upserts = []
    team_ids = {
        "King's Guard, West": 10,
        "Red/Blue Squad": 20,
    }
    player_ids = {}

    friendly_players = ["Anne-Marie", "O'Brien", "Joaquín", "Müller", "Fisher, Jr."]
    opponent_players = ["D'Artagnan", "Team/One", "Kowalski", "Smirnov", "Nguyễn"]

    next_player_id = 100
    for name in friendly_players:
        player_ids[(name, 10)] = next_player_id
        next_player_id += 1
    for name in opponent_players:
        player_ids[(name, 20)] = next_player_id
        next_player_id += 1

    dummy = SimpleNamespace(
        combobox_1=_DummyCombo(),
        combobox_2=_DummyCombo(),
        current_rating_system="1-5",
        _resolve_or_create_matchup_team=lambda team_name, players, friendly_team_name=None: team_ids[team_name],
        db_manager=SimpleNamespace(
            query_player_id=lambda player_name, team_id: player_ids.get((player_name, team_id)),
            upsert_rating=lambda p1, p2, t1, t2, scenario_id, rating: upserts.append(
                (p1, p2, t1, t2, scenario_id, rating)
            ),
        ),
    )

    lines = [
        ["King's Guard, West", *friendly_players],
        ["Red/Blue Squad", *opponent_players],
        ["1", *opponent_players],
    ]
    for player_name in friendly_players:
        lines.append([player_name, "1", "2", "3", "4", "5"])

    summary = UiManager.import_csv_header_and_ratings(cast(Any, dummy), lines)

    assert summary["team_1_name"] == "King's Guard, West"
    assert summary["team_2_name"] == "Red/Blue Squad"
    assert summary["ratings_upserted"] == 25
    assert len(upserts) == 25


def test_import_csv_header_and_ratings_invalid_char_reports_row_and_column():
    dummy = SimpleNamespace(
        combobox_1=_DummyCombo(),
        combobox_2=_DummyCombo(),
        current_rating_system="1-5",
        _resolve_or_create_matchup_team=lambda team_name, players, friendly_team_name=None: 1,
        db_manager=SimpleNamespace(query_player_id=lambda *args, **kwargs: 1, upsert_rating=lambda *args, **kwargs: None),
    )

    lines = [
        ["Friendly Team", "Player 1", "Player 2", "Player 3", "Player 4", "Name;Semi"],
        ["Opponent Team", "Opp 1", "Opp 2", "Opp 3", "Opp 4", "Opp 5"],
        ["1", "Opp 1", "Opp 2", "Opp 3", "Opp 4", "Opp 5"],
        ["Player 1", "1", "2", "3", "4", "5"],
    ]

    with pytest.raises(ValueError) as exc_info:
        UiManager.import_csv_header_and_ratings(cast(Any, dummy), lines)

    message = str(exc_info.value)
    assert "row 1, column 'player_5'" in message
    assert "invalid characters" in message
    assert ";" in message
