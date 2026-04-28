# Advanced Strategic Sorting - User Guide

## Overview

The QTR Pairing Process now includes advanced sorting algorithms that go beyond simple score optimization. These features help you make better strategic decisions by considering factors like reliability, opponent adaptation, and risk management.

## The Three Sorting Methods

### 1. Cumulative Sorting (Default)

- **Purpose**: Maximizes theoretical score potential
- **Best For**: When you want the highest possible outcomes
- **How It Works**: Sums all ratings in each decision path and ranks by total value
- **Use When**: You're confident in your ratings accuracy and want maximum upside

### 2. Risk-Adjusted Confidence Sorting

- **Purpose**: Prioritizes reliable, consistent strategies
- **Best For**: Tournament situations where consistency matters more than maximum potential
- **How It Works**:
  - Assigns confidence scores to each rating (5=95%, 4=80%, 3=60%, 2=35%, 1=15%)
  - Penalizes high-variance paths (inconsistent ratings)
  - Promotes paths with steady, dependable outcomes
- **Use When**:
  - High-pressure matches where you need predictable results
  - Conservative strategy approach
  - When avoiding losses is more important than maximizing wins

### 3. Counter-Resistance Sorting

- **Purpose**: Identifies strategies that work even when opponents adapt
- **Best For**: Competitive play against skilled, adaptive opponents
- **How It Works**:
  - Models how opponents will likely counter your strategies
  - Midpoint ratings (3 on a 1–5 scale) score highest — they are hardest to counter
  - Extreme ratings are easier for opponents to exploit
- **Use When**:
  - Facing experienced opponents who adapt mid-game
  - You expect opponent to make optimal counter-moves
  - High-level competitive environments

## How to Use

1. Select teams and scenario, fill in the rating grid, click **Generate Combinations**.
2. Click **Sort by Confidence** or **Sort by Counter-Resistance** to apply.
3. Top branches show the best strategies for your chosen method.
4. Click **Remove Sorting** to return to original order.

## Choosing the Right Mode

| Situation | Recommended Mode |
|---|---|
| Elimination round, need consistency | Confidence |
| Opponent adapts mid-game | Counter-Resistance |
| Need maximum theoretical score | Cumulative |
| General balanced analysis | Strategic Fusion |

## Understanding Confidence Scores

| Rating | Confidence |
|---|---|
| 5 | 95% |
| 4 | 80% |
| 3 | 60% |
| 2 | 35% |
| 1 | 15% |

## Understanding Counter-Resistance Scores

- **Rating 3 paths often rank high**: opponents waste effort countering even matchups.
- **Rating 5 paths may rank lower**: they draw the opponent's strongest counter-responses.
- **Mixed-rating paths**: often show good resistance due to unpredictability.

## Tournament Day Tips

- **Pre-match**: Use Confidence sorting to identify your 3–5 most reliable strategies.
- **During pairings**: Switch to Counter-Resistance if opponent shows unexpected adaptation.
- **Post-match**: Track which sorting method best predicted outcomes to calibrate your approach.
