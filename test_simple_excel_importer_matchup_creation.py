from typing import Any, cast

from qtr_pairing_process.excel_management.simple_excel_importer import SimpleExcelImporter


class _TrackingDb:
    def __init__(self):
        self._next_team_id = 1
        self.team_ids = {"Friendly": self._next_team_id}
        self._next_team_id += 1
        self.players_by_team = {}
        self.player_ids = {}
        self._next_player_id = 100
        self.created_teams = []
        self.ratings = []

    def query_team_id(self, team_name):
        return self.team_ids.get(team_name)

    def upsert_team(self, team_name):
        if team_name in self.team_ids:
            return self.team_ids[team_name]
        team_id = self._next_team_id
        self._next_team_id += 1
        self.team_ids[team_name] = team_id
        self.created_teams.append(team_name)
        return team_id

    def upsert_and_validate_players(self, team_id, player_names):
        existing = self.players_by_team.get(team_id)
        if existing is None:
            self.players_by_team[team_id] = list(player_names)
            for player_name in player_names:
                key = (team_id, player_name)
                self.player_ids[key] = self._next_player_id
                self._next_player_id += 1
        elif existing != list(player_names):
            raise ValueError("Players differ between existing team and queried team")
        return [(self.player_ids[(team_id, name)], name) for name in self.players_by_team[team_id]]

    def query_player_id(self, player_name, team_id):
        return self.player_ids[(team_id, player_name)]

    def upsert_rating(self, player_id_1, player_id_2, team_id_1, team_id_2, scenario_id, rating):
        self.ratings.append(
            (player_id_1, player_id_2, team_id_1, team_id_2, scenario_id, rating)
        )


def test_save_team_to_database_creates_missing_opponent_for_friendly_matchup():
    db = _TrackingDb()
    importer = SimpleExcelImporter(db_manager=cast(Any, db), file_path="dummy.xlsx", scenario_id=0)  # type: ignore[arg-type]
    importer.friendly_team_name = "Friendly"

    team_data = {
        "opponent_team_name": "Brand New Opponent",
        "friendly_players": ["F1", "F2", "F3", "F4", "F5"],
        "opponent_players": ["O1", "O2", "O3", "O4", "O5"],
        "ratings_matrix": [
            [1, 2, 3, 4, 5],
            [2, 3, 4, 5, 1],
            [3, 4, 5, 1, 2],
            [4, 5, 1, 2, 3],
            [5, 1, 2, 3, 4],
        ],
    }

    assert importer.save_team_to_database(team_data) is True

    assert "Brand New Opponent" in db.created_teams
    assert len(db.ratings) == 25

    friendly_team_id = db.query_team_id("Friendly")
    opponent_team_id = db.query_team_id("Brand New Opponent")
    assert friendly_team_id is not None
    assert opponent_team_id is not None

    assert all(row[2] == friendly_team_id for row in db.ratings)
    assert all(row[3] == opponent_team_id for row in db.ratings)
