""" © Daniel P Raven 2024 All Rights Reserved """
import json
import sys

from qtr_pairing_process.constants import DEFAULT_COLOR_MAP, SCENARIO_MAP, DIRECTORY, SCENARIO_RANGES, SCENARIO_TO_CSV_MAP
from qtr_pairing_process.app_logger import get_logger
from qtr_pairing_process.tk_runtime_guard import run_tk_preflight


def _log_and_report_tk_failure(logger, error_message, details):
    logger.critical("Tk runtime preflight failed: %s", error_message)
    logger.critical("Tk runtime diagnostics: %s", json.dumps(details, ensure_ascii=False, default=str))
    print("\nQTR startup blocked: Tk runtime is unavailable on this machine.")
    print("Please install Python with Tcl/Tk support (python.org installer) and recreate the project environment.")
    print("Developer diagnostics were written to qtr_pairing_process.log.")

if __name__ == '__main__':
    logger = get_logger(__name__)
    tk_ok, tk_error, tk_details = run_tk_preflight()
    if not tk_ok:
        _log_and_report_tk_failure(logger, tk_error, tk_details)
        sys.exit(2)

    from qtr_pairing_process.ui_manager_v2 import UiManager

    ui_manager = UiManager(color_map=DEFAULT_COLOR_MAP, scenario_map=SCENARIO_MAP, directory=DIRECTORY, scenario_ranges=SCENARIO_RANGES, scenario_to_csv_map=SCENARIO_TO_CSV_MAP)
    ui_manager.create_ui()
    