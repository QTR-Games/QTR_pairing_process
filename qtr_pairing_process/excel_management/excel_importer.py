
import openpxyl
from qtr_pairing_process.excel_management.constants import SHEET_NAMES
class ExcelImporter:
    def __init__(self):
        self.workbook = None
        self.team_metadata = {}

    def read_excel_file(self, file_path, file_name):
        self.workbook = openpxyl.load_workbook(filename = file_name)

    def validate_sheetnames(self):
        workbook_sheet_names = self.workbook.sheetnames
        for sn in SHEET_NAMES:
            if sn not in workbook_sheet_names:
                print(f'Sheet {sn} not found')

    def validate_and_assign_team(self, team_position, team_name, player_names):
        if not isinstance(team_name, str) or team_name=='':
            print(f'Invalid team name for {team_position}: {team_name}')
        for player_name in player_names:
            if not isinstance(player_name, str) or player_name=='':
                print(f'Invalid player_name for {team_position}: {player_name}')

        team_dict = {
            'team_name': team_name,
            'player_names': player_names
        }
        self.team_metadata[team_position] = team_dict

    def validate_team_sheet(self, team_sheet):
        team1 = [x[0].value for x in team_sheet['A1':'A6']]
        team1_name = team1[0]
        team1_players = team1[1:]
        self.validate_and_assign_team('team1',team1_name, team1_players)

        team2 = [x[0].value for x in team_sheet['B1':'B6']]
        team2_name = team2[0]
        team2_players = team2[1:]
        self.validate_and_assign_team('team2',team2_name, team2_players)

    def validate_ranking_sheets(self):
        for sheet_name in SHEET_NAMES[1:]:
            self.validate_ranking_sheet_players(sheet_name)
            self.validate_ranking_sheet_ranks(sheet_name)
    def validate_ranking_sheet_players(self, sheet_name):
        sheet = self.workbook[sheet_name]
        team1_ranking_players = [x[0].value for x in sheet['A2':'A6']]
        team2_ranking_players = [x.value for x in sheet['B1':'F1'][0]]

        if team1_ranking_players != self.team_metadata['team1']['player_names']:
            print(f'Varying team row names between team sheet and sheet_name {sheet_name}.')

        if team2_ranking_players != self.team_metadata['team2']['player_names']:
            print(f'Varying team column names between team sheet and sheet_name {sheet_name}.')
    def validate_ranking_sheet_ranks(self, sheet_name):
        sheet = self.workbook[sheet_name]
        grid_ranks = sheet['B2':'F6']
        for row in grid_ranks:
            for col in row:
                if not isinstance(col.value,int):
                    print(f'Not a valid value for ranking: {col.value}')
                elif col.value < 1 or col.value > 5:
                    print(f'Bad value {col.value} for rank, should be in range 1-5.')

    def import_data(self):