# Comments System Implementation

## Overview

The QTR Pairing Process application now includes a comprehensive comments system that allows users to add strategic notes and observations for individual player matchups across different scenarios.

## Features Implemented

### 1. Database Layer

- **New Table**: `matchup_comments` with foreign key relationships to players and scenarios
- **Character Limit**: 2000 characters per comment
- **Unique Constraints**: One comment per player-vs-player-per-scenario combination
- **Automatic Indexing**: Optimized for fast retrieval during UI operations
- **Data Integrity**: CASCADE deletion when players or scenarios are removed

### 2. User Interface Integration

#### Tooltip Display (Hover)

- **Trigger**: Hover mouse over any matchup cell in the left grid
- **Behavior**: Displays existing comment in a tooltip popup
- **Visual**: Yellow background with wrapped text (300px max width)
- **Requirements**: Teams, scenario, and player names must be selected/filled

#### Comment Editor (Right-Click)

- **Trigger**: Right-click on any matchup cell in the left grid
- **Dialog Features**:
  - Modal dialog with team/player/scenario context displayed
  - Large text area with scrollbar support
  - Real-time character counter (0/2000)
  - Color-coded character count (black → orange → red)
  - Pre-populated with existing comment content
  - Three action buttons: Save, Delete, Cancel

#### Grid Restrictions

- **Compatible**: Only left grid (matchup ratings) supports comments
- **Incompatible**: Right grid (display grid) does not support comments
- **Header Cells**: Comments only work on actual matchup cells (row > 0, col > 0)

### 3. Database Integration Methods

#### Name-Based Wrapper Methods

```python
# Insert/Update comment
db_manager.upsert_comment_by_name(
    team1_name, team2_name, scenario_name,
    friendly_player_name, opponent_player_name,
    comment_text
)

# Retrieve comment
comment = db_manager.query_comment_by_name(
    team1_name, team2_name, scenario_name,
    friendly_player_name, opponent_player_name
)

# Delete comment
db_manager.delete_comment_by_name(
    team1_name, team2_name, scenario_name,
    friendly_player_name, opponent_player_name
)
```

#### Core Database Methods

- `upsert_comment()`: Insert or update using IDs
- `query_comment()`: Retrieve single comment using IDs
- `query_all_comments()`: Get all comments for team matchup
- `delete_comment()`: Remove comment using IDs
- `get_comment_statistics()`: Usage analytics
- `query_player_id()`: Helper to resolve player names to IDs

## Usage Instructions

### For Users

1. **Adding a Comment**:
   - Select teams and scenario from dropdowns
   - Enter player names in grid headers
   - Right-click on desired matchup cell
   - Type comment in dialog (max 2000 characters)
   - Click "Save" to store

2. **Viewing Comments**:
   - Hover mouse over any matchup cell
   - Tooltip will appear if comment exists
   - Tooltip shows full comment text with word wrapping

3. **Editing Comments**:
   - Right-click on cell with existing comment
   - Dialog opens with current comment pre-loaded
   - Edit text and click "Save" to update

4. **Deleting Comments**:
   - Right-click on cell with comment
   - Click "Delete" button in dialog
   - Confirm deletion in popup dialog

### For Developers

1. **Database Schema**: Comments table automatically created during initialization
2. **Error Handling**: All comment operations include try-catch blocks
3. **Validation**: Character limits enforced at both UI and database levels
4. **Performance**: Indexed queries for efficient comment retrieval
5. **Data Integrity**: Foreign key constraints ensure referential integrity

## Technical Notes

### Character Limit Implementation

- **UI Validation**: Real-time character counting with visual feedback
- **Database Constraint**: TEXT(2000) column type enforces hard limit
- **User Experience**: Clear indication when approaching or exceeding limit

### Comment Scope

- **Per Individual Matchup**: One comment per friendly player vs opponent player
- **Per Scenario**: Comments are scenario-specific (0-6 scenarios)
- **Per Team Pairing**: Comments are tied to specific team combinations

### Performance Considerations

- **Lazy Loading**: Comments only queried when tooltip is triggered
- **Efficient Indexing**: Database indexes on common query patterns
- **Minimal UI Impact**: Comment functionality doesn't affect existing grid performance

## Testing

### Automated Tests

- Database CRUD operations
- Name-to-ID resolution
- Error handling for invalid data
- Character limit validation

### Manual UI Testing

Use `test_ui_comments.py` to launch the application and manually test:

- Comment tooltips on hover
- Right-click comment editing
- Character limit enforcement
- Save/Delete operations

## Future Enhancements

### Potential Improvements

1. **Comment Export**: Include comments in CSV/Excel exports
2. **Comment Search**: Find matchups by comment content
3. **Comment History**: Track comment changes over time
4. **Bulk Operations**: Copy comments between scenarios
5. **Rich Text**: Support for formatting in comments
6. **Comment Templates**: Pre-defined comment snippets
7. **Team Sharing**: Export/import comment sets between users

### Integration Points

- Export functionality (CSV/Excel) could include comment columns
- Tree generation could factor in comment flags
- Import systems could support comment data
- Backup/restore could preserve comment history

## Database Schema Details

```sql
CREATE TABLE matchup_comments (
    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_1_player_id INTEGER NOT NULL,
    team_2_player_id INTEGER NOT NULL,
    scenario_id INTEGER NOT NULL,
    comment TEXT(2000),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (team_1_player_id, team_2_player_id, scenario_id),

    FOREIGN KEY (team_1_player_id) REFERENCES players(player_id) ON DELETE CASCADE,
    FOREIGN KEY (team_2_player_id) REFERENCES players(player_id) ON DELETE CASCADE,
    FOREIGN KEY (scenario_id) REFERENCES scenarios(scenario_id) ON DELETE CASCADE
);
```

This implementation provides a robust, user-friendly commenting system that integrates seamlessly with the existing QTR Pairing Process application while maintaining data integrity and performance standards.
