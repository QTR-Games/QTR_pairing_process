""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
import sqlite3
from os.path import expanduser
import os
import json
import hashlib
import threading

from qtr_pairing_process.constants import SCENARIO_MAP
from qtr_pairing_process.secure_db_interface import SecureDBInterface
from qtr_pairing_process.data_validator import DataValidator
from qtr_pairing_process.constants import RATING_SYSTEMS, DEFAULT_RATING_SYSTEM
from qtr_pairing_process.app_logger import get_logger

class DbManager:
    def __init__(self, path=None, name=None) -> None:
        self.path = path or expanduser("~")
        self.name = name or 'default.db'
        self.logger = get_logger(__name__)
        print(self.path, self.name)
        self._secure_db_by_thread = {}
        self._secure_db_get_calls = 0
        self._secure_db_cleanup_interval = 128
        self.initialize_db()

    def _cleanup_secure_interface_cache_if_needed(self, force: bool = False):
        """Bulk-clean stale thread cache entries on a coarse interval.

        REVIEW DECISION (2026-04): We intentionally avoid per-call aggressive
        cleanup to keep `get_secure_interface` fast on hot paths. Instead, stale
        thread entries are removed in periodic bulk sweeps.
        """
        if not self._secure_db_by_thread:
            return

        if not force and self._secure_db_get_calls % self._secure_db_cleanup_interval != 0:
            return

        active_thread_ids = {t.ident for t in threading.enumerate() if t.ident is not None}
        stale_keys = [key for key in self._secure_db_by_thread if key[0] not in active_thread_ids]
        if not stale_keys:
            return

        for key in stale_keys:
            secure_db = self._secure_db_by_thread.pop(key, None)
            if secure_db is None:
                continue
            try:
                secure_db.close()
            except Exception:
                # Best-effort resource release only.
                pass

    def initialize_db(self):
        os.makedirs(self.path, exist_ok=True)
        db_file = os.path.join(self.path, self.name)
        self.logger.info("DbManager.initialize_db start db=%s", db_file)

        if (not os.path.isfile(db_file)) or (not self._has_required_schema()):
            self.logger.info("DbManager creating/repairing schema for db=%s", db_file)
            self.create_tables()

        self._ensure_default_seed_data()
        self._ensure_app_settings_table()
        self.logger.info("DbManager.initialize_db complete db=%s", db_file)

    def _has_required_schema(self):
        required = {"teams", "players", "scenarios", "ratings"}
        try:
            with self.connect_db(self.path, self.name) as db_conn:
                db_cur = db_conn.cursor()
                db_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing = {row[0] for row in db_cur.fetchall()}
            return required.issubset(existing)
        except sqlite3.Error:
            return False

    def _ensure_default_seed_data(self):
        teams_count = self.query_sql("SELECT COUNT(*) FROM teams")[0][0]
        scenarios_count = self.query_sql("SELECT COUNT(*) FROM scenarios")[0][0]
        players_count = self.query_sql("SELECT COUNT(*) FROM players")[0][0]
        ratings_count = self.query_sql("SELECT COUNT(*) FROM ratings")[0][0]
        self.logger.info(
            "DbManager seed counts teams=%s scenarios=%s players=%s ratings=%s",
            teams_count,
            scenarios_count,
            players_count,
            ratings_count,
        )

        if teams_count == 0:
            self.create_default_teams()
        if scenarios_count == 0:
            self.create_default_scenarios()
        if players_count == 0:
            self.create_default_players()
        if ratings_count == 0:
            self.create_default_ratings(rating_system=DEFAULT_RATING_SYSTEM)

        # Keep scenario labels aligned to current-season naming conventions.
        self.insert_scenarios()

    def connect_db(self, path, name):
        return sqlite3.connect(f'{path}/{name}')

    def _ensure_app_settings_table(self):
        self.execute_sql(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def get_rating_system(self, default="1-5"):
        self._ensure_app_settings_table()
        rows = self.query_sql_params(
            "SELECT setting_value FROM app_settings WHERE setting_key = ?",
            ("rating_system",),
        )
        if rows and rows[0][0]:
            return str(rows[0][0])
        inferred = self.infer_rating_system_from_data(default=default)
        return inferred

    def set_rating_system(self, rating_system):
        self._ensure_app_settings_table()
        if rating_system not in RATING_SYSTEMS:
            raise ValueError(f"Unsupported rating system: {rating_system}")
        self.execute_sql(
            """
            INSERT INTO app_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(setting_key)
            DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = excluded.updated_at
            """,
            ("rating_system", str(rating_system)),
        )
        self.logger.info("DbManager set rating system db=%s/%s rating_system=%s", self.path, self.name, rating_system)

    def infer_rating_system_from_data(self, default=DEFAULT_RATING_SYSTEM):
        """Infer rating system from stored rating values when metadata is absent."""
        rows = self.query_sql("SELECT MIN(rating), MAX(rating) FROM ratings")
        if not rows or rows[0][1] is None:
            return default

        min_rating, max_rating = rows[0]
        if min_rating is None or max_rating is None:
            return default

        for system, cfg in sorted(RATING_SYSTEMS.items(), key=lambda item: item[1]['range'][1]):
            min_allowed, max_allowed = cfg['range']
            if int(min_rating) >= int(min_allowed) and int(max_rating) <= int(max_allowed):
                return system
        return default
    
    def get_secure_interface(self):
        """Get a thread-local secure interface for parameterized queries.

        SQLite connections/cursors are bound to their creating thread by default.
        Caching a single SecureDBInterface globally can therefore fail when
        background workers reuse a cursor created on the UI thread.
        """
        self._secure_db_get_calls += 1
        self._cleanup_secure_interface_cache_if_needed()

        thread_key = (threading.get_ident(), self.path, self.name)
        secure_db = self._secure_db_by_thread.get(thread_key)
        if secure_db is None:
            conn = self.connect_db(self.path, self.name)
            secure_db = SecureDBInterface(conn)
            self._secure_db_by_thread[thread_key] = secure_db
        return secure_db
    
    def execute_sql(self, sql, parameters=None):
        with self.connect_db(self.path, self.name) as db_conn:
            db_cur = db_conn.cursor()
            if parameters:
                db_cur.execute(sql, parameters)
            else:
                db_cur.execute(sql)
            db_conn.commit()
            return db_cur.rowcount

    def query_sql(self, sql):
        with self.connect_db(self.path, self.name) as db_conn:
            db_cur = db_conn.cursor()
            db_cur.execute(sql)
            rows = db_cur.fetchall()
        return rows

    def query_sql_params(self, sql, parameters=None):
        with self.connect_db(self.path, self.name) as db_conn:
            db_cur = db_conn.cursor()
            db_cur.execute(sql, parameters or ())
            rows = db_cur.fetchall()
        return rows
    
    def insert_row(self, values, columns, table):
        # REVIEW DECISION (2026-04): `table` is an internal call-site constant,
        # never user input. Do not route external/user strings here.
        placeholders = ','.join(['?'] * len(columns))
        insert_sql = f"""
            INSERT INTO {table}
            ({','.join(columns)})
            VALUES
            ({placeholders})
        """
        rows_affected = self.execute_sql(insert_sql, tuple(values))
        if rows_affected == 0:
            raise ValueError(f'insert_row operation failed for table {table}. No rows were affected.')

    def upsert_row(self, values, columns, table, constraint_columns, update_column):
        # REVIEW DECISION (2026-04): Identifier interpolation here is internal-only
        # (fixed table/column names from code), not user-controlled data.
        placeholders = ','.join(['?'] * len(columns))
        upsert_sql = f"""
            INSERT INTO {table}
            ({','.join(columns)})
            VALUES
            ({placeholders})
            ON CONFLICT({','.join(constraint_columns)})
            DO UPDATE SET
            {update_column} = excluded.{update_column}
        """
        # print(f"sql statement: {upsert_sql}")
        rows_affected = self.execute_sql(upsert_sql, tuple(values))
        if rows_affected == 0:
            raise ValueError(f'upsert_row operation failed for table {table}. No rows were affected.')

    ###########
    # Scenarios
    ###########
    def create_scenario(self, scenario_id, scenario_name):
        """Create scenario using secure parameterized query"""
        try:
            secure_db = self.get_secure_interface()
            secure_db.create_scenario_secure(scenario_id, scenario_name)
        except (ValueError, RuntimeError) as e:
            print(f"Error creating scenario '{scenario_name}': {e}")
            raise

    def query_scenario_id(self, scenario_name):
        """Query scenario ID using secure parameterized query"""
        try:
            secure_db = self.get_secure_interface()
            return secure_db.query_scenario_id_secure(scenario_name)
        except (ValueError, RuntimeError) as e:
            print(f"Error querying scenario ID for '{scenario_name}': {e}")
            raise
    
    def insert_scenarios(self):
        for num, desc in SCENARIO_MAP.items():
            self.upsert_scenario(num, desc)

    def upsert_scenario(self, scenario_id, scenario_name):
        """Upsert scenario name by ID across both modern and legacy schemas.

        Some legacy databases have a `scenarios` table without a UNIQUE/PK
        constraint on `scenario_id`, so `ON CONFLICT(scenario_id)` is invalid.
        Use update-then-insert logic that works regardless of table constraints.
        """
        updated = self.execute_sql(
            "UPDATE scenarios SET scenario_name = ? WHERE scenario_id = ?",
            (scenario_name, scenario_id),
        )

        if updated == 0:
            self.execute_sql(
                "INSERT INTO scenarios (scenario_id, scenario_name) VALUES (?, ?)",
                (scenario_id, scenario_name),
            )

    #######
    # Teams
    #######
    def create_team(self, team_name):
        """Create team using secure parameterized query"""
        try:
            secure_db = self.get_secure_interface()
            secure_db.create_team_secure(team_name)
        except (ValueError, RuntimeError) as e:
            print(f"Error creating team '{team_name}': {e}")
            raise

    def query_team_id(self, team_name):
        """Query team ID using secure parameterized query"""
        try:
            secure_db = self.get_secure_interface()
            return secure_db.query_team_id_secure(team_name)
        except (ValueError, RuntimeError) as e:
            print(f"Error querying team ID for '{team_name}': {e}")
            raise

    def upsert_team(self, team_name):
        """Create or update team using secure parameterized query"""
        try:
            secure_db = self.get_secure_interface()
            return secure_db.upsert_team_secure(team_name)
        except (ValueError, RuntimeError) as e:
            print(f"Error upserting team '{team_name}': {e}")
            raise

    def rename_team(self, team_id, team_name):
        """Rename an existing team in place using secure parameterized query."""
        try:
            secure_db = self.get_secure_interface()
            rows = secure_db.update_team_name_secure(team_id, team_name)
            if rows == 0:
                raise RuntimeError(f"No team row updated for team_id={team_id}")
            return rows
        except (ValueError, RuntimeError) as e:
            print(f"Error renaming team {team_id} to '{team_name}': {e}")
            raise
            
    #########
    # Players
    #########
    def create_player(self, player_name, team_id):
        """Create player using secure parameterized query"""
        try:
            secure_db = self.get_secure_interface()
            secure_db.create_player_secure(player_name, team_id)
        except (ValueError, RuntimeError) as e:
            print(f"Error creating player '{player_name}' for team {team_id}: {e}")
            raise

    def query_players(self, team_id):
        """Query players using secure parameterized query"""
        try:
            secure_db = self.get_secure_interface()
            results = secure_db.query_players_secure(team_id)
            
            # Keep original business logic for 5-player validation
            if len(results) > 5 or (len(results) > 0 and len(results) < 5):
                raise ValueError(f'Invalid Number of Player Records for team {team_id}')
            elif len(results) == 5:
                return results
            else:
                return None
        except (ValueError, RuntimeError) as e:
            print(f"Error querying players for team {team_id}: {e}")
            raise

    def query_player_id(self, player_name, team_id):
        """Get player ID by player name and team ID using secure parameterized query"""
        try:
            secure_db = self.get_secure_interface()
            return secure_db.query_player_id_secure(player_name, team_id)
        except (ValueError, RuntimeError) as e:
            print(f"Error querying player ID for '{player_name}' in team {team_id}: {e}")
            raise


    def rename_player(self, player_id, team_id, player_name):
        """Rename an existing player in place using secure parameterized query."""
        try:
            secure_db = self.get_secure_interface()
            rows = secure_db.update_player_name_secure(player_id, team_id, player_name)
            if rows == 0:
                raise RuntimeError(f"No player row updated for player_id={player_id} team_id={team_id}")
            return rows
        except (ValueError, RuntimeError) as e:
            print(f"Error renaming player {player_id} on team {team_id} to '{player_name}': {e}")
            raise

    def upsert_and_validate_players(self, team_id, player_names):
        players = self.query_players(team_id)
        # print(f"team_id={team_id};\nplayer_names={player_names};\nplayers={players}")
        if not players:
            for player_name in player_names:
                self.create_player(team_id=team_id, player_name=player_name)
            players = self.query_players(team_id=team_id)
            if not players:
                raise ValueError('Team Not Upserting')
        # validate players are the same
        queried_player_names = [x[1] for x in players]
        # print(f"queried_player_names are: {queried_player_names}")
        if queried_player_names != player_names:
            raise ValueError(f'Players differ between existing team and queried team: {queried_player_names} {player_names}')
        return players
        
    #########
    # Ratings
    #########

    def upsert_rating(self, player_id_1, player_id_2, team_id_1, team_id_2, scenario_id, rating):
        # Ensure team and player IDs are in the correct order for upsert
        # if team_id_1 > team_id_2:
        #     team_id_1, team_id_2 = team_id_2, team_id_1
        #     player_id_1, player_id_2 = player_id_2, player_id_1

        table = 'ratings'
        columns = ['team_1_player_id', 'team_1_id', 'team_2_player_id', 'team_2_id', 'scenario_id', 'rating']
        values = (player_id_1, team_id_1, player_id_2, team_id_2, scenario_id, rating)
        constraint_columns = ['team_1_player_id', 'team_2_player_id', 'scenario_id']
        update_column = 'rating'
        self.upsert_row(values, columns, table, constraint_columns, update_column)
    
    def get_ratings_count(self):
        """Get the total count of ratings in the database"""
        sql = "SELECT COUNT(*) FROM ratings"
        result = self.query_sql(sql)
        return result[0][0] if result else 0

    def get_db_fingerprint(self):
        """Build a stable lineage fingerprint from teams, players, and scenarios."""
        teams = self.query_sql("SELECT team_id, team_name FROM teams ORDER BY team_id")
        players = self.query_sql("SELECT player_id, team_id, player_name FROM players ORDER BY player_id")
        scenarios = self.query_sql("SELECT scenario_id, scenario_name FROM scenarios ORDER BY scenario_id")
        payload = {
            "teams": teams,
            "players": players,
            "scenarios": scenarios,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_team_roster_hash(self, team_id):
        """Build a stable hash for a team's player roster including IDs and names."""
        rows = self.query_sql_params(
            "SELECT player_id, player_name FROM players WHERE team_id = ? ORDER BY player_id",
            (team_id,),
        )
        raw = json.dumps(rows, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def export_individual_player_ratings(self, team_id, player_id):
        """Export all ratings/comments for a friendly player across all opponents and scenarios."""
        source_row = self.query_sql_params(
            """
            SELECT p.player_id, p.player_name, p.team_id, t.team_name
            FROM players p
            JOIN teams t ON t.team_id = p.team_id
            WHERE p.player_id = ? AND p.team_id = ?
            """,
            (player_id, team_id),
        )
        if not source_row:
            raise ValueError(f"Friendly player {player_id} not found for team {team_id}")

        source_player_id, source_player_name, source_team_id, source_team_name = source_row[0]

        rows = self.query_sql_params(
            """
            SELECT
                r.team_2_id,
                t2.team_name,
                r.team_2_player_id,
                p2.player_name,
                r.scenario_id,
                r.rating,
                COALESCE(mc.comment, '')
            FROM ratings r
            JOIN teams t2 ON t2.team_id = r.team_2_id
            JOIN players p2 ON p2.player_id = r.team_2_player_id
            LEFT JOIN matchup_comments mc
                ON mc.team_1_player_id = r.team_1_player_id
               AND mc.team_2_player_id = r.team_2_player_id
               AND mc.scenario_id = r.scenario_id
            WHERE r.team_1_id = ?
              AND r.team_1_player_id = ?
            ORDER BY r.team_2_id, r.team_2_player_id, r.scenario_id
            """,
            (team_id, player_id),
        )

        export_rows = []
        for team_2_id, team_2_name, player_2_id, player_2_name, scenario_id, rating, comment in rows:
            export_rows.append(
                {
                    "opponent_team_id": team_2_id,
                    "opponent_team_name": team_2_name,
                    "opponent_player_id": player_2_id,
                    "opponent_player_name": player_2_name,
                    "scenario_id": scenario_id,
                    "rating": rating,
                    "comment": comment or "",
                }
            )

        return {
            "source_team_id": source_team_id,
            "source_team_name": source_team_name,
            "source_player_id": source_player_id,
            "source_player_name": source_player_name,
            "rows": export_rows,
        }

    def replace_individual_player_ratings(self, team_id, player_id, rows):
        """Replace all ratings/comments for a friendly player and import provided rows transactionally."""
        deleted_ratings = 0
        deleted_comments = 0
        upserted_ratings = 0
        upserted_comments = 0
        cleared_comments = 0

        with self.connect_db(self.path, self.name) as db_conn:
            db_cur = db_conn.cursor()
            try:
                db_cur.execute("BEGIN")

                db_cur.execute(
                    "DELETE FROM ratings WHERE team_1_id = ? AND team_1_player_id = ?",
                    (team_id, player_id),
                )
                deleted_ratings = db_cur.rowcount

                db_cur.execute(
                    "DELETE FROM matchup_comments WHERE team_1_player_id = ?",
                    (player_id,),
                )
                deleted_comments = db_cur.rowcount

                for row in rows:
                    db_cur.execute(
                        """
                        INSERT INTO ratings
                            (team_1_player_id, team_1_id, team_2_player_id, team_2_id, scenario_id, rating)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(team_1_player_id, team_2_player_id, scenario_id)
                        DO UPDATE SET rating = excluded.rating
                        """,
                        (
                            player_id,
                            team_id,
                            row["opponent_player_id"],
                            row["opponent_team_id"],
                            row["scenario_id"],
                            row["rating"],
                        ),
                    )
                    upserted_ratings += 1

                    comment = (row.get("comment") or "").strip()
                    if comment:
                        db_cur.execute(
                            """
                            INSERT INTO matchup_comments
                                (team_1_player_id, team_2_player_id, scenario_id, comment, updated_date)
                            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                            ON CONFLICT(team_1_player_id, team_2_player_id, scenario_id)
                            DO UPDATE SET
                                comment = excluded.comment,
                                updated_date = excluded.updated_date
                            """,
                            (
                                player_id,
                                row["opponent_player_id"],
                                row["scenario_id"],
                                comment,
                            ),
                        )
                        upserted_comments += 1
                    else:
                        cleared_comments += 1

                db_conn.commit()
            except Exception:
                db_conn.rollback()
                raise

        return {
            "deleted_ratings": deleted_ratings,
            "deleted_comments": deleted_comments,
            "upserted_ratings": upserted_ratings,
            "upserted_comments": upserted_comments,
            "cleared_comments": cleared_comments,
        }

    #########
    # Comments
    #########

    def upsert_comment(self, player_id_1, player_id_2, scenario_id, comment):
        """
        Insert or update a matchup comment.
        
        Args:
            player_id_1 (int): Team 1 (friendly) player ID
            player_id_2 (int): Team 2 (opponent) player ID  
            scenario_id (int): Scenario ID (0-6)
            comment (str): Comment text (max 2000 characters)
        """
        if comment is None or comment.strip() == '':
            # Delete comment if empty
            self.delete_comment(player_id_1, player_id_2, scenario_id)
            return

        # Validate comment length
        if len(comment) > 2000:
            raise ValueError(f'Comment exceeds maximum length of 2000 characters: {len(comment)}')

        rows_affected = self.execute_sql(
            """
            INSERT INTO matchup_comments
                (team_1_player_id, team_2_player_id, scenario_id, comment, updated_date)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(team_1_player_id, team_2_player_id, scenario_id)
            DO UPDATE SET
                comment = excluded.comment,
                updated_date = excluded.updated_date
            """,
            (player_id_1, player_id_2, scenario_id, comment),
        )
        if rows_affected == 0:
            raise ValueError('upsert_comment operation failed. No rows were affected.')

    def query_comment(self, player_id_1, player_id_2, scenario_id):
        """
        Retrieve a specific matchup comment.
        
        Returns:
            str or None: Comment text if exists, None if no comment
        """
        results = self.query_sql_params(
            """
            SELECT comment
            FROM matchup_comments
            WHERE team_1_player_id = ? AND team_2_player_id = ? AND scenario_id = ?
            """,
            (player_id_1, player_id_2, scenario_id),
        )
        if results and len(results) > 0:
            return results[0][0]
        return None

    def query_all_comments(self, team_1_id, team_2_id, scenario_id):
        """
        Retrieve all comments for a team matchup in a specific scenario.
        
        Returns:
            dict: {(friendly_player_name, opponent_player_name): comment}
        """
        results = self.query_sql_params(
            """
            SELECT 
                p1.player_name as friendly_player,
                p2.player_name as opponent_player,
                mc.comment
            FROM matchup_comments mc
            JOIN players p1 ON mc.team_1_player_id = p1.player_id
            JOIN players p2 ON mc.team_2_player_id = p2.player_id
            WHERE p1.team_id = ? AND p2.team_id = ? AND mc.scenario_id = ?
            """,
            (team_1_id, team_2_id, scenario_id),
        )
        
        comments_dict = {}
        for friendly_player, opponent_player, comment in results:
            comments_dict[(friendly_player, opponent_player)] = comment
        
        return comments_dict

    def delete_comment(self, player_id_1, player_id_2, scenario_id):
        """Delete a specific matchup comment."""
        self.execute_sql(
            """
            DELETE FROM matchup_comments
            WHERE team_1_player_id = ? AND team_2_player_id = ? AND scenario_id = ?
            """,
            (player_id_1, player_id_2, scenario_id),
        )

    def get_comment_statistics(self):
        """Get statistics about comment usage."""
        sql = """
            SELECT 
                COUNT(*) as total_comments,
                AVG(LENGTH(comment)) as avg_comment_length,
                MAX(LENGTH(comment)) as max_comment_length,
                COUNT(DISTINCT scenario_id) as scenarios_with_comments
            FROM matchup_comments 
            WHERE comment IS NOT NULL AND comment != ''
        """
        results = self.query_sql(sql)
        if results and len(results) > 0:
            return {
                'total_comments': results[0][0],
                'avg_comment_length': results[0][1] or 0,
                'max_comment_length': results[0][2] or 0,
                'scenarios_with_comments': results[0][3]
            }
        return {'total_comments': 0, 'avg_comment_length': 0, 'max_comment_length': 0, 'scenarios_with_comments': 0}

    # Name-based wrapper methods for UI integration
    def upsert_comment_by_name(self, team1_name, team2_name, scenario_name, 
                              friendly_player_name, opponent_player_name, comment):
        """Upsert comment using team names, scenario name, and player names"""
        # Get team IDs
        team1_id = self.query_team_id(team1_name)
        team2_id = self.query_team_id(team2_name)
        
        if team1_id is None or team2_id is None:
            raise ValueError(f"Teams not found: {team1_name}, {team2_name}")
        
        # Get scenario ID
        scenario_id = self.query_scenario_id(scenario_name)
        if scenario_id is None:
            raise ValueError(f"Scenario not found: {scenario_name}")
        
        # Get player IDs
        player1_id = self.query_player_id(friendly_player_name, team1_id)
        player2_id = self.query_player_id(opponent_player_name, team2_id)
        
        if player1_id is None or player2_id is None:
            raise ValueError(f"Players not found: {friendly_player_name} (team {team1_name}), {opponent_player_name} (team {team2_name})")
        
        # Call the ID-based method
        return self.upsert_comment(player1_id, player2_id, scenario_id, comment)

    def query_comment_by_name(self, team1_name, team2_name, scenario_name, 
                             friendly_player_name, opponent_player_name):
        """Query comment using team names, scenario name, and player names"""
        try:
            # Get team IDs
            team1_id = self.query_team_id(team1_name)
            team2_id = self.query_team_id(team2_name)
            
            if team1_id is None or team2_id is None:
                return None
            
            # Get scenario ID
            scenario_id = self.query_scenario_id(scenario_name)
            if scenario_id is None:
                return None
            
            # Get player IDs
            player1_id = self.query_player_id(friendly_player_name, team1_id)
            player2_id = self.query_player_id(opponent_player_name, team2_id)
            
            if player1_id is None or player2_id is None:
                return None
            
            # Call the ID-based method
            return self.query_comment(player1_id, player2_id, scenario_id)
        except Exception:
            return None

    def delete_comment_by_name(self, team1_name, team2_name, scenario_name, 
                              friendly_player_name, opponent_player_name):
        """Delete comment using team names, scenario name, and player names"""
        # Get team IDs
        team1_id = self.query_team_id(team1_name)
        team2_id = self.query_team_id(team2_name)
        
        if team1_id is None or team2_id is None:
            raise ValueError(f"Teams not found: {team1_name}, {team2_name}")
        
        # Get scenario ID
        scenario_id = self.query_scenario_id(scenario_name)
        if scenario_id is None:
            raise ValueError(f"Scenario not found: {scenario_name}")
        
        # Get player IDs
        player1_id = self.query_player_id(friendly_player_name, team1_id)
        player2_id = self.query_player_id(opponent_player_name, team2_id)
        
        if player1_id is None or player2_id is None:
            raise ValueError(f"Players not found: {friendly_player_name} (team {team1_name}), {opponent_player_name} (team {team2_name})")
        
        # Call the ID-based method
        return self.delete_comment(player1_id, player2_id, scenario_id)
        
    def create_tables(self):
        import sys
        if getattr(sys, 'frozen', False):
            # Running as compiled exe — SQL files are bundled under _MEIPASS
            path = os.path.join(sys._MEIPASS, 'qtr_pairing_process', 'db_management', 'sql')
        else:
            # Running from source — locate sql/ relative to this file
            path = os.path.join(os.path.dirname(__file__), 'sql')
        files = os.listdir(path)

        for file in files:
            with open(f'{path}/{file}', 'r', encoding='utf-8-sig') as file_read:
                sql_content = file_read.read()
                
                # Split multiple SQL statements and execute them separately
                statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                
                for statement in statements:
                    if statement:  # Skip empty statements
                        try:
                            rows_affected = self.execute_sql(statement)
                            # Note: CREATE statements typically return 0 rows affected, so we don't check this
                        except sqlite3.OperationalError as exc:
                            if "already exists" in str(exc).lower():
                                continue
                            raise

    def create_default_teams(self):
        self.create_team('default_team_1')
        self.create_team('default_team_2')

    def create_default_scenarios(self):
        self.create_scenario(0,'1 - Trench Warfare')
        self.create_scenario(1,'2 - Two Fronts')
        self.create_scenario(2,'3 - Wolves At Our Heels')
        self.create_scenario(3,'4 - Pressure Point')
        self.create_scenario(4,'5 - High Stakes')
        self.create_scenario(5,'6 - Fault Line')
        self.create_scenario(6,'7 - Payload')

    def create_default_players(self):
        for i in range(1,3):
            for j in range(1,6):
                self.create_player(f'default_player_{i}_{j}',i)

    def create_default_ratings(self, rating_system=DEFAULT_RATING_SYSTEM):
        team_1 = self.query_sql('select player_id, team_id from players where team_id=1')
        team_2 = self.query_sql('select player_id, team_id from players where team_id=2')
        if rating_system not in RATING_SYSTEMS:
            rating_system = DEFAULT_RATING_SYSTEM
        min_rating, max_rating = RATING_SYSTEMS[rating_system]['range']
        baseline_rating = 1 if min_rating <= 1 <= max_rating else min_rating

        for scenario_id in SCENARIO_MAP.keys():
            for player_1_row in team_1:
                for player_2_row in team_2:
                    self.upsert_rating(
                        player_id_1=player_1_row[0],
                        team_id_1=player_1_row[1],
                        player_id_2=player_2_row[0],
                        team_id_2=player_2_row[1],
                        scenario_id=scenario_id,
                        rating=baseline_rating
                    )

    def normalize_ratings_to_system(self, rating_system):
        """Clamp all rating values to the selected rating system range."""
        if rating_system not in RATING_SYSTEMS:
            raise ValueError(f"Unsupported rating system: {rating_system}")

        min_rating, max_rating = RATING_SYSTEMS[rating_system]['range']
        with self.connect_db(self.path, self.name) as db_conn:
            db_cur = db_conn.cursor()
            db_cur.execute(
                """
                UPDATE ratings
                SET rating = CASE
                    WHEN rating < ? THEN ?
                    WHEN rating > ? THEN ?
                    ELSE rating
                END
                """,
                (min_rating, min_rating, max_rating, max_rating),
            )
            db_conn.commit()
            updated = db_cur.rowcount if db_cur.rowcount is not None else 0
        self.logger.info(
            "DbManager normalized ratings db=%s/%s system=%s updated_rows=%s",
            self.path,
            self.name,
            rating_system,
            updated,
        )
        return updated
