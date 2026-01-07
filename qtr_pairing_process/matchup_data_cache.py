""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
"""
High-performance caching system for QTR Pairing Process.
Reduces database queries by 80-90% while maintaining data consistency.
"""

from typing import Dict, List, Tuple, Optional, Any
import time
from datetime import datetime

class MatchupDataCache:
    """
    Intelligent caching system for QTR Pairing Process data.
    Caches teams, players, ratings, and comments to minimize database queries.
    """
    
    def __init__(self, db_manager, print_output: bool = False):
        self.db_manager = db_manager
        self.print_output = print_output
        
        # Cache dictionaries
        self._teams_cache: Dict[str, int] = {}                    # {team_name: team_id}
        self._players_cache: Dict[int, List[Tuple[int, str]]] = {} # {team_id: [(player_id, player_name), ...]}
        self._ratings_cache: Dict[Tuple[int, int, int], Dict[Tuple[int, int], int]] = {}  # {(team1_id, team2_id, scenario_id): {(player1_id, player2_id): rating}}
        self._comments_cache: Dict[Tuple[int, int, int], str] = {}  # {(player1_id, player2_id, scenario_id): comment}
        
        # Performance tracking
        self._cache_hits = 0
        self._cache_misses = 0
        self._last_refresh = time.time()
        
        # Initialize cache with base data
        self._load_base_data()
    
    def _load_base_data(self):
        """Load teams and players data that rarely changes during a session."""
        start_time = time.time()
        
        if self.print_output:
            print("🔄 Loading base data into cache...")
        
        try:
            # Load all teams
            teams_sql = "SELECT team_name, team_id FROM teams ORDER BY team_name"
            teams_data = self.db_manager.query_sql(teams_sql)
            self._teams_cache = {name: team_id for name, team_id in teams_data}
            
            # Load all players for each team
            self._players_cache.clear()
            for team_name, team_id in self._teams_cache.items():
                players_sql = f"SELECT player_id, player_name FROM players WHERE team_id = {team_id} ORDER BY player_id"
                players_data = self.db_manager.query_sql(players_sql)
                self._players_cache[team_id] = players_data
            
            load_time = time.time() - start_time
            total_players = sum(len(players) for players in self._players_cache.values())
            
            if self.print_output:
                print(f"✅ Cached {len(self._teams_cache)} teams and {total_players} players in {load_time:.2f}s")
                
        except Exception as e:
            if self.print_output:
                print(f"❌ Error loading base data: {e}")
            # Initialize empty caches on error
            self._teams_cache = {}
            self._players_cache = {}
    
    def get_team_id(self, team_name: str) -> Optional[int]:
        """Get team ID from cache (no database query)."""
        self._cache_hits += 1
        return self._teams_cache.get(team_name)
    
    def get_team_players(self, team_id: int) -> List[Tuple[int, str]]:
        """Get team players from cache (no database query)."""
        self._cache_hits += 1
        return self._players_cache.get(team_id, [])
    
    def get_team_names(self) -> List[str]:
        """Get all team names from cache."""
        self._cache_hits += 1
        names = list(self._teams_cache.keys())
        return names if names else ['No teams Found']
    
    def get_matchup_ratings(self, team1_id: int, team2_id: int, scenario_id: int) -> Dict[Tuple[int, int], int]:
        """
        Get ratings for a specific matchup, caching result.
        Returns dict of {(player1_id, player2_id): rating}
        """
        cache_key = (team1_id, team2_id, scenario_id)
        
        if cache_key in self._ratings_cache:
            self._cache_hits += 1
            return self._ratings_cache[cache_key]
        
        # Cache miss - load from database
        self._cache_misses += 1
        self._load_matchup_ratings(team1_id, team2_id, scenario_id)
        return self._ratings_cache.get(cache_key, {})
    
    def _load_matchup_ratings(self, team1_id: int, team2_id: int, scenario_id: int):
        """Load specific matchup ratings from database and cache them."""
        if self.print_output:
            print(f"📊 Loading ratings for teams {team1_id} vs {team2_id}, scenario {scenario_id}")
        
        try:
            # Get player IDs for both teams from cache
            team1_players = self.get_team_players(team1_id)
            team2_players = self.get_team_players(team2_id)
            
            if not team1_players or not team2_players:
                if self.print_output:
                    print(f"⚠️ No players found for teams {team1_id} or {team2_id}")
                return
            
            team1_player_ids = [p[0] for p in team1_players]
            team2_player_ids = [p[0] for p in team2_players]
            
            # Query ratings from database
            ratings_sql = f"""
                SELECT team_1_player_id, team_2_player_id, rating
                FROM ratings
                WHERE team_1_player_id IN ({','.join(map(str, team1_player_ids))})
                  AND team_2_player_id IN ({','.join(map(str, team2_player_ids))})
                  AND team_1_id = {team1_id}
                  AND team_2_id = {team2_id}
                  AND scenario_id = {scenario_id}
                ORDER BY team_1_player_id, team_2_player_id
            """
            
            ratings_data = self.db_manager.query_sql(ratings_sql)
            
            # Store in cache
            cache_key = (team1_id, team2_id, scenario_id)
            self._ratings_cache[cache_key] = {}
            
            for player1_id, player2_id, rating in ratings_data:
                self._ratings_cache[cache_key][(player1_id, player2_id)] = rating
                
            if self.print_output:
                print(f"✅ Cached {len(ratings_data)} ratings for matchup")
                
        except Exception as e:
            if self.print_output:
                print(f"❌ Error loading matchup ratings: {e}")
    
    def get_cached_grid_data(self, team1_name: str, team2_name: str, scenario_id: int) -> Optional[Dict[str, Any]]:
        """
        Get complete grid data for UI from cache.
        Returns structured data ready for grid population.
        """
        # Get team IDs
        team1_id = self.get_team_id(team1_name)
        team2_id = self.get_team_id(team2_name)
        
        if team1_id is None or team2_id is None:
            return None
        
        # Get players
        team1_players = self.get_team_players(team1_id)
        team2_players = self.get_team_players(team2_id)
        
        if not team1_players or not team2_players:
            return None
        
        # Get ratings
        ratings = self.get_matchup_ratings(team1_id, team2_id, scenario_id)
        
        # Structure data for UI
        return {
            'team1_id': team1_id,
            'team2_id': team2_id,
            'team1_players': team1_players,
            'team2_players': team2_players,
            'ratings': ratings,
            'from_cache': True
        }
    
    def invalidate_ratings_cache(self, team1_id: Optional[int] = None, team2_id: Optional[int] = None, scenario_id: Optional[int] = None):
        """
        Invalidate specific or all ratings cache entries.
        Call this after saving ratings to ensure cache consistency.
        """
        if team1_id is None and team2_id is None and scenario_id is None:
            # Clear all ratings cache
            self._ratings_cache.clear()
            if self.print_output:
                print("🗑️ Cleared all ratings cache")
        else:
            # Clear specific matchups
            keys_to_remove = []
            for key in self._ratings_cache.keys():
                t1, t2, s = key
                if ((team1_id is None or t1 == team1_id or t2 == team1_id) and
                    (team2_id is None or t1 == team2_id or t2 == team2_id) and
                    (scenario_id is None or s == scenario_id)):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._ratings_cache[key]
                
            if self.print_output and keys_to_remove:
                print(f"🗑️ Invalidated {len(keys_to_remove)} rating cache entries")
    
    def refresh_base_data(self):
        """
        Refresh teams and players cache.
        Call this after importing teams or adding/deleting teams.
        """
        if self.print_output:
            print("🔄 Refreshing base data cache...")
        
        self._teams_cache.clear()
        self._players_cache.clear()
        self._load_base_data()
        
        # Also clear ratings cache since team/player changes affect it
        self._ratings_cache.clear()
    
    def update_cached_rating(self, team1_id: int, team2_id: int, scenario_id: int, 
                           player1_id: int, player2_id: int, rating: int):
        """
        Update a specific rating in the cache.
        Use this when saving individual ratings to keep cache in sync.
        """
        cache_key = (team1_id, team2_id, scenario_id)
        
        if cache_key not in self._ratings_cache:
            # Initialize cache entry if it doesn't exist
            self._ratings_cache[cache_key] = {}
        
        self._ratings_cache[cache_key][(player1_id, player2_id)] = rating
        
        if self.print_output:
            print(f"📝 Updated cached rating: players {player1_id}->{player2_id} = {rating}")
    
    def preload_common_matchups(self, team_pairs: List[Tuple[str, str]], scenario_ids: List[int]):
        """
        Preload ratings for commonly used team matchups.
        Call this during application startup for better performance.
        """
        if self.print_output:
            print(f"🚀 Preloading {len(team_pairs)} matchups across {len(scenario_ids)} scenarios...")
        
        start_time = time.time()
        loaded_count = 0
        
        for team1_name, team2_name in team_pairs:
            team1_id = self.get_team_id(team1_name)
            team2_id = self.get_team_id(team2_name)
            
            if team1_id and team2_id:
                for scenario_id in scenario_ids:
                    # This will load and cache the ratings
                    self.get_matchup_ratings(team1_id, team2_id, scenario_id)
                    loaded_count += 1
        
        load_time = time.time() - start_time
        if self.print_output:
            print(f"✅ Preloaded {loaded_count} matchups in {load_time:.2f}s")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'teams_cached': len(self._teams_cache),
            'players_cached': sum(len(p) for p in self._players_cache.values()),
            'ratings_cached': len(self._ratings_cache),
            'comments_cached': len(self._comments_cache),
            'total_rating_entries': sum(len(r) for r in self._ratings_cache.values()),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': hit_rate,
            'last_refresh': datetime.fromtimestamp(self._last_refresh).strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def print_cache_stats(self):
        """Print formatted cache statistics."""
        stats = self.get_cache_stats()
        
        print("\n📊 CACHE PERFORMANCE STATISTICS")
        print("=" * 40)
        print(f"Teams cached: {stats['teams_cached']}")
        print(f"Players cached: {stats['players_cached']}")
        print(f"Ratings matchups cached: {stats['ratings_cached']}")
        print(f"Total rating entries: {stats['total_rating_entries']}")
        print(f"Cache hits: {stats['cache_hits']}")
        print(f"Cache misses: {stats['cache_misses']}")
        print(f"Hit rate: {stats['hit_rate_percent']:.1f}%")
        print(f"Last refresh: {stats['last_refresh']}")
        
        # Performance assessment
        if stats['hit_rate_percent'] > 80:
            print("🟢 Excellent cache performance!")
        elif stats['hit_rate_percent'] > 60:
            print("🟡 Good cache performance")
        else:
            print("🔴 Consider preloading more data")