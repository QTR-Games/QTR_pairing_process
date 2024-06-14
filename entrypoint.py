from qtr_pairing_process.ui_manager import UiManager
from qtr_pairing_process.constants import DEFAULT_COLOR_MAP, MATT_DIR, DAN_DIR

if __name__ == '__main__':
    ui_manager = UiManager(color_map=DEFAULT_COLOR_MAP, directory=DAN_DIR)
    ui_manager.create_ui()