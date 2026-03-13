"""Legacy test notes for round selection and tree sync.

This file intentionally contains only a summary. The full test suite was removed
from the active test set when the round-selection feature was pulled out of the
application. Refer to git history prior to the removal commit to recover the
original test implementation.

Coverage summary from the removed tests:
- Parsing round selections into MatchupSelection objects
- Matching tree paths for round selections
- Round to tree synchronization behavior
- Tree to round synchronization behavior
- Pattern matching for node text (including OR clauses)
- Conflict and incomplete data handling
- Performance checks for repeated sync operations
- Cache behavior and size limits
- Tab visibility optimization (skip sync when tree not visible)
- Cleanup and cache invalidation behavior
"""
