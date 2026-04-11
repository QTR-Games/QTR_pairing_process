# QTR Pairing Process 2.0.0 User Guide

## 1. Overview

QTR Pairing Process helps a 5-player team plan pairings against another 5-player team using scenario-based matchup ratings and decision-tree analysis.

## 2. System Requirements

- Windows 10 or Windows 11 (64-bit)
- No separate Python install required for `.exe` usage
- Recommended display: 1920x1080 or higher

## 3. Getting Started

1. Launch `QTR_Pairing_Process_v2.0.0.exe`.
2. Select Team 1 and Team 2 from dropdowns.
3. Select scenario (0-6).
4. Enter ratings in the 5x5 matchup grid (1-5 scale).
5. Click Generate Combinations.

## 4. Rating Scale

- 1: Very unfavorable matchup
- 2: Unfavorable matchup
- 3: Even matchup
- 4: Favorable matchup
- 5: Very favorable matchup

## 5. Core Workflow

1. Choose teams and scenario.
2. Enter or load matchup ratings.
3. Generate the pairing tree.
4. Use sort strategies to inspect outcomes.
5. Record decisions and notes in comments.

## 6. Tree Sort Modes

- Cumulative Sort: Favors strongest total-path value.
- Highest Confidence: Favors more reliable paths.
- Counter Pick: Favors resistance to opponent counters.
- Strategic Fusion: Blends strategic factors into a unified score.

You can also click tree column headers (`Pairing`, `Rating`, `Sort Value`) to apply column-based ordering.

## 7. Loading and Busy Indicators

During heavy operations (generation/sorting):

- Status bar shows loading text.
- Progress activity indicator is displayed.
- Heavy action controls are temporarily disabled.

This behavior prevents accidental repeated actions and improves UI feedback during processing.

## 8. Data Import and Export

- CSV import: load team and matchup data from existing exports/templates.
- Excel import: load structured team/rating data from `.xlsx` files.
- Save/export as needed for collaboration and backup.

## 9. Comments and Notes

- Right-click a matchup cell to add/edit comments.
- Comments are scenario-specific.
- Comment markers do not alter the rating color coding.

## 10. Troubleshooting

### App does not open

- Re-run the executable.
- Check that antivirus or SmartScreen is not blocking first launch.
- Confirm file extraction permissions in your user profile.

### Slow first startup

- One-file executables extract resources on first run; this is expected.

### Ratings look wrong or stale

- Confirm scenario selection.
- Re-generate combinations after major input changes.
- Verify you are viewing the intended sort mode.

## 11. Best Practices for Tournament Use

- Validate teams and scenario before entering ratings.
- Keep ratings consistent across coaches and analysts.
- Compare at least two sort modes before final decisions.
- Save snapshots before major strategy changes.

## 12. Release Support Files

- `RELEASE_NOTES_v2.0.0.md`
- `SHA256SUMS.txt`

To validate the executable checksum in PowerShell:

```powershell
Get-FileHash .\QTR_Pairing_Process_v2.0.0.exe -Algorithm SHA256
```

Compare the hash output to `SHA256SUMS.txt`.
