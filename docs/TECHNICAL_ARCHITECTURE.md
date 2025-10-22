# Technical Architecture Documentation

## Overview

The QTR Pairing Process is a desktop application built with Python and tkinter, designed for strategic tournament pairing analysis in 5v5 miniature wargaming tournaments.

## System Architecture

### Core Components

```
QTR Pairing Process
├── Presentation Layer (UI)
│   ├── ui_manager.py - Main application interface
│   ├── lazy_tree_view.py - Custom TreeView with scrolling
│   ├── tooltip.py - UI tooltip functionality
│   └── delete_team_dialog.py - Team management dialogs
├── Business Logic Layer
│   ├── tree_generator.py - Pairing algorithm and decision trees
│   ├── utility_funcs.py - Helper functions
│   └── ui_db_funcs.py - UI-Database bridge functions
├── Data Access Layer
│   ├── db_manager.py - SQLite database operations
│   └── excel_importer.py - File import processing
└── Data Storage
    ├── SQLite Database (portable .db files)
    └── Import/Export (CSV, Excel formats)
```

### Technology Stack

- **Language**: Python 3.7+
- **GUI Framework**: tkinter (cross-platform desktop UI)
- **Database**: SQLite3 (embedded, portable)
- **File Processing**: 
  - CSV: Python built-in `csv` module
  - Excel: `openpyxl` library
- **Data Structures**: Native Python collections

## Database Schema

### Tables Overview

#### Teams Table
```sql
CREATE TABLE teams (
    team_id INTEGER PRIMARY KEY ASC,
    team_name TEXT
);
```

#### Players Table  
```sql
CREATE TABLE players (
    player_id INTEGER PRIMARY KEY ASC,
    team_id INTEGER,
    player_name TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
```

#### Scenarios Table
```sql
CREATE TABLE scenarios(
    scenario_id INTEGER,
    scenario_name TEXT
);
```

#### Ratings Table
```sql
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_1_player_id INTEGER NOT NULL,
    team_1_id INTEGER NOT NULL,
    team_2_player_id INTEGER NOT NULL,
    team_2_id INTEGER NOT NULL,
    scenario_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    UNIQUE (team_1_player_id, team_2_player_id, scenario_id),
    FOREIGN KEY (team_1_player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_2_player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_1_id) REFERENCES teams(team_id),
    FOREIGN KEY (team_2_id) REFERENCES teams(team_id),
    FOREIGN KEY (scenario_id) REFERENCES scenarios(scenario_id)
);
```

### Data Relationships

```
Teams (1) ──── (Many) Players
   │                    │
   │                    │
   └─── Ratings ────────┘
         │
         └─── Scenarios
```

### Key Constraints

- **Unique Ratings**: Each player-vs-player matchup per scenario can only have one rating
- **Team Size**: Application enforces exactly 5 players per team
- **Rating Range**: Values constrained to 1-5 (future: expandable to 1-10)
- **Scenario Structure**: Always includes Scenario 0 (Agnostic) + 6 named scenarios

## Application Flow

### Startup Sequence

1. **Database Selection**: User chooses existing database or creates new one
2. **UI Initialization**: Main window with tabbed interface loads
3. **Data Loading**: Available teams and scenarios populate dropdowns
4. **Grid Setup**: 5x5 rating grid initializes with color coding

### Core Workflows

#### 1. Team Setup Workflow
```
Load Teams → Select Team 1 & 2 → Choose Scenario → Load Existing Ratings
```

#### 2. Rating Input Workflow
```
Select Grid Cell → Enter Rating (1-5) → Color Updates → Auto-save to Database
```

#### 3. Analysis Workflow
```
Generate Tree → Apply Sorting Algorithm → Review Decision Paths → Export Results
```

#### 4. Data Import Workflow
```
Select File → Validate Format → Parse Teams/Players → Import Ratings → Update Database
```

## Pairing Algorithm

### Decision Tree Generation

The core algorithm generates all possible pairing combinations following WTC tournament rules:

#### Tree Structure
```
Root
├── Team A Player 1 vs [Team B Options]
│   ├── Remaining Player A vs Remaining Team B
│   │   └── ... (recursive until all paired)
│   └── Alternative pairing paths
└── Team A Player 2 vs [Team B Options]
    └── ... (all combinations)
```

#### Strategic Considerations

1. **Pinning Strategy**: Holding high-rated players to force opponent into poor choices
2. **Floor Analysis**: Identifying safest conservative choices
3. **Optimization**: Finding paths leading to highest cumulative ratings

### Evaluation Modes

#### MAX Mode (Primary)
- **Logic**: `max(rating_0, rating_1)` for each decision node
- **Strategy**: Aggressive, opportunity-seeking
- **Use Case**: When you have strong players who can exploit good matchups

#### MIN Mode (Risk-Averse)
- **Logic**: `min(match_ratings)` across all child nodes
- **Strategy**: Conservative, avoid disasters
- **Use Case**: When avoiding bad matchups is more important than maximizing good ones

#### SUM Mode (Comprehensive)
- **Logic**: Sum all ratings in pairing branch
- **Strategy**: Balanced team approach
- **Use Case**: When overall team strength matters most

#### AVG Mode (Consistent)
- **Logic**: Average ratings for steady outcomes
- **Strategy**: Predictable performance
- **Use Case**: Well-rounded team compositions

## File Format Specifications

### CSV Import Format

#### Header Structure
```csv
Team Name,Player1,Player2,Player3,Player4,Player5
Opponent Team,Opponent1,Opponent2,Opponent3,Opponent4,Opponent5
```

#### Rating Sections (Per Scenario)
```csv
0,Opponent1,Opponent2,Opponent3,Opponent4,Opponent5
Player1,3,2,4,3,5
Player2,2,3,3,4,2
Player3,4,4,3,2,3
Player4,3,3,4,4,4
Player5,2,2,3,3,4
1,Opponent1,Opponent2,Opponent3,Opponent4,Opponent5
[... ratings for scenario 1 ...]
```

### Excel Import Format

#### Required Sheets
- **Teams**: Team names and player rosters
- **Scenario_0** through **Scenario_6**: Rating matrices

#### Sheet Structure
```
     A        B        C        D        E        F
1  Team1    Team2
2  Player1  Opponent1
3  Player2  Opponent2  
4  Player3  Opponent3
5  Player4  Opponent4
6  Player5  Opponent5
```

## Configuration Management

### Scenario Configuration
Scenarios are stored in database and configurable without code changes:

```python
SCENARIO_MAP = {
    0: "0 - Scenario Agnostic",
    1: "1 - Recon",
    2: "2 - Battle Lines",
    3: "3 - Wolves At Our Heels", 
    4: "4 - Payload",
    5: "5 - Two Fronts",
    6: "6 - Invasion"
}
```

### Color Coding System
```python
DEFAULT_COLOR_MAP = {
    '1': 'orangered',    # Extremely unfavorable
    '2': 'orange',       # Unfavorable
    '3': 'yellow',       # Even/Neutral
    '4': 'greenyellow',  # Favorable  
    '5': 'lime'          # Extremely favorable
}
```

## Performance Considerations

### Database Optimization
- **Indexing**: Primary keys and foreign key constraints
- **Query Patterns**: Optimized for team-vs-team scenario queries
- **File Size**: Designed to remain email-friendly (< 25MB typical)

### Memory Management
- **Lazy Loading**: TreeView loads nodes on-demand
- **Data Caching**: Recently accessed ratings cached in memory
- **Garbage Collection**: Explicit cleanup of large tree structures

### UI Responsiveness
- **Progressive Rendering**: Large trees render incrementally
- **Background Processing**: Tree generation doesn't block UI
- **Scrolling Optimization**: Virtual scrolling for large datasets

## Security & Data Integrity

### Data Validation
- **Rating Bounds**: Enforced 1-5 range (configurable for future expansion)
- **Team Size**: Strict 5-player validation
- **SQL Injection**: Parameterized queries throughout
- **File Validation**: Schema validation for imports

### Database Integrity
- **Foreign Key Constraints**: Maintain referential integrity
- **Unique Constraints**: Prevent duplicate ratings
- **Transaction Safety**: Database operations are atomic

### Backup & Recovery
- **Portable Files**: SQLite databases are self-contained
- **Export Options**: CSV/Excel exports serve as backups
- **Version Control**: Database schema versioning for future updates

## Error Handling

### Common Error Scenarios
1. **Database Connection Issues**: Graceful fallback to file-based storage
2. **Import Format Errors**: Detailed validation messages
3. **Missing Data**: Default values and user notifications
4. **Tree Generation Failures**: Partial results with error reporting

### Logging Strategy
- **User Actions**: Key operations logged for debugging
- **Error Details**: Stack traces preserved for development
- **Performance Metrics**: Tree generation timing tracked

## Future Architecture Considerations

### Planned Enhancements
1. **Comments System**: Database schema ready for matchup annotations
2. **Rating Scale Expansion**: Database supports 1-10 scale migration  
3. **Battlefield Advantages**: Framework for modifiable ratings
4. **Web Interface**: API layer preparation for future web version

### Scalability Preparations
- **Modular Design**: Clean separation of concerns
- **Plugin Architecture**: Extensible evaluation algorithms
- **Configuration Management**: External configuration files
- **API Readiness**: Business logic separated from UI concerns