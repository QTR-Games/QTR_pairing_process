#!/usr/bin/env python3
"""Integration tests for generated tree cache persistence and generation-id propagation."""

import logging
import sqlite3
import tempfile
import tkinter as tk
import json
from tkinter import ttk
from typing import cast

from qtr_pairing_process.db_management.db_manager import DbManager
from qtr_pairing_process.tree_generator import TreeGenerator
from qtr_pairing_process.ui_manager_v2 import UiManager


class DummyTreeView:
    """Minimal tree wrapper fixture so TreeGenerator can run without full UI wiring."""

    def __init__(self, tree):
        self.tree = tree


class LightweightDbManager:
    """Small db manager used for integration tests against a temp sqlite file."""

    def __init__(self, path: str, name: str):
        self.path = path
        self.name = name

    def connect_db(self, path, name):
        return sqlite3.connect(f"{path}/{name}")

    def execute_sql(self, sql, parameters=None):
        with self.connect_db(self.path, self.name) as conn:
            cur = conn.cursor()
            if parameters:
                cur.execute(sql, parameters)
            else:
                cur.execute(sql)
            conn.commit()
            return cur.rowcount


def _build_minimal_ui(path: str, name: str):
    ui = UiManager.__new__(UiManager)
    ui.db_path = path
    ui.db_name = name
    ui.db_manager = cast(DbManager, LightweightDbManager(path, name))
    ui.logger = logging.getLogger("generated_tree_cache_integration")
    ui._tree_cache = {}
    ui._tree_cache_key = None
    ui._tree_generation_id = 0
    return ui


def test_generated_tree_cache_persistence_round_trip():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        ui = _build_minimal_ui(tmpdir, "integration_cache.db")
        ui._ensure_generated_tree_cache_table()

        cache_key = (
            "Friendly Team",
            "Enemy Team",
            3,
            "1-5",
            True,
            "[[1,2,3,4,5],[2,3,4,5,1]]",
        )
        payload = {
            "snapshot": [
                {
                    "text": "Pairings",
                    "values": (0, 0),
                    "tags": ("0",),
                    "open": True,
                    "children": [],
                }
            ],
            "generation_id": 17,
        }

        ui._save_persistent_tree_snapshot(cache_key, payload)
        loaded = ui._load_persistent_tree_snapshot(cache_key)

        assert loaded is not None
        assert loaded["generation_id"] == 17
        expected_snapshot = json.loads(json.dumps(payload["snapshot"]))
        assert loaded["snapshot"] == expected_snapshot


def _payload(generation_id: int) -> dict:
    return {
        "snapshot": [{"text": "Pairings", "values": (0, 0), "tags": ("0",), "open": True, "children": []}],
        "generation_id": generation_id,
    }


def test_generated_tree_cache_accepts_the_real_build_key_shape():
    """The key `_build_tree_cache_key` actually returns must round-trip.

    That function appends the engine and the risk-columns flag, making an
    eight-field key, but the persistence helpers unpacked exactly six. The
    unpack sat above their try blocks, so every real call raised ValueError and
    snapshot persistence was dead on the default widget engine. The existing
    round-trip test missed it by hand-building a six-field key.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        ui = _build_minimal_ui(tmpdir, "real_key_shape.db")
        ui._ensure_generated_tree_cache_table()

        cache_key = ("Us", "Them", 3, "1-5", True, "[[1,2],[3,4]]", "widget", False)

        ui._save_persistent_tree_snapshot(cache_key, _payload(21))
        loaded = ui._load_persistent_tree_snapshot(cache_key)

        assert loaded is not None, "eight-field key must round-trip"
        assert loaded["generation_id"] == 21


def test_risk_and_engine_flags_do_not_share_a_cached_row():
    """Keys differing only past the sixth field must not collide.

    Risk reporting adds four columns to every values tuple, so restoring a
    risk-on snapshot into a risk-off run mismatches the treeview. The extra
    discriminators are folded into the signature column precisely to keep these
    rows apart.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        ui = _build_minimal_ui(tmpdir, "risk_isolation.db")
        ui._ensure_generated_tree_cache_table()

        base = ("Us", "Them", 3, "1-5", True, "[[1,2],[3,4]]")
        risk_off = base + ("model", False)
        risk_on = base + ("model", True)

        ui._save_persistent_tree_snapshot(risk_off, _payload(1))
        ui._save_persistent_tree_snapshot(risk_on, _payload(2))

        assert ui._load_persistent_tree_snapshot(risk_off)["generation_id"] == 1
        assert ui._load_persistent_tree_snapshot(risk_on)["generation_id"] == 2

        # A six-field key stays distinct from both, so older callers are unaffected.
        ui._save_persistent_tree_snapshot(base, _payload(3))
        assert ui._load_persistent_tree_snapshot(base)["generation_id"] == 3
        assert ui._load_persistent_tree_snapshot(risk_on)["generation_id"] == 2


def test_generation_id_propagates_to_tree_generator():
    root = tk.Tk()
    root.withdraw()
    tree = ttk.Treeview(root, columns=("Rating", "Sort Value"))

    ui = UiManager.__new__(UiManager)
    ui._tree_generation_id = 0
    ui.tree_generator = TreeGenerator(treeview=DummyTreeView(tree), strategic_preferences={})

    ui._set_tree_generation_id(33)

    assert ui._tree_generation_id == 33
    assert ui.tree_generator._generation_id == 33

    root.destroy()
