# Developer Guide

<!-- markdownlint-disable MD051 -->

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Code Architecture](#code-architecture)
3. [Development Workflow](#development-workflow)
4. [Testing Strategy](#testing-strategy)
5. [Contributing Guidelines](#contributing-guidelines)
6. [Code Style and Standards](#code-style-and-standards)

## Development Environment Setup

### Prerequisites

**Required Software:**

- Python 3.7+ (recommended: Python 3.9+)
- Git for version control
- IDE/Editor (recommended: VS Code, PyCharm)

**Python Dependencies:**

```bash
# Core dependencies
pip install openpyxl    # Excel file processing
pip install tkinter     # GUI framework (usually included with Python)

# Development dependencies
pip install pytest      # Testing framework
pip install black       # Code formatting
pip install flake8      # Linting
pip install mypy        # Type checking
```

### Project Setup

1. **Clone Repository**

   ```bash
   git clone https://github.com/QTR-Games/QTR_pairing_process.git
   cd QTR_pairing_process
   ```

2. **Create Virtual Environment**

   ```bash
   python -m venv qtr_env

   # Windows
   qtr_env\Scripts\activate

   # macOS/Linux
   source qtr_env/bin/activate

```text

3. **Install Dependencies**
   ```bash

   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development tools

```text

4. **Verify Installation**
   ```bash

   python main.py  # Should launch the application

```text

### IDE Configuration

**VS Code Settings (.vscode/settings.json):**
```json

{
    "python.defaultInterpreterPath": "./qtr_env/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.testing.pytestEnabled": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}

```text

## Code Architecture

### Project Structure

```text
QTR_pairing_process/
├── main.py                 # Application entry point
├── entrypoint.py          # Alternative entry point
├── config.txt             # Configuration file
├── setup.py               # Package setup
├── requirements.txt       # Dependencies
├── README.md              # Project documentation
├── docs/                  # Documentation
├── qtr_pairing_process/   # Main package
│   ├── __init__.py
│   ├── constants.py       # Application constants
│   ├── ui_manager.py      # Main UI controller
│   ├── tree_generator.py  # Pairing algorithm
│   ├── lazy_tree_view.py  # Custom TreeView widget
│   ├── tooltip.py         # UI tooltips
│   ├── utility_funcs.py   # Helper functions
│   ├── ui_db_funcs.py     # UI-Database bridge
│   ├── file_explorer.py   # File operations
│   ├── db_load_ui.py      # Database selection UI
│   ├── xlsx_load_ui.py    # Excel import UI
│   ├── delete_team_dialog.py # Team management UI
│   ├── db_management/     # Database layer
│   │   ├── __init__.py
│   │   ├── db_manager.py  # Database operations
│   │   └── sql/           # SQL schemas
│   │       ├── players.sql
│   │       ├── ratings.sql
│   │       ├── scenarios.sql
│   │       └── teams.sql
│   └── excel_management/  # Excel processing
│       ├── __init__.py
│       ├── constants.py
│       └── excel_importer.py
└── tests/                 # Test suite
    ├── __init__.py
    ├── test_db_manager.py
    ├── test_tree_generator.py
    └── fixtures/          # Test data
```

### Key Design Patterns

#### 1. MVC Architecture

```python

# Model: Database layer (db_manager.py)

# View: UI components (ui_manager.py, lazy_tree_view.py)

# Controller: Business logic (tree_generator.py, ui_db_funcs.py)

```text

#### 2. Repository Pattern
```python

class DbManager:
    """Central data access layer"""
    def query_sql(self, sql: str) -> List[Tuple]
    def execute_sql(self, sql: str, parameters: List = None) -> int
    def upsert_rating(self, player_id_1: int, player_id_2: int, ...)

```text

#### 3. Observer Pattern
```python

# UI components observe data changes

self.team1_var.trace_add('write', self.on_team_box_change)
self.scenario_var.trace_add('write', self.on_scenario_box_change)

```text

### Module Responsibilities

#### Core Modules

**ui_manager.py**
- Main application window and layout
- Event handling and user interactions
- Data binding between UI and database
- Tab management (Grid vs Tree views)

**tree_generator.py**
- Pairing combination algorithms
- Decision tree construction
- Strategic evaluation modes (MAX, MIN, SUM, AVG)
- Tree optimization and sorting

**db_manager.py**
- SQLite database operations
- CRUD operations for all entities
- Transaction management
- Data integrity enforcement

**lazy_tree_view.py**
- Custom TreeView with performance optimizations
- Lazy loading for large datasets
- Custom scrolling behavior
- Event handling for tree interactions

#### Support Modules

**constants.py**
- Application-wide configuration
- Color schemes and UI settings
- Scenario definitions
- Default values

**utility_funcs.py**
- Pure functions for data manipulation
- Helper algorithms
- Common operations

**excel_importer.py**
- Excel file parsing and validation
- Data transformation and mapping
- Error handling for import operations

### Data Flow

#### 1. Application Startup
```text
main.py → UiManager.__init__() → select_database() → initialize_ui_vars() → create_ui()
```

#### 2. Data Import Flow

```text
User Action → File Selection → ExcelImporter.read_excel_file() →
Data Validation → DbManager.upsert_*() → UI Refresh
```

#### 3. Rating Input Flow

```text
Grid Cell Edit → Validation → DbManager.upsert_rating() →
Color Update → Auto-save Confirmation
```

#### 4. Tree Generation Flow

```text
Generate Button → extract_ratings() → TreeGenerator.generate_combinations() →
Tree Construction → UI Display → User Analysis
```

## Development Workflow

### Branch Strategy

**Main Branches:**

- `main`: Production-ready code
- `develop`: Integration branch for features
- `Support_Comments_On_Matchups`: Current feature branch

**Feature Branches:**

- `feature/rating-scale-expansion`: Expand 1-5 to 1-10 rating system
- `feature/battlefield-advantages`: Implement table selection modifiers
- `feature/improved-sorting`: Enhanced tree sorting algorithms
- `feature/ui-alignment-fix`: Fix grid alignment issues

### Development Process

#### 1. Feature Development

```bash

# Create feature branch

git checkout -b feature/your-feature-name

# Make changes

# ... development work ...

# Test changes

python -m pytest tests/

# Commit with descriptive message

git add .
git commit -m "feat: add matchup comments functionality"

# Push branch

git push origin feature/your-feature-name

# Create pull request

```text

#### 2. Code Review Checklist
- [ ] Code follows style guidelines (Black formatting)
- [ ] All tests pass
- [ ] New features include tests
- [ ] Database changes include migration strategy
- [ ] UI changes preserve existing functionality
- [ ] Documentation updated for user-facing changes

#### 3. Testing Strategy

**Unit Tests:**
```python

# tests/test_tree_generator.py

def test_generate_combinations():
    """Test basic tree generation functionality."""
    # Setup test data
    fNames = ['Player1', 'Player2']
    oNames = ['Enemy1', 'Enemy2']
    ratings = {...}

    # Execute
    generator = TreeGenerator(mock_treeview, sort_alpha=True)
    generator.generate_combinations(fNames, oNames, ratings, ratings)

    # Assert expected behavior
    assert mock_treeview.tree.insert.called

```text

**Integration Tests:**
```python

# tests/test_db_integration.py

def test_rating_crud_operations():
    """Test complete rating lifecycle."""
    # Create test database
    # Insert teams, players, scenarios
    # Test rating operations
    # Verify data integrity

```text

**Manual Testing:**
- UI responsiveness across different screen sizes
- Database file sharing between computers
- Import/export with various file formats
- Tree generation performance with large datasets

### Debugging Guidelines

#### Common Development Issues

**Database Connection Problems:**
```python

# Add debugging to db_manager.py

def connect_db(self, path, name):
    try:
        conn = sqlite3.connect(f'{path}/{name}')
        print(f"Connected to database: {path}/{name}")
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise

```text

**UI Thread Issues:**
```python

# Ensure database operations don't block UI

def long_running_operation(self):
    """Run heavy operations in background."""
    import threading

    def worker():
        # Database intensive work
        result = self.generate_large_tree()
        # Update UI from main thread
        self.root.after(0, lambda: self.update_tree_display(result))

    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()

```text

**Tree Generation Performance:**
```python

# Add timing and profiling

import time
import cProfile

def generate_combinations(self, ...):
    start_time = time.time()

    # Algorithm implementation

    elapsed = time.time() - start_time
    print(f"Tree generation took {elapsed:.2f} seconds")

```text

## Testing Strategy

### Test Organization

```

tests/
├── unit/              # Individual component tests
│   ├── test_db_manager.py
│   ├── test_tree_generator.py
│   └── test_utility_funcs.py
├── integration/       # Component interaction tests
│   ├── test_ui_db_integration.py
│   └── test_import_workflow.py
├── fixtures/          # Test data
│   ├── sample_teams.csv
│   ├── test_ratings.xlsx
│   └── mock_database.db
└── conftest.py        # Pytest configuration

```text

### Test Categories

#### 1. Unit Tests
**Database Operations:**
```python

def test_upsert_rating():
    """Test rating insertion and updates."""
    db = DbManager(':memory:')  # In-memory database for testing

    # Test insertion
    db.upsert_rating(1, 2, 1, 2, 0, 4)
    rating = db.query_sql("SELECT rating FROM ratings WHERE team_1_player_id=1")
    assert rating[0][0] == 4

    # Test update
    db.upsert_rating(1, 2, 1, 2, 0, 5)  # Update same record
    rating = db.query_sql("SELECT rating FROM ratings WHERE team_1_player_id=1")
    assert rating[0][0] == 5

```text

**Algorithm Logic:**
```python

def test_tree_evaluation_modes():
    """Test different tree evaluation algorithms."""
    generator = TreeGenerator(mock_treeview, False)

    # Test MAX mode
    generator.sum_leaf_values(test_node, mode=0)
    assert generator.treeview.tree.set.called_with(test_node, 'Rating', expected_max)

    # Test MIN mode
    generator.sum_leaf_values(test_node, mode=2)
    assert generator.treeview.tree.set.called_with(test_node, 'Rating', expected_min)

```text

#### 2. Integration Tests
**Complete Workflows:**
```python

def test_csv_import_to_tree_generation():
    """Test full workflow from import to analysis."""
    # Import CSV file
    ui_manager = UiManager(test_config)
    ui_manager.import_csv_file('tests/fixtures/sample_teams.csv')

    # Verify teams loaded
    teams = ui_manager.db_manager.query_sql("SELECT team_name FROM teams")
    assert len(teams) == 2

    # Generate tree
    ui_manager.on_generate_combinations()

    # Verify tree created
    assert ui_manager.treeview.tree.get_children()

```text

#### 3. UI Tests
**Mock-Based Testing:**
```python

@patch('tkinter.Tk')
def test_ui_initialization(mock_tk):
    """Test UI components initialize correctly."""
    ui_manager = UiManager(test_config)
    ui_manager.create_ui()

    # Verify UI elements created
    assert ui_manager.combobox_1 is not None
    assert ui_manager.grid_entries is not None
    assert len(ui_manager.grid_entries) == 6

```text

### Running Tests

```bash

# Run all tests

python -m pytest

# Run specific test file

python -m pytest tests/test_db_manager.py

# Run with coverage

python -m pytest --cov=qtr_pairing_process

# Run with verbose output

python -m pytest -v

# Run only unit tests

python -m pytest tests/unit/

```text

## Contributing Guidelines

### Code Contribution Process

#### 1. Issue Creation
Before starting development:
- Check existing issues to avoid duplication
- Create detailed issue describing the problem/feature
- Include use cases and acceptance criteria
- Tag with appropriate labels (bug, feature, enhancement)

#### 2. Development Standards

**Commit Message Format:**
```

type(scope): short description

feat(ui): add comments field to matchup grid
fix(db): resolve foreign key constraint error
docs(readme): update installation instructions
refactor(tree): optimize combination generation algorithm

```text

**Code Documentation:**
```python

def generate_nested_combinations(
    self,
    first_fName: str,
    fNames: List[str],
    oNames: List[str],
    fRatings: Dict[str, Dict[str, int]],
    oRatings: Dict[str, Dict[str, int]],
    parent: str
) -> None:
    """
    Generate all possible pairing combinations recursively.

    Args:
        first_fName: Name of first friendly player to pair
        fNames: Remaining friendly player names
        oNames: Available opponent player names
        fRatings: Friendly team ratings dictionary
        oRatings: Opponent team ratings dictionary
        parent: Parent node ID in tree view

    Returns:
        None (updates tree view directly)

    Raises:
        ValueError: If player names don't match rating dictionary keys
    """

```text

#### 3. Pull Request Guidelines

**PR Description Template:**
```markdown

## Description

Brief description of changes

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated

```text

### Priority Development Areas

Based on user feedback, prioritize contributions in this order:

#### 1. **Improved Sorting Algorithms** (Highest Priority)
Current sorting methods need refinement:
```python

# Opportunity for new evaluation algorithms

def evaluate_tree_advanced(self, node, strategy='balanced'):
    """
    Advanced tree evaluation with multiple strategies.

    Strategies:

    - 'aggressive': Maximize ceiling outcomes
    - 'conservative': Maximize floor outcomes
    - 'balanced': Optimize risk/reward ratio
    - 'adaptive': Dynamic strategy based on current state
    """

```text

#### 2. **Comments/Tooltips System**
Add matchup annotation capabilities:
```python

# Database schema addition needed

"""
CREATE TABLE matchup_comments (
    id INTEGER PRIMARY KEY,
    team_1_player_id INTEGER,
    team_2_player_id INTEGER,
    scenario_id INTEGER,
    comment TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_1_player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_2_player_id) REFERENCES players(player_id)
);
"""

```text

#### 3. **UI Alignment Fixes**
Grid alignment issues need resolution:
- Investigate tkinter grid layout problems
- Ensure consistent spacing across different screen resolutions
- Fix left/right grid synchronization

#### 4. **Battlefield Advantage Modifiers**
Future enhancement for table selection impact:
```python

# Proposed rating adjustment system

class BattlefieldModifier:
    def apply_table_advantage(self, base_rating: int, advantage_type: str) -> float:
        """Apply table selection modifier to base rating."""
        modifiers = {
            'favorable_terrain': 0.5,
            'neutral_terrain': 0.0,
            'unfavorable_terrain': -0.5
        }
        return base_rating + modifiers.get(advantage_type, 0.0)

```text

## Code Style and Standards

### Python Style Guide

**Follow PEP 8 with these specifics:**

```python

# Imports: standard, third-party, local

import os
import sqlite3
from typing import List, Dict, Optional

import tkinter as tk
from tkinter import ttk

from qtr_pairing_process.db_management import db_manager

```text

**Naming Conventions:**
```python

# Classes: PascalCase

class TreeGenerator:

# Functions/Variables: snake_case

def generate_combinations():
    player_ratings = {}

# Constants: UPPER_CASE

DEFAULT_COLOR_MAP = {...}

# Private methods: leading underscore

def _update_scrollbars(self):

```text

**Type Hints:**
```python

from typing import List, Dict, Optional, Union

def upsert_rating(
    self,
    player_id_1: int,
    player_id_2: int,
    team_id_1: int,
    team_id_2: int,
    scenario_id: int,
    rating: int
) -> None:

```text

### Database Standards

**SQL Style:**
```sql

-- Use uppercase for keywords
SELECT
    player_id,
    player_name
FROM players
WHERE team_id = ?
ORDER BY player_id;

-- Descriptive table/column names
CREATE TABLE matchup_comments (
    comment_id INTEGER PRIMARY KEY,
    friendly_player_id INTEGER NOT NULL,
    opponent_player_id INTEGER NOT NULL
);

```text

**Migration Strategy:**
```python

# Version-controlled schema changes

def upgrade_database_v1_to_v2(db_manager: DbManager):
    """Add comments table to existing database."""
    db_manager.execute_sql("""
        CREATE TABLE IF NOT EXISTS matchup_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_1_player_id INTEGER,
            team_2_player_id INTEGER,
            scenario_id INTEGER,
            comment TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

```text

### UI Development Guidelines

**tkinter Best Practices:**
```python

# Use meaningful widget names

self.team_selection_frame = tk.Frame(parent)
self.matchup_grid_frame = tk.Frame(parent)

# Consistent layout management

self.team_selection_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

# Event handling with clear method names

self.team1_var.trace_add('write', self.on_team1_selection_changed)

# Resource cleanup

def cleanup_ui_resources(self):
    """Clean up UI resources before shutdown."""
    if hasattr(self, 'large_tree_data'):
        del self.large_tree_data

```text

**Error Handling:**
```python

def safe_database_operation(self, operation_func, *args, **kwargs):
    """Wrapper for database operations with error handling."""
    try:
        return operation_func(*args, **kwargs)
    except sqlite3.Error as e:
        error_msg = f"Database error: {e}"
        messagebox.showerror("Database Error", error_msg)
        return None
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        messagebox.showerror("Application Error", error_msg)
        return None

```text

### Documentation Standards

**Module Documentation:**
```python

"""
QTR Pairing Process - Tree Generator Module

This module contains the core algorithm for generating pairing decision trees
used in tournament strategy analysis. It supports multiple evaluation modes
and optimization strategies.

Author: Daniel P. Raven, Matt Russell
Created: 2024
License: All Rights Reserved
"""

```text

**Function Documentation:**
```python

def generate_combinations(
    self,
    fNames: List[str],
    oNames: List[str],
    fRatings: Dict[str, Dict[str, int]],
    oRatings: Dict[str, Dict[str, int]]
) -> None:
    """
    Generate complete pairing decision tree for strategic analysis.

    Creates a hierarchical tree showing all possible player pairing sequences
    based on the WTC tournament format. Each branch represents a different
    strategic path through the pairing process.

    Args:
        fNames: List of friendly team player names
        oNames: List of opponent team player names
        fRatings: Nested dict of friendly player ratings vs opponents
                 Format: {friendly_player: {opponent: rating}}
        oRatings: Nested dict of opponent player ratings vs friendlies
                 Format: {opponent: {friendly_player: rating}}

    Returns:
        None: Updates self.treeview directly with generated tree

    Raises:
        ValueError: If player names in fNames/oNames don't match rating keys
        KeyError: If required rating data is missing

    Example:
        >>> generator = TreeGenerator(treeview, sort_alpha=True)
        >>> fNames = ['Alice', 'Bob']
        >>> oNames = ['Charlie', 'Dave']
        >>> ratings = {'Alice': {'Charlie': 4, 'Dave': 3}}
        >>> generator.generate_combinations(fNames, oNames, ratings, ratings)
    """

```text

---

*This developer guide is a living document. Update it as the codebase evolves and new patterns emerge.*
