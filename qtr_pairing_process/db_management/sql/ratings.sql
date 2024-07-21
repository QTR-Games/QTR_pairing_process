CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_1_player_id INTEGER NOT NULL,
    team_1_id INTEGER NOT NULL,
    team_2_player_id INTEGER NOT NULL,
    team_2_id INTEGER NOT NULL,
    scenario_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    UNIQUE (team_1_player_id, team_2_player_id, scenario_id)
);