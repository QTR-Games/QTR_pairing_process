""" © Daniel P Raven 2024 All Rights Reserved """
import argparse

from qtr_pairing_process.ui_manager_v2 import UiManager
from qtr_pairing_process.constants import DEFAULT_COLOR_MAP, SCENARIO_MAP, DIRECTORY, SCENARIO_RANGES, SCENARIO_TO_CSV_MAP

if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=True)
    perf_group = parser.add_mutually_exclusive_group()
    perf_group.add_argument("--perf", action="store_true", help="Enable UI performance logging")
    perf_group.add_argument("--no-perf", action="store_true", help="Disable UI performance logging")
    args, _ = parser.parse_known_args()

    perf_enabled = False
    if args.perf:
        perf_enabled = True
    elif args.no_perf:
        perf_enabled = False

    ui_manager = UiManager(
        color_map=DEFAULT_COLOR_MAP,
        scenario_map=SCENARIO_MAP,
        directory=DIRECTORY,
        scenario_ranges=SCENARIO_RANGES,
        scenario_to_csv_map=SCENARIO_TO_CSV_MAP,
        perf_enabled=perf_enabled
    )
    ui_manager.create_ui()