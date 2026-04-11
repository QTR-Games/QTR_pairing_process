#!/usr/bin/env python3
"""Manual dynamic-UI sizing script (not for automated pytest runs)."""

import pytest


pytestmark = pytest.mark.skip(reason="Manual blocking UI script")


def test_simple_dynamic_manual_placeholder():
    assert True
