CREATE TABLE IF NOT EXISTS matchup_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_1_player_id INTEGER NOT NULL,
    team_2_player_id INTEGER NOT NULL,
    scenario_id INTEGER NOT NULL,
    comment TEXT NOT NULL,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (team_1_player_id, team_2_player_id, scenario_id),
    FOREIGN KEY (team_1_player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_2_player_id) REFERENCES players(player_id),
    FOREIGN KEY (scenario_id) REFERENCES scenarios(scenario_id)
);
