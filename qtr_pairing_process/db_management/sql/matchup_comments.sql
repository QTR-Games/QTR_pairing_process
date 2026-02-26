-- Matchup Comments Table Schema
-- Supports strategic annotations for individual player matchups per scenario

CREATE TABLE IF NOT EXISTS matchup_comments (
    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_1_player_id INTEGER NOT NULL,
    team_2_player_id INTEGER NOT NULL,
    scenario_id INTEGER NOT NULL,
    comment TEXT(2000),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure one comment per player-vs-player-per-scenario combination
    UNIQUE (team_1_player_id, team_2_player_id, scenario_id),

    -- Foreign key constraints for data integrity
    FOREIGN KEY (team_1_player_id) REFERENCES players(player_id) ON DELETE CASCADE,
    FOREIGN KEY (team_2_player_id) REFERENCES players(player_id) ON DELETE CASCADE,
    FOREIGN KEY (scenario_id) REFERENCES scenarios(scenario_id) ON DELETE CASCADE
);

-- Index for efficient comment retrieval during grid loading
CREATE INDEX IF NOT EXISTS idx_comments_lookup ON matchup_comments(team_1_player_id, team_2_player_id, scenario_id);
-- Index for scenario-based queries
CREATE INDEX IF NOT EXISTS idx_comments_scenario ON matchup_comments(scenario_id);
