
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
            self.create_default_players()
            self.create_default_ratings()
    def connect_db(self, path, name):
        return sqlite3.connect(f'{path}/{name}')
    
    def execute_sql(self, sql):
        with self.connect_db(self.path, self.name) as db_conn:
            db_cur = db_conn.cursor()
            db_cur.execute(sql)
            db_conn.commit()

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
        self.execute_sql(insert_sql)

    def upsert_row(self, value_string, columns, table, contraint_columns, update_column):
        upsert_sql = f"""
            INSERT INTO {table}
            ({','.join(columns)})
            VALUES
            {value_string}
            ON CONFLICT({','.join(contraint_columns)})
            DO UPDATE SET
            {update_column} = excluded.{update_column}

        """
        self.execute_sql(upsert_sql)

    def insert_scenarios(self):
        insert_template = "({num},'{desc}')"
        template_list = []
        for num, desc in SCENARIO_MAP.items():
            template_list.append(insert_template.format(num=num, desc=desc))
        insert_str = ',\n'.join(template_list)

        insert_sql = f"""
            INSERT INTO scenarios
            (scenario_id, scenario_name)
            VALUES
            {insert_str}
        """
        self.execute_sql(insert_sql)

    def create_team(self, team_name):
        table = 'teams'
        columns = ['team_name']
        value_string = f"('{team_name}')"
        self.insert_row(value_string, columns, table)

    def create_player(self, player_name, team_id):
        table = 'players'
        columns = ['player_name','team_id']
        value_string = f"('{player_name}', {team_id})"
        self.insert_row(value_string, columns, table)

    def upsert_rating(self, player_id_1, player_id_2, team_id_1, team_id_2, scenario_id, rating):

        if team_id_1 > team_id_2:
            team_id_1, team_id_2 = team_id_2, team_id_1
            player_id_1, player_id_2 = player_id_2, player_id_1

        table = 'ratings'
        columns = ['team_1_player_id', 'team_1_id', 'team_2_player_id', 'team_2_id','scenario_id', 'rating']
        value_string = f"({player_id_1}, {team_id_1}, {player_id_2}, {team_id_2}, {scenario_id}, {rating})"
        contraint_columns = ['team_1_player_id', 'team_2_player_id', 'scenario_id']
        update_column = 'rating'

        self.upsert_row(value_string, columns, table, contraint_columns, update_column)
    def create_tables(self):
        path = 'qtr_pairing_process/db_management/sql'
        files = os.listdir(path)

        for file in files:
            with open(f'{path}/{file}', 'r') as file_read:
                sql= file_read.read()
                self.execute_sql(sql)

    def create_default_teams(self):
        self.create_team('default_team_1')
        self.create_team('default_team_2')

    def create_default_players(self):
        for i in range(1,3):
            for j in range(1,6):
                self.create_player(f'default_player_{i}_{j}',i)

    def create_default_ratings(self):
        team_1 = self.query_sql('select player_id, team_id from players where team_id=1')
        team_2 = self.query_sql('select player_id, team_id from players where team_id=2')

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
