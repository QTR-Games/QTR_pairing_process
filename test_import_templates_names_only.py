from types import SimpleNamespace
from typing import Any, cast
import csv
import io
import zipfile
from contextlib import contextmanager

import openpyxl
import pytest

from qtr_pairing_process.constants import SCENARIO_MAP
from qtr_pairing_process.ui_manager_v2 import UiManager


def test_neutral_rating_value_midpoints():
    assert UiManager._neutral_rating_value(cast(Any, SimpleNamespace(rating_range=(1, 3)))) == 2
    assert UiManager._neutral_rating_value(cast(Any, SimpleNamespace(rating_range=(1, 5)))) == 3
    assert UiManager._neutral_rating_value(cast(Any, SimpleNamespace(rating_range=(1, 10)))) == 5


def test_single_team_csv_template_layout_uses_neutral_rating():
    dummy = SimpleNamespace(rating_range=(1, 5))
    dummy._neutral_rating_value = lambda: UiManager._neutral_rating_value(cast(Any, dummy))
    rows = UiManager._build_single_team_csv_template_rows(cast(Any, dummy))

    assert rows[0][0] == "Friendly Team Example"
    assert rows[1][0] == "Opponent Team Example"

    expected_rows = 2 + (len(SCENARIO_MAP) * 6)
    assert len(rows) == expected_rows

    first_scenario_header = rows[2]
    assert first_scenario_header[0] == min(SCENARIO_MAP.keys())

    first_rating_row = rows[3]
    assert first_rating_row[0] == "Friendly 1"
    assert first_rating_row[1:] == [3, 3, 3, 3, 3]


def test_names_only_csv_loader_parses_rows(tmp_path):
    file_path = tmp_path / "names_only.csv"
    file_path.write_text(
        "team_name,player_1,player_2,player_3,player_4,player_5\n"
        "Team Alpha,A1,A2,A3,A4,A5\n"
        "Team Bravo,B1,B2,B3,B4,B5\n",
        encoding="utf-8",
    )

    rows = UiManager._load_names_only_csv_rows(cast(Any, SimpleNamespace()), str(file_path))

    assert len(rows) == 2
    assert rows[0]["team_name"] == "Team Alpha"
    assert rows[0]["player_names"] == ["A1", "A2", "A3", "A4", "A5"]
    assert rows[1]["team_name"] == "Team Bravo"


def test_names_only_csv_loader_rejects_short_rows(tmp_path):
    file_path = tmp_path / "names_only_invalid.csv"
    file_path.write_text(
        "team_name,player_1,player_2\n"
        "Team Alpha,A1,A2\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc_info:
        UiManager._load_names_only_csv_rows(cast(Any, SimpleNamespace()), str(file_path))

    assert "expected 6 columns" in str(exc_info.value)


class _FakeVar:
    def __init__(self, value=0):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _FakeWidget:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def pack(self, *args, **kwargs):
        return None

    def pack_forget(self, *args, **kwargs):
        return None

    def grid(self, *args, **kwargs):
        return None

    def config(self, *args, **kwargs):
        self.kwargs.update(kwargs)
        return None

    def configure(self, *args, **kwargs):
        self.kwargs.update(kwargs)
        return None

    def title(self, *args, **kwargs):
        return None

    def geometry(self, *args, **kwargs):
        return None

    def minsize(self, *args, **kwargs):
        return None

    def resizable(self, *args, **kwargs):
        return None

    def transient(self, *args, **kwargs):
        return None

    def grab_set(self, *args, **kwargs):
        return None

    def destroy(self, *args, **kwargs):
        return None

    def grid_columnconfigure(self, *args, **kwargs):
        return None

    def grid_rowconfigure(self, *args, **kwargs):
        return None


class _FakeRoot:
    def winfo_x(self):
        return 0

    def winfo_y(self):
        return 0


def test_data_management_menu_wires_new_buttons(monkeypatch):
    created_buttons = []
    invoked = {"import_templates": 0, "import_names_only": 0}

    class _FakeButton(_FakeWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created_buttons.append(self)

    monkeypatch.setattr("tkinter.Toplevel", _FakeWidget)
    monkeypatch.setattr("tkinter.Frame", _FakeWidget)
    monkeypatch.setattr("tkinter.Label", _FakeWidget)
    monkeypatch.setattr("tkinter.Button", _FakeButton)
    monkeypatch.setattr("tkinter.Checkbutton", _FakeWidget)
    monkeypatch.setattr("tkinter.IntVar", _FakeVar)
    monkeypatch.setattr("tkinter.BooleanVar", _FakeVar)
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *args, **kwargs: None)

    dummy = SimpleNamespace(
        root=_FakeRoot(),
        data_mgmt_show_guides_logs=False,
        data_mgmt_show_advanced_settings=False,
        db_preferences=SimpleNamespace(update_ui_preferences=lambda *args, **kwargs: None),
        tree_autogen_var=_FakeVar(0),
        lazy_sort_on_expand_var=_FakeVar(0),
        perf_logging_enabled=False,
        _is_persistent_strategic_memo_enabled=lambda: False,
        _on_perf_logging_toggle=lambda: None,
        _on_tree_autogen_toggle=lambda: None,
        _on_lazy_sort_toggle=lambda: None,
        _on_persistent_memo_toggle=lambda: None,
        clear_generated_tree_cache_active_matchup=lambda: None,
        clear_generated_tree_cache_all_matchups=lambda: None,
        open_tooltip_numbers_guide=lambda reopen_data_management_on_close=False: None,
        open_full_user_guide=lambda reopen_data_management_on_close=False: None,
        open_import_logs_folder=lambda: None,
        on_create_team=lambda: None,
        on_modify_team=lambda: None,
        on_delete_team=lambda: None,
        on_change_database=lambda: None,
        on_configure_rating_system=lambda: None,
        import_csvs=lambda: None,
        export_csvs=lambda: None,
        import_xlsx=lambda: None,
        export_xlsx=lambda: None,
        export_individual_player_ratings=lambda: None,
        import_individual_player_ratings=lambda: None,
        bulk_import_individual_player_ratings=lambda: None,
        import_names_only_csv=lambda: invoked.__setitem__("import_names_only", invoked["import_names_only"] + 1),
        show_import_templates_popup=lambda: invoked.__setitem__("import_templates", invoked["import_templates"] + 1),
        _menu_action=lambda _menu, action, reopen_data_management_on_complete=False: action(),
        _operation_failed_error=lambda s: s,
    )

    UiManager.show_data_management_menu(cast(Any, dummy))

    button_by_text = {
        button.kwargs.get("text"): button
        for button in created_buttons
        if button.kwargs.get("text")
    }

    assert "Import Names Only" in button_by_text
    assert "Import Templates" in button_by_text

    button_by_text["Import Names Only"].kwargs["command"]()
    button_by_text["Import Templates"].kwargs["command"]()

    assert invoked["import_names_only"] == 1
    assert invoked["import_templates"] == 1


def test_download_all_templates_zip_contains_expected_files(monkeypatch, tmp_path):
    zip_path = tmp_path / "templates.zip"
    info_calls = []

    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.filedialog.asksaveasfilename",
        lambda **kwargs: str(zip_path),
    )
    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.messagebox.showinfo",
        lambda title, message: info_calls.append((title, message)),
    )

    dummy = SimpleNamespace(rating_range=(1, 5), _operation_notice_info=lambda s: s)
    for method_name in [
        "_neutral_rating_value",
        "_build_single_team_csv_template_rows",
        "_build_multiple_team_csv_template_rows",
        "_build_names_only_csv_template_rows",
        "_build_xlsx_template_bytes",
        "_write_csv_rows",
        "_write_binary_file",
        "_template_specs",
    ]:
        setattr(dummy, method_name, getattr(UiManager, method_name).__get__(dummy, UiManager))

    UiManager._download_all_templates_zip(cast(Any, dummy))

    assert zip_path.exists()
    assert info_calls

    with zipfile.ZipFile(zip_path, "r") as archive:
        names = sorted(archive.namelist())
        assert names == [
            "multiple_team_import_template.csv",
            "multiple_team_import_template.xlsx",
            "names_only_import_template.csv",
            "single_team_import_template.csv",
            "single_team_import_template.xlsx",
        ]

        names_only_rows = list(csv.reader(io.StringIO(archive.read("names_only_import_template.csv").decode("utf-8"))))
        assert names_only_rows[0] == ["team_name", "player_1", "player_2", "player_3", "player_4", "player_5"]

        workbook = openpyxl.load_workbook(io.BytesIO(archive.read("single_team_import_template.xlsx")))
        sheet = workbook["ImportReady"]
        assert sheet["A1"].value == "Friendly Team Example"
        workbook.close()


def test_show_import_templates_popup_buttons_route_to_handlers(monkeypatch):
    created_buttons = []
    invoked = {
        "single_team_xlsx": 0,
        "single_team_csv": 0,
        "multiple_team_xlsx": 0,
        "multiple_team_csv": 0,
        "names_only": 0,
        "zip": 0,
    }

    class _FakeButton(_FakeWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created_buttons.append(self)

    monkeypatch.setattr("qtr_pairing_process.ui_manager_v2.tk.Toplevel", _FakeWidget)
    monkeypatch.setattr("qtr_pairing_process.ui_manager_v2.tk.Label", _FakeWidget)
    monkeypatch.setattr("qtr_pairing_process.ui_manager_v2.tk.Frame", _FakeWidget)
    monkeypatch.setattr("qtr_pairing_process.ui_manager_v2.tk.Button", _FakeButton)

    dummy = SimpleNamespace(
        root=_FakeRoot(),
        _download_template=lambda key: invoked.__setitem__(key, invoked[key] + 1),
        _download_all_templates_zip=lambda: invoked.__setitem__("zip", invoked["zip"] + 1),
    )

    UiManager.show_import_templates_popup(cast(Any, dummy))

    buttons_by_text = {
        button.kwargs.get("text"): button
        for button in created_buttons
        if button.kwargs.get("text")
    }

    for label in [
        "Single Team Import XLSX",
        "Single Team Import CSV",
        "Multiple Team Import XLSX",
        "Multiple Team Import CSV",
        "Names Only",
        "Download All (ZIP)",
    ]:
        assert label in buttons_by_text

    buttons_by_text["Single Team Import XLSX"].kwargs["command"]()
    buttons_by_text["Single Team Import CSV"].kwargs["command"]()
    buttons_by_text["Multiple Team Import XLSX"].kwargs["command"]()
    buttons_by_text["Multiple Team Import CSV"].kwargs["command"]()
    buttons_by_text["Names Only"].kwargs["command"]()
    buttons_by_text["Download All (ZIP)"].kwargs["command"]()

    assert invoked["single_team_xlsx"] == 1
    assert invoked["single_team_csv"] == 1
    assert invoked["multiple_team_xlsx"] == 1
    assert invoked["multiple_team_csv"] == 1
    assert invoked["names_only"] == 1
    assert invoked["zip"] == 1


def test_download_template_single_team_csv_writes_file(monkeypatch, tmp_path):
    file_path = tmp_path / "single_team.csv"
    info_calls = []

    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.filedialog.asksaveasfilename",
        lambda **kwargs: str(file_path),
    )
    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.messagebox.showinfo",
        lambda title, message: info_calls.append((title, message)),
    )

    dummy = SimpleNamespace(rating_range=(1, 5), _operation_notice_info=lambda s: s)
    for method_name in [
        "_neutral_rating_value",
        "_build_single_team_csv_template_rows",
        "_build_multiple_team_csv_template_rows",
        "_build_names_only_csv_template_rows",
        "_build_xlsx_template_bytes",
        "_write_csv_rows",
        "_write_binary_file",
        "_template_specs",
    ]:
        setattr(dummy, method_name, getattr(UiManager, method_name).__get__(dummy, UiManager))

    UiManager._download_template(cast(Any, dummy), "single_team_csv")

    assert file_path.exists()
    rows = list(csv.reader(file_path.read_text(encoding="utf-8").splitlines()))
    assert rows[0][0] == "Friendly Team Example"
    assert rows[1][0] == "Opponent Team Example"
    assert info_calls


def test_download_template_rejects_unknown_key():
    dummy = SimpleNamespace(_template_specs=lambda: {})
    with pytest.raises(ValueError):
        UiManager._download_template(cast(Any, dummy), "does_not_exist")


class _TrackingNamesOnlyDb:
    def __init__(self):
        self._next_team_id = 2
        self.teams = {"Friendly Team": 1}
        self.players_by_team = {
            1: [(10, "F1"), (11, "F2"), (12, "F3"), (13, "F4"), (14, "F5")],
        }
        self.player_id_by_name_team = {
            ("F1", 1): 10,
            ("F2", 1): 11,
            ("F3", 1): 12,
            ("F4", 1): 13,
            ("F5", 1): 14,
        }
        self._next_player_id = 100
        self.upsert_ratings_calls = []

    def query_players(self, team_id):
        return self.players_by_team.get(team_id)

    def query_team_id(self, team_name):
        return self.teams.get(team_name)

    def upsert_team(self, team_name):
        existing = self.teams.get(team_name)
        if existing is not None:
            return existing
        team_id = self._next_team_id
        self._next_team_id += 1
        self.teams[team_name] = team_id
        return team_id

    def upsert_and_validate_players(self, team_id, player_names):
        existing = self.players_by_team.get(team_id)
        if existing is None:
            rows = []
            for player_name in player_names:
                player_id = self._next_player_id
                self._next_player_id += 1
                rows.append((player_id, player_name))
                self.player_id_by_name_team[(player_name, team_id)] = player_id
            self.players_by_team[team_id] = rows
            return rows
        existing_names = [name for _, name in existing]
        if existing_names != list(player_names):
            raise ValueError("Players differ between existing team and queried team")
        return existing

    def query_player_id(self, player_name, team_id):
        return self.player_id_by_name_team.get((player_name, team_id))

    def upsert_rating(self, player_id_1, player_id_2, team_id_1, team_id_2, scenario_id, rating):
        self.upsert_ratings_calls.append(
            (player_id_1, player_id_2, team_id_1, team_id_2, scenario_id, rating)
        )


def _names_only_dummy_ui(db):
    @contextmanager
    def _busy(_label):
        yield

    dummy = SimpleNamespace(
        db_manager=db,
        rating_range=(1, 10),
        logger=SimpleNamespace(info=lambda *args, **kwargs: None, exception=lambda *args, **kwargs: None),
        _busy_ui_operation=_busy,
        _get_selected_friendly_team=lambda: (1, "Friendly Team"),
        _invalidate_team_cache=lambda *args, **kwargs: None,
        _invalidate_comment_cache=lambda *args, **kwargs: None,
        load_grid_data_from_db=lambda refresh_ui=True: None,
        data_cache=SimpleNamespace(invalidate_ratings_cache=lambda: None),
        _build_import_report=lambda operation, status, details=None, exc=None: {
            "operation": operation,
            "status": status,
            "details": details or {},
            "exc": str(exc) if exc else "",
        },
        _write_import_diagnostic_report=lambda report: "diagnostic.json",
        _operation_notice_info=lambda s: s,
        _operation_failed_error=lambda s: s,
    )
    for method_name in ["_load_names_only_csv_rows", "_neutral_rating_value", "_resolve_or_create_matchup_team"]:
        setattr(dummy, method_name, getattr(UiManager, method_name).__get__(dummy, UiManager))
    return dummy


def test_import_names_only_csv_end_to_end_success(monkeypatch, tmp_path):
    file_path = tmp_path / "names_only_import.csv"
    file_path.write_text(
        "team_name,player_1,player_2,player_3,player_4,player_5\n"
        "Team Alpha,A1,A2,A3,A4,A5\n"
        "Team Bravo,B1,B2,B3,B4,B5\n",
        encoding="utf-8",
    )

    info_calls = []
    error_calls = []
    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.filedialog.askopenfilename",
        lambda **kwargs: str(file_path),
    )
    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.messagebox.showinfo",
        lambda title, message: info_calls.append((title, message)),
    )
    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.messagebox.showerror",
        lambda title, message: error_calls.append((title, message)),
    )

    db = _TrackingNamesOnlyDb()
    dummy = _names_only_dummy_ui(db)

    UiManager.import_names_only_csv(cast(Any, dummy))

    assert not error_calls
    assert info_calls
    assert "Imported teams: 2" in info_calls[0][1]
    assert "Neutral rating used: 5" in info_calls[0][1]

    expected_calls = 2 * 5 * 5 * len(SCENARIO_MAP)
    assert len(db.upsert_ratings_calls) == expected_calls
    assert all(call[2] == 1 for call in db.upsert_ratings_calls)
    assert all(call[5] == 5 for call in db.upsert_ratings_calls)


def test_import_names_only_csv_partial_failure_with_friendly_team_row(monkeypatch, tmp_path):
    file_path = tmp_path / "names_only_partial.csv"
    file_path.write_text(
        "team_name,player_1,player_2,player_3,player_4,player_5\n"
        "Friendly Team,F1,F2,F3,F4,F5\n"
        "Team Delta,D1,D2,D3,D4,D5\n",
        encoding="utf-8",
    )

    info_calls = []
    error_calls = []
    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.filedialog.askopenfilename",
        lambda **kwargs: str(file_path),
    )
    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.messagebox.showinfo",
        lambda title, message: info_calls.append((title, message)),
    )
    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.messagebox.showerror",
        lambda title, message: error_calls.append((title, message)),
    )

    db = _TrackingNamesOnlyDb()
    dummy = _names_only_dummy_ui(db)

    UiManager.import_names_only_csv(cast(Any, dummy))

    assert not error_calls
    assert info_calls
    assert "Imported teams: 1" in info_calls[0][1]
    assert "Some rows failed" in info_calls[0][1]


def test_import_names_only_csv_all_rows_fail_shows_error(monkeypatch, tmp_path):
    file_path = tmp_path / "names_only_fail.csv"
    file_path.write_text(
        "team_name,player_1,player_2,player_3,player_4,player_5\n"
        "Friendly Team,F1,F2,F3,F4,F5\n",
        encoding="utf-8",
    )

    info_calls = []
    error_calls = []
    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.filedialog.askopenfilename",
        lambda **kwargs: str(file_path),
    )
    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.messagebox.showinfo",
        lambda title, message: info_calls.append((title, message)),
    )
    monkeypatch.setattr(
        "qtr_pairing_process.ui_manager_v2.messagebox.showerror",
        lambda title, message: error_calls.append((title, message)),
    )

    db = _TrackingNamesOnlyDb()
    dummy = _names_only_dummy_ui(db)

    UiManager.import_names_only_csv(cast(Any, dummy))

    assert not info_calls
    assert error_calls
    assert "could not import names-only CSV" in error_calls[0][1]


def test_names_only_csv_loader_supports_headerless_rows(tmp_path):
    file_path = tmp_path / "headerless.csv"
    file_path.write_text(
        "Team One,A1,A2,A3,A4,A5\n"
        "Team Two,B1,B2,B3,B4,B5\n",
        encoding="utf-8",
    )

    rows = UiManager._load_names_only_csv_rows(cast(Any, SimpleNamespace()), str(file_path))

    assert len(rows) == 2
    assert rows[0]["team_name"] == "Team One"
    assert rows[1]["team_name"] == "Team Two"


def test_names_only_csv_loader_rejects_duplicate_player_names(tmp_path):
    file_path = tmp_path / "duplicate_names.csv"
    file_path.write_text(
        "team_name,player_1,player_2,player_3,player_4,player_5\n"
        "Team Alpha,A1,A1,A3,A4,A5\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc_info:
        UiManager._load_names_only_csv_rows(cast(Any, SimpleNamespace()), str(file_path))

    assert "player names must be unique" in str(exc_info.value)
