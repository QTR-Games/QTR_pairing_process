""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """
import sqlite3
from os.path import expanduser
import os

from qtr_pairing_process.constants import SCENARIO_MAP

class DbManager:
    def __init__(self, path=None, name=None) -> None:
        self.path = path or expanduser("~")
        self.name = name or 'default.db'
        print(self.path, self.name)
        self.initialize_db()
    def initialize_db(self):
        if not os.path.isfile(f'{self.path}/{self.name}'):
            self.create_tables()
            self.create_default_teams()
            self.create_default_scenarios()
            self.create_default_players()
            self.create_default_ratings()
    def connect_db(self, path, name):
        return sqlite3.connect(f'{path}/{name}')
    
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
    
    def insert_row(self, value_string, columns, table):
        insert_sql = f"""
            INSERT INTO {table}
            ({','.join(columns)})
            VALUES
            {value_string}
        """
        rows_affected = self.execute_sql(insert_sql)
        if rows_affected == 0:
            raise ValueError(f'insert_row operation failed for table {table}. No rows were affected.')

    def upsert_row(self, value_string, columns, table, constraint_columns, update_column):
        upsert_sql = f"""
            INSERT INTO {table}
            ({','.join(columns)})
            VALUES
            {value_string}
            ON CONFLICT({','.join(constraint_columns)})
            DO UPDATE SET
            {update_column} = excluded.{update_column}
        """
        # print(f"sql statement: {upsert_sql}")
        rows_affected = self.execute_sql(upsert_sql)
        if rows_affected == 0:
            raise ValueError(f'upsert_row operation failed for table {table}. No rows were affected.')

    ###########
    # Scenarios
    ###########
    def create_scenario(self, scenario_id, scenario_name):
        table = 'scenarios'
        columns = ['scenario_id', 'scenario_name']
        value_string = f"({scenario_id}, '{scenario_name}')"
        self.insert_row(value_string, columns, table)

    def query_scenario_id(self, scenario_name):
        sql = f"SELECT scenario_id FROM scenarios WHERE scenario_name = '{scenario_name}'"
        results = self.query_sql(sql)
        print(f"query_scenario_id results {results}")
        if len(results) > 1:
            raise ValueError(f'Too Many Records for scenario {scenario_name}')
        elif len(results) == 1:
            scenario_id = results[0][0]
        else:
            scenario_id = None
        return scenario_id
    
    def insert_scenarios(self):
        for num, desc in SCENARIO_MAP.items():
            self.upsert_scenario(num, desc)

    def upsert_scenario(self, scenario_id, scenario_name):
        table = 'scenarios'
        columns = ['scenario_id', 'scenario_name']
        value_string = f"({scenario_id}, '{scenario_name}')"
        constraint_columns = ['scenario_id']
        update_column = 'scenario_name'
        self.upsert_row(value_string, columns, table, constraint_columns, update_column)

    #######
    # Teams
    #######
    def create_team(self, team_name):
        table = 'teams'
        columns = ['team_name']
        value_string = f"('{team_name}')"
        self.insert_row(value_string, columns, table)

    def query_team_id(self, team_name):
        sql = f"select team_id from teams where team_name = '{team_name}'"
        results = self.query_sql(sql)
        
        if len(results)>1:
            raise ValueError(f'Too Many Records for team {team_name}')
        elif len(results) == 1:
            team_id = results[0][0]
        else:
            team_id = None
        return team_id

    def upsert_team(self, team_name):
        team_id = self.query_team_id(team_name)
        if not team_id:
            self.create_team(team_name=team_name)
            team_id = self.query_team_id(team_name=team_name)
            if not team_id:
                raise ValueError('Team Not Upserting')
        return team_id
            
    #########
    # Players
    #########
    def create_player(self, player_name, team_id):
        table = 'players'
        columns = ['player_name', 'team_id']
        value_string = f"('{player_name}', {team_id})"
        self.insert_row(value_string, columns, table)

    def query_players(self, team_id):
        sql = f"SELECT player_id, player_name FROM players WHERE team_id = '{team_id}' ORDER BY player_id"
        results = self.query_sql(sql)
        
        if len(results) > 5 or (len(results) > 0 and len(results) < 5):
            raise ValueError(f'Invalid Number of Player Records for team {team_id}')
        elif len(results) == 5:
            players = results
        else:
            players = None
        return players

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
        value_string = f"({player_id_1}, {team_id_1}, {player_id_2}, {team_id_2}, {scenario_id}, {rating})"
        constraint_columns = ['team_1_player_id', 'team_2_player_id', 'scenario_id']
        update_column = 'rating'
        self.upsert_row(value_string, columns, table, constraint_columns, update_column)
        
    def create_tables(self):
        path = 'qtr_pairing_process/db_management/sql'
        files = os.listdir(path)

        for file in files:
            with open(f'{path}/{file}', 'r') as file_read:
                sql= file_read.read()
                rows_affected = self.execute_sql(sql)
                if rows_affected == 0:
                    raise ValueError(f'create_tables operation failed. No rows were affected.')

    def create_default_teams(self):
        self.create_team('default_team_1')
        self.create_team('default_team_2')

    def create_default_scenarios(self):
        self.create_scenario(0,'0 - Neutral')
        self.create_scenario(1,'1 - Recon')
        self.create_scenario(2,'2 - Battle Lines')
        self.create_scenario(3,'3 - Wolves At Our Heels')
        self.create_scenario(4,'4 - Payload')
        self.create_scenario(5,'5 - Two Fronts')
        self.create_scenario(6,'6 - Invasion')

    def create_default_players(self):
        for i in range(1,3):
            for j in range(1,6):
                self.create_player(f'default_player_{i}_{j}',i)

    def create_default_ratings(self):
        team_1 = self.query_sql('select player_id, team_id from players where team_id=1')
        team_2 = self.query_sql('select player_id, team_id from players where team_id=2')
        print(f"team_1 - {team_1}")
        print(f"team_2 - {team_2}")
        for scenario_id in SCENARIO_MAP.keys():
            for player_1_row in team_1:
                for player_2_row in team_2:
                    self.upsert_rating(
                        player_id_1=player_1_row[0],
                        team_id_1=player_1_row[1],
                        player_id_2=player_2_row[0],
                        team_id_2=player_2_row[1],
                        scenario_id=scenario_id,
                        rating=player_1_row[0]**2 + player_2_row[0]**2
                    )
