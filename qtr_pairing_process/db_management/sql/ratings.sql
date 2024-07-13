CREATE TABLE ratings (
    team_1_player_id INTEGER,
    team_1_id INTEGER,
    team_2_player_id INTEGER,
    team_2_id INTEGER,
    scenario_id INTEGER,
    rating INTEGER,
    CONSTRAINT player_id_mix PRIMARY KEY(team_1_player_id, team_2_player_id, scenario_id)
);