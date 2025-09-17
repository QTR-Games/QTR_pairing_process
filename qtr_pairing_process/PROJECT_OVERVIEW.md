# QTR_PAIRING_PROCESS

## Mission Statement

QTR_PAIRING_PROCESS is a desktop application designed to help users manage, analyze, and optimize team pairings and matchups—primarily for competitive gaming or tournament settings. The application's mission is to provide a robust, flexible, and user-friendly tool for strategizing team matchups, ensuring data integrity, and supporting efficient workflows for team captains, organizers, and analysts.

All enhancements and changes to this project should support or extend this mission.

---

## Core Features

- **Database Management**: Create or load a local SQLite database to store teams, players, scenarios, and ratings.  
  _Implemented in:_ `db_management/db_manager.py`, `db_load_ui.py`

- **Data Import (Excel/CSV)**: Import team and player data from Excel or CSV files, with validation and mapping to database tables.  
  _Implemented in:_ `excel_management/excel_importer.py`, `ui_manager.py`

- **User Interface**: Intuitive Tkinter-based UI with tabs for team grid editing and matchup tree visualization.  
  _Implemented in:_ `ui_manager.py`, `lazy_tree_view.py`, `tree_generator.py`

- **Pairing Tree Generation**: Generate and visualize all possible player matchups between two teams, including ratings and scenario-based analysis.  
  _Implemented in:_ `tree_generator.py`, `ui_manager.py`

- **Exporting Results**: Export matchup results and analyses to CSV for sharing or further analysis.  
  _Implemented in:_ `ui_manager.py`, `ui_db_funcs.py`

---

## Typical Workflow

1. **Database Setup**: On launch, the user creates or loads a database file.  
   _See:_ `db_load_ui.py`, `db_management/db_manager.py`
2. **Data Import**: User imports team/player data from Excel or CSV.  
   _See:_ `excel_management/excel_importer.py`, `ui_manager.py`
3. **Team/Player Management**: Teams and players can be viewed, edited, or deleted.  
   _See:_ `ui_manager.py`, `ui_db_funcs.py`
4. **Pairing Analysis**: The user generates all possible matchups, visualized as a tree, and can analyze/sort by various criteria.  
   _See:_ `tree_generator.py`, `ui_manager.py`
5. **Export**: Results can be exported to CSV for reporting or further analysis.  
   _See:_ `ui_manager.py`, `ui_db_funcs.py`

---

## Key Files and Their Roles

| Functionality                | File/Function(s)                                                                 |
|------------------------------|----------------------------------------------------------------------------------|
| Database setup               | `db_management/db_manager.py` (`DbManager`, `initialize_db`, `create_tables`)   |
| Excel import                 | `excel_management/excel_importer.py` (`ExcelImporter.execute`)                   |
| Main UI                      | `ui_manager.py` (`UiManager.create_ui`, `if __name__ == '__main__'`)            |
| Team/player management       | `ui_manager.py`, `ui_db_funcs.py`                                               |
| Pairing tree generation      | `tree_generator.py` (`TreeGenerator.generate_combinations`)                      |
| Exporting results            | `ui_manager.py` (`export_csvs`)                                                 |
| Scenario/team constants      | `constants.py`, `excel_management/constants.py`                                  |

---

## Contribution Guidelines

- All enhancements must align with the mission statement above.
- When adding features, update this document to reflect new capabilities and their code locations.
- Cite relevant files/functions in all documentation and pull requests.

---

## License

© Daniel P Raven and Matt Russell 2024 All Rights Reserved
