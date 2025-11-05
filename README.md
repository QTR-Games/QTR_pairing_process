# QTR Pairing Process

![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red)
![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![Status](https://img.shields.io/badge/Status-Active%20Development-green)

## Overview

The **QTR Pairing Process** is a sophisticated tournament pairing application designed for 5v5 team-based miniature wargaming tournaments. Built by Daniel P. Raven and Matt Russell, this tool helps teams strategically analyze matchups and optimize player pairings based on detailed rating matrices.

### What is QTR?

**QTR** stands for "Quote The Raven" - the brand name for this suite of tournament management tools.

## Key Features

- **Interactive Matchup Grid**: Visual 5x5 grid for rating player-vs-player matchups
- **Scenario-Based Analysis**: Support for 7 different game scenarios (0-6) with unique strategic considerations
- **Decision Tree Generator**: Hierarchical visualization of all possible pairing combinations
- **Multiple Evaluation Modes**: MAX, MIN, SUM, and AVG algorithms for different strategic approaches
- **Database Management**: SQLite-based storage for teams, players, scenarios, and ratings
- **Import/Export System**: Support for CSV and Excel file formats
- **Color-Coded Ratings**: Intuitive visual feedback with customizable color schemes
- **Comments System**: Strategic annotations for individual matchups with 2000-character limit per comment

## Tournament Format

This application is designed for tournaments following the **World Team Championship (WTC)** format:

- **Team Size**: Exactly 5 players per team
- **Format**: Team vs Team elimination
- **Scenarios**: 7 predefined scenarios with different tactical objectives
- **Rating System**: 1-5 scale where:
  - **1**: Extremely unfavorable matchup (near-certain loss)
  - **2**: Unfavorable matchup
  - **3**: Even/neutral matchup
  - **4**: Favorable matchup
  - **5**: Extremely favorable matchup (near-certain win)

## Installation

### Prerequisites

- Python 3.7 or higher
- tkinter (usually included with Python)
- Required Python packages:

  ```bash
  pip install openpyxl sqlite3
  ```

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/QTR-Games/QTR_pairing_process.git
   cd QTR_pairing_process
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:

   ```bash
   python main.py
   ```

## Quick Start

### Basic Usage

1. **Launch Application**: Run `python main.py` to open the main interface
2. **Select Teams**: Use dropdown menus to choose Team 1 and Team 2
3. **Choose Scenario**: Select the tournament scenario (0-6)
4. **Input Ratings**: Fill the 5x5 grid with matchup ratings (1-5)
5. **Generate Tree**: Click "Generate Combinations" to see all possible pairings
6. **Analyze Results**: Review the decision tree to find optimal pairings

### Data Management

- **Import CSV**: Load existing team data and ratings from CSV files
- **Import Excel**: Support for `.xlsx` files with structured team data
- **Export Data**: Save current ratings and analysis to CSV format
- **Database Storage**: Persistent storage of teams, players, and historical data

### Comments System

- **Strategic Annotations**: Add detailed notes for individual player matchups
- **Per-Scenario Comments**: Comments are specific to each scenario (0-6)
- **Hover Tooltips**: View existing comments by hovering over matchup cells
- **Right-Click Editing**: Add, edit, or delete comments via right-click context
- **Character Limit**: 2000 characters maximum per comment
- **Real-Time Validation**: Live character counting with visual feedback

For detailed information about the comments system, see [Comments System Documentation](docs/COMMENTS_SYSTEM.md).

## Application Structure

### Main Components

- **UI Manager** (`ui_manager.py`): Main application interface and user interactions
- **Tree Generator** (`tree_generator.py`): Pairing combination logic and decision trees
- **Database Manager** (`db_manager.py`): SQLite database operations
- **Excel Importer** (`excel_importer.py`): Excel file processing and data import

### Key Modules

```text
qtr_pairing_process/
├── constants.py          # Application constants and configuration
├── ui_manager.py         # Main UI and application logic
├── tree_generator.py     # Pairing algorithm and decision trees
├── lazy_tree_view.py     # Custom TreeView widget with scrolling
├── tooltip.py            # UI tooltip functionality
├── utility_funcs.py      # Helper functions
├── db_management/        # Database layer
│   ├── db_manager.py     # SQLite operations
│   └── sql/              # SQL schema definitions
└── excel_management/     # Excel import functionality
    └── excel_importer.py # Excel file processing
```

## Evaluation Modes

The application supports multiple algorithms for evaluating pairing decisions:

### 1. MAX Mode (Default)

- **Strategy**: Maximize best-case scenarios
- **Logic**: Prioritizes the highest single rating in each pairing branch
- **Best For**: Aggressive, opportunity-seeking strategies

### 2. MIN Mode

- **Strategy**: Risk-averse approach
- **Logic**: Avoids poor matchups by prioritizing minimum ratings
- **Best For**: Conservative strategies, avoiding disasters

### 3. SUM Mode

- **Strategy**: Maximize total advantage
- **Logic**: Sums all ratings across the entire pairing tree
- **Best For**: Balanced team strategies

### 4. AVG Mode

- **Strategy**: Consistent performance
- **Logic**: Averages ratings for steady, predictable outcomes
- **Best For**: Well-rounded team compositions

## File Formats

### CSV Import Format

```csv
Team Name,Player1,Player2,Player3,Player4,Player5
Enemy Team,Enemy1,Enemy2,Enemy3,Enemy4,Enemy5
0,Enemy1,Enemy2,Enemy3,Enemy4,Enemy5
Player1,3,2,4,3,5
Player2,2,3,3,4,2
...
```

### Excel Import Format

- **Teams Sheet**: Team names and player rosters
- **Scenario Sheets**: Individual sheets for each scenario (0-6)
- **Rating Matrix**: 5x5 grid of matchup ratings per scenario

## Configuration

### Color Scheme (constants.py)

```python
DEFAULT_COLOR_MAP = {
    '1': 'orangered',  # Very unfavorable
    '2': 'orange',     # Unfavorable
    '3': 'yellow',     # Neutral
    '4': 'greenyellow',# Favorable
    '5': 'lime'        # Very favorable
}
```

### Scenarios

- **0**: Scenario Agnostic (general matchups)
- **1**: Recon
- **2**: Battle Lines
- **3**: Wolves At Our Heels
- **4**: Payload
- **5**: Two Fronts
- **6**: Invasion

## Contributing

This project is actively developed by Daniel P. Raven and Matt Russell. For contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

© Daniel P Raven and Matt Russell 2024 All Rights Reserved

## Support

For questions, issues, or feature requests, please contact the development team or create an issue in the repository.

## Version History

- **v0.1**: Initial release with core pairing functionality
- **Current**: Active development with database integration and Excel support

## Future Roadmap

- Battlefield advantage modifiers
- Web-based interface option

---

*This application is designed for competitive miniature wargaming tournaments following the World Team Championship format.*