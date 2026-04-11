"""Regression tests for simple XLSX export/import template compatibility."""

from qtr_pairing_process.db_management.db_manager import DbManager
from qtr_pairing_process.excel_management.simple_excel_exporter import SimpleExcelExporter
from qtr_pairing_process.excel_management.simple_excel_importer import SimpleExcelImporter


def _seed_team(manager: DbManager, team_name: str, players):
    team_id = manager.upsert_team(team_name)
    manager.upsert_and_validate_players(team_id, list(players))
    return team_id


def test_simple_xlsx_export_import_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *args, **kwargs: None)
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *args, **kwargs: None)

    source_db = DbManager(path=str(tmp_path), name="source_export.db")
    friendly_players = ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]
    opponent_players = ["Foxtrot", "Golf", "Hotel", "India", "Juliet"]

    friendly_id = _seed_team(source_db, "Friendly Team", friendly_players)
    opponent_id = _seed_team(source_db, "Opponent Team", opponent_players)

    scenario_id = 6
    ratings_matrix = [
        [1, 2, 3, 4, 5],
        [5, 4, 3, 2, 1],
        [2, 2, 3, 3, 4],
        [4, 3, 2, 1, 5],
        [3, 3, 3, 3, 3],
    ]

    for row_idx, friendly_name in enumerate(friendly_players):
        friendly_player_id = source_db.query_player_id(friendly_name, friendly_id)
        for col_idx, opponent_name in enumerate(opponent_players):
            opponent_player_id = source_db.query_player_id(opponent_name, opponent_id)
            source_db.upsert_rating(
                player_id_1=friendly_player_id,
                player_id_2=opponent_player_id,
                team_id_1=friendly_id,
                team_id_2=opponent_id,
                scenario_id=scenario_id,
                rating=ratings_matrix[row_idx][col_idx],
            )

    export_path = tmp_path / "roundtrip_export.xlsx"
    exporter = SimpleExcelExporter(
        file_path=str(export_path),
        friendly_team_name="Friendly Team",
        opponent_team_name="Opponent Team",
        friendly_players=friendly_players,
        opponent_players=opponent_players,
        ratings_matrix=ratings_matrix,
    )
    exporter.execute()

    target_db = DbManager(path=str(tmp_path), name="target_import.db")
    importer = SimpleExcelImporter(
        db_manager=target_db,
        file_path=str(export_path),
        scenario_id=scenario_id,
    )
    imported_count = importer.execute()

    assert imported_count == 1

    imported_friendly_id = target_db.query_team_id("Friendly Team")
    imported_opponent_id = target_db.query_team_id("Opponent Team")
    assert imported_friendly_id is not None
    assert imported_opponent_id is not None

    for row_idx, friendly_name in enumerate(friendly_players):
        friendly_player_id = target_db.query_player_id(friendly_name, imported_friendly_id)
        for col_idx, opponent_name in enumerate(opponent_players):
            opponent_player_id = target_db.query_player_id(opponent_name, imported_opponent_id)
            rows = target_db.query_sql(
                f"""
                SELECT rating FROM ratings
                WHERE team_1_player_id = {friendly_player_id}
                  AND team_2_player_id = {opponent_player_id}
                  AND scenario_id = {scenario_id}
                """
            )
            assert rows
            assert rows[0][0] == ratings_matrix[row_idx][col_idx]
