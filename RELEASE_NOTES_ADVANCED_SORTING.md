# QTR Pairing Process - Advanced Sorting Features Release Notes

## Version 2.1.0 - Advanced Decision Intelligence

### 🎯 **New Features: Strategic Sorting Algorithms**

This release introduces two revolutionary sorting methods designed to enhance tournament decision-making beyond simple optimization.

---

## 🛡️ **Risk-Adjusted Confidence Sorting**

### What It Does

Sorts decision paths by **reliability and consistency** rather than pure maximum potential, helping you identify strategies that are most likely to succeed under tournament pressure.

### How It Works

- **Confidence Scoring**: Each rating gets a confidence score based on its reliability:
  - Ratings are normalized from the active scale to `n in [0, 1]`
  - `confidence = round(15 + 80 * n)`
  - Higher ratings always increase confidence, with full native-scale granularity

- **Variance Penalty**: Paths with high variance (mix of 1s and 5s) are penalized compared to consistent paths (all 3s-4s)
- **Floor-Ceiling Analysis**: Calculates both minimum guaranteed and maximum potential outcomes

### When to Use

- **High-Stakes Matches**: When you need predictable results over maximum theoretical upside
- **Conservative Strategy**: When avoiding losses is more important than maximizing wins
- **Pressure Situations**: When you want strategies most likely to perform as expected

### Strategic Value

- Identifies "safe" strategies vs "gambling" strategies
- Shows not just best potential outcomes, but most **reliable** outcomes
- Critical for tournament play where consistency beats occasional brilliance

---

## ⚔️ **Counter-Resistance Sorting**

### Counter-Strategy Purpose

Sorts decision paths by how well they perform against **optimal opponent counter-strategies**, assuming your opponent will adapt and make their best possible responses.

### Implementation Details

- **Counter-Strategy Modeling**: Simulates likely opponent responses to your moves
- **Resistance Scoring**: Evaluates how each rating withstands opponent focus:
  - Ratings are normalized from the active scale to `n in [0, 1]`
  - `resistance = round(50 + 35 * (1 - 4*(n - 0.5)^2))`
  - Midpoint ratings are most stable; extremes are easier to counter

- **Adaptive Response Simulation**: Models how opponent counter-effectiveness varies based on your strategy
  - `extremity = abs(n - 0.5) * 2`
  - `counter_effectiveness = 0.1 + 0.2 * extremity`

- **Scale Granularity**:
  - `1-3`: coarse differentiation
  - `1-5`: medium differentiation
  - `1-10`: fine differentiation (fewer ties in confidence/resistance-driven ordering)

### Optimal Usage Scenarios

- **High-Level Competition**: Against skilled opponents who will adapt mid-game
- **Defensive Strategy**: When you expect opponent to make optimal counter-moves
- **Meta-Game Awareness**: When opponent behavior patterns are predictable

### Counter-Resistance Benefits

- Moves beyond "assuming opponent plays poorly"
- Identifies strategies that remain strong even when opponent adapts
- Essential for competitive play where opponents learn and counter

---

## 🎮 **How to Use These Features**

### In the Matchup Tree Tab

1. **Generate Combinations** (creates the decision tree)
2. **Choose Your Sorting Strategy**:
   - **"Sort by Confidence"**: For reliable, consistent outcomes
   - **"Sort by Counter-Resistance"**: For opponent-adaptive strategies
   - **Default Cumulative Sorting**: For maximum theoretical value
3. **Toggle Sorting**: Use "Remove Sorting" to return to original order

### Best Practices

- **Start with Confidence Sorting** for most tournament situations
- **Use Counter-Resistance** when facing known adaptive opponents
- **Compare multiple sorting methods** to understand different strategic angles
- **Remember**: The "best" strategy depends on your risk tolerance and opponent skill level

---

## 🔄 **Sorting Method Comparison**

| Sorting Method | Best For | Prioritizes | Risk Level |
|----------------|----------|-------------|------------|
| **Cumulative** | Maximum potential | Highest theoretical scores | High |
| **Confidence** | Reliability | Consistent, predictable outcomes | Low |
| **Counter-Resistance** | Adaptive opponents | Strategies that survive counters | Medium |

---

## 🎯 **Strategic Philosophy**

These features represent a shift from **pure optimization** to **decision intelligence**:

- **Pure Optimization**: "What's the highest possible score?"
- **Decision Intelligence**: "What's the most likely to actually work?"

Tournament success often comes from making **good decisions consistently** rather than perfect decisions occasionally. These tools help you identify strategies that work in the real world of competitive play.

---

## 📈 **Technical Implementation Notes**

- **Performance**: Sorting calculations complete in under 100ms for typical 5v5 matchups
- **Data Storage**: Uses tree item tags for efficient confidence/resistance data storage
- **Compatibility**: Fully backward compatible with existing tree functionality
- **State Management**: Preserves original tree order for easy toggling between methods

---

## 🎖️ **Tournament Usage Recommendations**

### Pre-Tournament Planning

1. Use **Confidence Sorting** to identify your most reliable strategies
2. Use **Counter-Resistance** to prepare for expected opponent archetypes
3. Document your top 3-5 decision paths from each method

### Day-of-Tournament

1. Start with **Confidence Sorting** for consistent performance
2. Switch to **Counter-Resistance** if opponent shows adaptive behavior
3. Use **Remove Sorting** to quickly reference original generation order

### Post-Game Analysis

- Compare which sorting method best predicted actual outcomes
- Refine your understanding of when each method is most valuable
- Build institutional knowledge for future tournaments

---

## 🛣️ **Roadmap**

• Optimize the application by reducing calls to the database.

• LINK the matchup tree navigation with what is selected in the first page.
NEEDS TESTING

• Implement the bottom right panel on the Grid page.

*These features transform the QTR Pairing Process from a calculation tool into a strategic intelligence system, giving you the analytical edge needed for competitive tournament play.*
