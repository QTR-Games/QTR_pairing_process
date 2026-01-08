# Tree Sorting Strategies Guide

## Overview

The QTR Pairing Process provides three sophisticated sorting algorithms to help analyze matchup decision trees from different strategic perspectives. Each sorting method reorganizes the tree to highlight different aspects of the matchup combinations.

**Location**: `qtr_pairing_process/tree_generator.py`  
**UI Buttons**: Matchup Tree tab, left sidebar

---

## 1. Cumulative Sort

### Purpose
Highlights paths with the **highest total matchup strength** for your team. This is an aggressive strategy that maximizes the sum of all matchup ratings along a decision path.

### How It Works
**Implementation**: Lines 56-155 in `tree_generator.py`

1. **Path Calculation**: For each complete path from root to leaf, calculates the sum of all ratings
   - Example: [Rating 5] → [Rating 4] → [Rating 3] = Cumulative Value 12

2. **Recursive Scoring**: Each branch node stores the maximum cumulative value achievable through its children

3. **Sorting**: At each level, options are sorted with highest cumulative values at the top

### Algorithm Details
```python
# Stores cumulative sum in node tags: 'cumulative_12'
# Sorts children: reverse=True (highest first)
# Recursively processes entire tree
```

### When to Use
- **Maximize total points**: When overall matchup strength matters most
- **Aggressive play**: Seeking the highest possible combined ratings
- **Clear advantage scenarios**: When you want to press your strongest matchups

### Display
- Column Header: "Cumulative Value"
- Shows: Total sum of ratings along that path

---

## 2. Highest Confidence (Risk-Adjusted)

### Purpose
Identifies paths with the **most reliable high-scoring outcomes**. This is a balanced strategy that considers both rating quality and path consistency, penalizing volatile paths even if they have high peaks.

### How It Works
**Implementation**: Lines 157-314 in `tree_generator.py`

1. **Confidence Mapping**: Converts ratings to confidence percentages
   - Rating 5 = 95% confidence (very strong advantage)
   - Rating 4 = 80% confidence (strong advantage)
   - Rating 3 = 60% confidence (even matchup)
   - Rating 2 = 35% confidence (disadvantage)
   - Rating 1 = 15% confidence (severe disadvantage)

2. **Path Analysis**: Tracks both floor (worst outcome) and ceiling (best outcome) for each path

3. **Variance Penalty**: Applies penalty for inconsistent paths
   - Path [5, 5, 5, 1] has high variance → penalty applied
   - Path [4, 4, 4, 4] has low variance → minimal penalty

4. **Combined Scoring**: `(average_confidence - variance_penalty)`

### Algorithm Details
```python
# Confidence formula:
final_confidence = avg_confidence - variance_penalty

# Variance penalty (0-20 scale):
penalty = min(20, (variance / max_variance) * 20)
```

### When to Use
- **Balanced strategy**: Want strong matchups without wild swings
- **Avoid risk**: Prefer consistent 4's over mix of 5's and 1's
- **Tournament play**: When reliability matters as much as strength
- **Unknown opponents**: When you want consistent performance

### Display
- Column Header: "Confidence Score"
- Shows: Risk-adjusted confidence percentage

---

## 3. Counter Pick (Counter-Resistance)

### Purpose
Identifies paths that are **most resistant to opponent counter-strategies**. This is a defensive-minded approach that assumes the opponent will actively try to counter your choices.

### How It Works
**Implementation**: Lines 316-470 in `tree_generator.py`

1. **Counter-Resistance Scoring**: Assigns resistance values based on how vulnerable each rating is to opponent focus
   - Rating 5 = 60 resistance (high value but vulnerable to focus-fire)
   - Rating 4 = 75 resistance (good value with moderate vulnerability)
   - Rating 3 = 85 resistance (most resistant - opponent indifferent)
   - Rating 2 = 70 resistance (low value, opponent may ignore)
   - Rating 1 = 50 resistance (very low, opponent will exploit)

2. **Opponent Counter Simulation**: Models how effectively opponent can counter each rating
   - High ratings (4-5): 30% effectiveness reduction (opponent counters hard)
   - Medium ratings (3): 10% effectiveness reduction (hardest to counter)
   - Low ratings (1-2): 20% effectiveness reduction (opponent may not need to counter)

3. **Path Resistance**: Combines current resistance with child path resistance, adjusted by opponent counter effectiveness

### Algorithm Details
```python
# Resistance calculation:
adjusted_resistance = (node_resistance + child_resistance) / 2
adjusted_resistance *= (1 - opponent_counter_effectiveness)

# Sorts by highest resistance (most counter-proof)
```

### When to Use
- **Experienced opponents**: Against players who actively counter-pick
- **Meta-game awareness**: When opponent knows your team well
- **Defensive play**: Minimize opponent's ability to exploit your choices
- **Conservative approach**: Prefer safe 3's that resist countering over risky 5's

### Display
- Column Header: "Resistance Score"
- Shows: Counter-resistance rating (higher = harder to counter)

---

## Strategy Comparison

| Sort Method | Focus | Best For | Risk Level |
|-------------|-------|----------|------------|
| **Cumulative** | Maximum total strength | Aggressive play, pressing advantages | High |
| **Highest Confidence** | Reliable consistency | Balanced play, avoiding volatility | Medium |
| **Counter Pick** | Opponent counter-resistance | Defensive play, experienced opponents | Low |

---

## Usage Tips

### Toggle Behavior
- Click once: Activate sorting
- Click again: Deactivate (return to default order)
- Only one sort can be active at a time

### Button States
- 🔴 Red filled circle + pressed appearance = Active
- ⭕ Empty circle + raised appearance = Inactive

### Interpreting Results

**Cumulative Sort**:
- Higher number = stronger overall path
- Compare top options' total values
- Look for paths that consistently score high

**Confidence Sort**:
- Higher percentage = more reliable path
- Paths with ~90%+ are very consistent
- Paths below ~50% have significant risk

**Counter Pick Sort**:
- Higher score = more counter-resistant
- Scores around 80-85 are very safe
- Scores below 60 are vulnerable to countering

---

## Technical Implementation Notes

### Data Storage
All scores are stored in node tags for efficient access:
```python
# Example node tags:
['cumulative_12', 'confidence_85', 'floor_10', 'ceiling_14', 'resistance_78']
```

### Recursive Sorting
All algorithms sort the entire tree recursively, ensuring:
- Each level is independently sorted
- Child nodes maintain their relative order
- Navigation through the tree always shows best options first

### Performance
- Calculations done once when sort activated
- Results cached in node tags
- Re-sorting uses cached values (fast)
- New tree generation clears cached values

---

## Example Scenario

Given three paths:
- **Path A**: [5, 5, 1] - Total: 11, Avg: 3.67, Variance: High
- **Path B**: [4, 4, 3] - Total: 11, Avg: 3.67, Variance: Low
- **Path C**: [3, 3, 3] - Total: 9, Avg: 3.00, Variance: None

**Sort Results**:

| Sort Type | Order | Reasoning |
|-----------|-------|----------|
| Cumulative | A=B (11) → C (9) | Pure total |
| Confidence | B (consistent high) → A (volatile) → C (safe but lower) | Penalizes variance |
| Counter Pick | C (resistance 85) → B (resistance 75) → A (resistance 60) | 3's resist counters best |

---

## Last Updated
January 8, 2026
