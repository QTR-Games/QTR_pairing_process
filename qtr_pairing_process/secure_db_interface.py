"""
Secure Database Interface
Provides parameterized query methods to prevent SQL injection attacks
"""
import sqlite3
from typing import List, Tuple, Optional, Any, Union
from .data_validator import DataValidator


class SecureDBInterface:
    """Secure database interface with parameterized queries"""
    
    def __init__(self, connection):
        """
        Initialize with database connection
        
        Args:
            connection: SQLite database connection
        """
        self.connection = connection
        self.cursor = connection.cursor()
    
    def execute_parameterized(self, query: str, params: Tuple = ()) -> int:
        """
        Execute a parameterized query safely
        
        Args:
            query: SQL query with ? placeholders
            params: Parameters to bind to the query
            
        Returns:
            Number of rows affected
        """
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
            return self.cursor.rowcount
        except sqlite3.Error as e:
            self.connection.rollback()
            raise RuntimeError(f"Database operation failed: {e}")
    
    def query_parameterized(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """
        Execute a parameterized SELECT query safely
        
        Args:
            query: SQL SELECT query with ? placeholders
            params: Parameters to bind to the query
            
        Returns:
            List of result tuples
        """
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            raise RuntimeError(f"Database query failed: {e}")
    
    def create_team_secure(self, team_name: str) -> None:
        """
        Create a new team with secure parameterized query
        
        Args:
            team_name: Name of the team to create
            
        Raises:
            ValueError: If team name is invalid
            RuntimeError: If database operation fails
        """
        # Validate and sanitize input
        validated_name = DataValidator.validate_team_name(team_name)
        
        # Use parameterized query
        query = "INSERT INTO teams (team_name) VALUES (?)"
        rows_affected = self.execute_parameterized(query, (validated_name,))
        
        if rows_affected == 0:
            raise RuntimeError("Failed to create team - no rows affected")
    
    def query_team_id_secure(self, team_name: str) -> Optional[int]:
        """
        Query team ID by name using secure parameterized query
        
        Args:
            team_name: Name of the team
            
        Returns:
            Team ID if found, None otherwise
            
        Raises:
            ValueError: If team name is invalid
            RuntimeError: If database query fails or multiple records found
        """
        # Validate and sanitize input
        validated_name = DataValidator.validate_team_name(team_name)
        
        # Use parameterized query
        query = "SELECT team_id FROM teams WHERE team_name = ?"
        results = self.query_parameterized(query, (validated_name,))
        
        if len(results) > 1:
            raise RuntimeError(f"Multiple teams found with name '{validated_name}'")
        elif len(results) == 1:
            return results[0][0]
        else:
            return None
    
    def upsert_team_secure(self, team_name: str) -> int:
        """
        Create team if it doesn't exist, return team ID
        
        Args:
            team_name: Name of the team
            
        Returns:
            Team ID
            
        Raises:
            ValueError: If team name is invalid
            RuntimeError: If database operation fails
        """
        # Validate and sanitize input
        validated_name = DataValidator.validate_team_name(team_name)
        
        # Check if team exists
        team_id = self.query_team_id_secure(validated_name)
        
        if not team_id:
            # Create new team
            self.create_team_secure(validated_name)
            team_id = self.query_team_id_secure(validated_name)
            
            if not team_id:
                raise RuntimeError("Failed to create or retrieve team ID")
        
        return team_id
    
    def create_player_secure(self, player_name: str, team_id: int) -> None:
        """
        Create a new player with secure parameterized query
        
        Args:
            player_name: Name of the player
            team_id: ID of the team
            
        Raises:
            ValueError: If player name is invalid
            RuntimeError: If database operation fails
        """
        # Validate and sanitize input
        validated_name = DataValidator.validate_player_name(player_name)
        validated_team_id = DataValidator.validate_integer(team_id, min_value=1)
        
        # Use parameterized query
        query = "INSERT INTO players (player_name, team_id) VALUES (?, ?)"
        rows_affected = self.execute_parameterized(query, (validated_name, validated_team_id))
        
        if rows_affected == 0:
            raise RuntimeError("Failed to create player - no rows affected")
    
    def query_players_secure(self, team_id: int) -> List[Tuple[int, str]]:
        """
        Query players for a team using secure parameterized query
        
        Args:
            team_id: ID of the team
            
        Returns:
            List of (player_id, player_name) tuples
            
        Raises:
            ValueError: If team_id is invalid
            RuntimeError: If database query fails
        """
        # Validate input
        validated_team_id = DataValidator.validate_integer(team_id, min_value=1)
        
        # Use parameterized query
        query = "SELECT player_id, player_name FROM players WHERE team_id = ? ORDER BY player_id"
        return self.query_parameterized(query, (validated_team_id,))
    
    def query_player_id_secure(self, player_name: str, team_id: int) -> Optional[int]:
        """
        Query player ID by name and team using secure parameterized query
        
        Args:
            player_name: Name of the player
            team_id: ID of the team
            
        Returns:
            Player ID if found, None otherwise
            
        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If database query fails
        """
        # Validate and sanitize input
        validated_name = DataValidator.validate_player_name(player_name)
        validated_team_id = DataValidator.validate_integer(team_id, min_value=1)
        
        # Use parameterized query
        query = "SELECT player_id FROM players WHERE player_name = ? AND team_id = ?"
        results = self.query_parameterized(query, (validated_name, validated_team_id))
        
        if len(results) > 1:
            raise RuntimeError(f"Multiple players found with name '{validated_name}' in team {validated_team_id}")
        elif len(results) == 1:
            return results[0][0]
        else:
            return None
    
    def create_scenario_secure(self, scenario_id: int, scenario_name: str) -> None:
        """
        Create a new scenario with secure parameterized query
        
        Args:
            scenario_id: ID of the scenario
            scenario_name: Name of the scenario
            
        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If database operation fails
        """
        # Validate and sanitize input
        validated_id = DataValidator.validate_integer(scenario_id, min_value=0)  # Allow scenario ID 0
        validated_name = DataValidator.validate_scenario_name(scenario_name)
        
        # Use parameterized query
        query = "INSERT INTO scenarios (scenario_id, scenario_name) VALUES (?, ?)"
        rows_affected = self.execute_parameterized(query, (validated_id, validated_name))
        
        if rows_affected == 0:
            raise RuntimeError("Failed to create scenario - no rows affected")
    
    def query_scenario_id_secure(self, scenario_name: str) -> Optional[int]:
        """
        Query scenario ID by name using secure parameterized query
        
        Args:
            scenario_name: Name of the scenario
            
        Returns:
            Scenario ID if found, None otherwise
            
        Raises:
            ValueError: If scenario name is invalid
            RuntimeError: If database query fails
        """
        # Validate and sanitize input
        validated_name = DataValidator.validate_scenario_name(scenario_name)
        
        # Use parameterized query
        query = "SELECT scenario_id FROM scenarios WHERE scenario_name = ?"
        results = self.query_parameterized(query, (validated_name,))
        
        if len(results) > 1:
            raise RuntimeError(f"Multiple scenarios found with name '{validated_name}'")
        elif len(results) == 1:
            return results[0][0]
        else:
            return None
    
    def delete_team_secure(self, team_name: str) -> bool:
        """
        Delete a team and all related records securely
        
        Args:
            team_name: Name of the team to delete
            
        Returns:
            True if team was deleted, False if not found
            
        Raises:
            ValueError: If team name is invalid
            RuntimeError: If database operation fails
        """
        # Validate and sanitize input
        validated_name = DataValidator.validate_team_name(team_name)
        
        # Get team ID first
        team_id = self.query_team_id_secure(validated_name)
        if not team_id:
            return False
        
        try:
            # Delete in proper order to maintain referential integrity
            # Delete ratings first
            self.execute_parameterized(
                "DELETE FROM ratings WHERE team_1_id = ? OR team_2_id = ?",
                (team_id, team_id)
            )
            
            # Delete players
            self.execute_parameterized(
                "DELETE FROM players WHERE team_id = ?",
                (team_id,)
            )
            
            # Finally delete team
            rows_affected = self.execute_parameterized(
                "DELETE FROM teams WHERE team_id = ?",
                (team_id,)
            )
            
            return rows_affected > 0
            
        except sqlite3.Error as e:
            self.connection.rollback()
            raise RuntimeError(f"Failed to delete team: {e}")
    
    def delete_players_for_team_secure(self, team_id: int) -> int:
        """
        Delete all players for a specific team
        
        Args:
            team_id: ID of the team
            
        Returns:
            Number of players deleted
            
        Raises:
            ValueError: If team_id is invalid
            RuntimeError: If database operation fails
        """
        # Validate input
        validated_team_id = DataValidator.validate_integer(team_id, min_value=1)
        
        # Use parameterized query
        query = "DELETE FROM players WHERE team_id = ?"
        return self.execute_parameterized(query, (validated_team_id,))
    
    def create_rating_secure(self, team_1_id: int, team_2_id: int, 
                           player_1_id: int, player_2_id: int, 
                           scenario_id: int, rating: int, 
                           rating_system: str = "1-5") -> None:
        """
        Create a new rating with secure parameterized query
        
        Args:
            team_1_id: ID of first team
            team_2_id: ID of second team
            player_1_id: ID of first player
            player_2_id: ID of second player
            scenario_id: ID of scenario
            rating: Rating value
            rating_system: Rating system to validate against
            
        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If database operation fails
        """
        # Validate all inputs
        validated_team_1_id = DataValidator.validate_integer(team_1_id, min_value=1)
        validated_team_2_id = DataValidator.validate_integer(team_2_id, min_value=1)
        validated_player_1_id = DataValidator.validate_integer(player_1_id, min_value=1)
        validated_player_2_id = DataValidator.validate_integer(player_2_id, min_value=1)
        validated_scenario_id = DataValidator.validate_integer(scenario_id, min_value=1)
        validated_rating = DataValidator.validate_rating(rating, rating_system)
        
        # Use parameterized query
        query = """
            INSERT INTO ratings (team_1_id, team_2_id, team_1_player_id, team_2_player_id, scenario_id, rating) 
            VALUES (?, ?, ?, ?, ?, ?)
        """
        rows_affected = self.execute_parameterized(
            query, 
            (validated_team_1_id, validated_team_2_id, validated_player_1_id, 
             validated_player_2_id, validated_scenario_id, validated_rating)
        )
        
        if rows_affected == 0:
            raise RuntimeError("Failed to create rating - no rows affected")
    
    def get_all_teams_secure(self) -> List[Tuple[int, str]]:
        """
        Get all teams from database securely
        
        Returns:
            List of (team_id, team_name) tuples
        """
        query = "SELECT team_id, team_name FROM teams ORDER BY team_name"
        return self.query_parameterized(query)
    
    def get_all_scenarios_secure(self) -> List[Tuple[int, str]]:
        """
        Get all scenarios from database securely
        
        Returns:
            List of (scenario_id, scenario_name) tuples
        """
        query = "SELECT scenario_id, scenario_name FROM scenarios ORDER BY scenario_name"
        return self.query_parameterized(query)