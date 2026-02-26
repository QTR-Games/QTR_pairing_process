""" © Daniel P Raven 2024 All Rights Reserved """
from qtr_pairing_process.ui_manager import UiManager
from qtr_pairing_process.constants import DEFAULT_COLOR_MAP, SCENARIO_MAP, DIRECTORY, SCENARIO_RANGES, SCENARIO_TO_CSV_MAP

if __name__ == '__main__':
    ui_manager = UiManager(color_map=DEFAULT_COLOR_MAP, scenario_map=SCENARIO_MAP, directory=DIRECTORY, scenario_ranges=SCENARIO_RANGES, scenario_to_csv_map=SCENARIO_TO_CSV_MAP)
    ui_manager.create_ui()