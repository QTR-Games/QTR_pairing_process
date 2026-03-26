#!/usr/bin/env python3
"""Manual smoke script for historical fixes (not for automated pytest runs)."""

import pytest


pytestmark = pytest.mark.skip(reason="Manual smoke script")


def test_fixes_manual_placeholder():
    assert True
