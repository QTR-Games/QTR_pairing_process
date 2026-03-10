"""
UI Manager - Import wrapper for V2 architecture

Automatically imports optimized V2 implementation with:
- GridDataModel (144 StringVars -> 1 data model)
- CommentOverlay (75 bindings -> 2 bindings)
- Batch update optimization
- Performance improvements

To use V1 (rollback), import from ui_manager_v1_backup instead.

Copyright (c) 2024 Daniel P Raven and Matt Russell. All rights reserved.
"""

from qtr_pairing_process.ui_manager_v2 import UiManager

__all__ = ["UiManager"]
