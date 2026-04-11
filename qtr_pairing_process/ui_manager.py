"""
UI Manager - Import wrapper for V2 architecture

Automatically imports optimized V2 implementation with:
- GridDataModel (144 StringVars ΓåÆ 1 data model)
- CommentOverlay (75 bindings ΓåÆ 2 bindings)
- Batch update optimization
- Performance improvements

To use V1 (rollback), import from ui_manager_v1_backup instead.

┬⌐ Daniel P Raven and Matt Russell 2024 All Rights Reserved
"""

# Import V2 by default
from qtr_pairing_process.ui_manager_v2 import UiManager

# Export UiManager for external imports
__all__ = ['UiManager']
