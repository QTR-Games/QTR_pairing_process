"""Shared golden-master capture helpers for the TreeGenerator solver."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tkinter as tk

from qtr_pairing_process.lazy_tree_view import LazyTreeView
from qtr_pairing_process.tree_generator import TreeGenerator

from golden_master_scenarios import GoldenScenario


SNAPSHOT_SCHEMA_VERSION = 1
SNAPSHOT_DIR = Path(__file__).resolve().parent / "golden_fixtures"
FULL_FIDELITY_NODE_THRESHOLD = 5000
RECORD_SEPARATOR = "\x1e"


def _run_cumulative(generator: TreeGenerator) -> None:
    generator.sort_by_cumulative_value()


def _run_risk_adjusted_confidence(generator: TreeGenerator) -> None:
    generator.sort_by_risk_adjusted_confidence()


def _run_opponent_response_simulation(generator: TreeGenerator) -> None:
    generator.sort_by_opponent_response_simulation()


def _run_strategic_optimal(generator: TreeGenerator) -> None:
    generator.sort_by_strategic_optimal()


def _run_enhanced_v3_scores(generator: TreeGenerator) -> None:
    generator.calculate_all_path_values_enhanced("")
    generator.calculate_confidence_scores_enhanced("")
    generator.calculate_counter_resistance_scores_enhanced("")
    generator.calculate_strategic3_scores("")


SORT_MODES: dict[str, Callable[[TreeGenerator], None]] = {
    "cumulative": _run_cumulative,
    "risk_adjusted_confidence": _run_risk_adjusted_confidence,
    "opponent_response_simulation": _run_opponent_response_simulation,
    "strategic_optimal": _run_strategic_optimal,
    "enhanced_v3_scores": _run_enhanced_v3_scores,
}


@contextmanager
def tk_treeview():
    root = tk.Tk()
    root.withdraw()
    treeview = LazyTreeView(
        print_output=False,
        master=root,
        columns=("base_rating", "cumulative", "confidence", "resistance"),
    )
    try:
        yield treeview
    finally:
        root.destroy()


def generate_snapshot(scenario: GoldenScenario, sort_mode: str) -> dict:
    if sort_mode not in SORT_MODES:
        raise KeyError(f"unknown sort mode: {sort_mode}")

    with tk_treeview() as treeview:
        generator = TreeGenerator(
            treeview=treeview,
            sort_alpha=False,
            strategic_preferences={},
            rating_system=scenario.rating_system,
        )
        generator.generate_combinations(
            list(scenario.our_players),
            list(scenario.opponent_players),
            scenario.our_ratings,
            scenario.opponent_ratings,
            our_team_first=scenario.our_team_first,
        )
        SORT_MODES[sort_mode](generator)
        snapshot = _capture_tree_snapshot(
            treeview.tree,
            metadata={
                "schema_version": SNAPSHOT_SCHEMA_VERSION,
                "scenario": scenario.slug,
                "description": scenario.description,
                "sort_mode": sort_mode,
                "our_team_first": scenario.our_team_first,
                "rating_system": scenario.rating_system,
                "our_players": list(scenario.our_players),
                "opponent_players": list(scenario.opponent_players),
            },
        )

    return snapshot


def snapshot_path(scenario_slug: str, sort_mode: str) -> Path:
    return SNAPSHOT_DIR / f"{scenario_slug}__{sort_mode}.json"


def write_snapshot(snapshot: dict) -> Path:
    scenario_slug = snapshot["metadata"]["scenario"]
    sort_mode = snapshot["metadata"]["sort_mode"]
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    path = snapshot_path(scenario_slug, sort_mode)
    json_kwargs = {"sort_keys": True, "ensure_ascii": False}
    if snapshot["node_count"] > 1000:
        json_kwargs["separators"] = (",", ":")
    else:
        json_kwargs["indent"] = 2
    path.write_text(
        json.dumps(snapshot, **json_kwargs) + "\n",
        encoding="utf-8",
    )
    return path


def read_snapshot(scenario_slug: str, sort_mode: str) -> dict:
    path = snapshot_path(scenario_slug, sort_mode)
    return json.loads(path.read_text(encoding="utf-8"))


def find_snapshot_differences(expected: dict, actual: dict, limit: int = 12) -> list[str]:
    differences: list[str] = []

    for key in ("metadata", "fidelity", "node_count", "digest"):
        if expected.get(key) != actual.get(key):
            differences.append(
                f"{key}: expected {expected.get(key)!r}, actual {actual.get(key)!r}"
            )
            if len(differences) >= limit:
                return differences

    differences.extend(
        find_tree_differences(expected.get("tree", []), actual.get("tree", []), limit=limit)
    )
    return differences[:limit]


def find_digest_snapshot_differences(
    expected: dict,
    actual: dict,
    limit: int = 20,
) -> list[str]:
    differences: list[str] = []

    for key in ("metadata", "fidelity", "node_count", "depth_histogram", "digest"):
        if expected.get(key) != actual.get(key):
            differences.append(
                f"{key}: expected {expected.get(key)!r}, actual {actual.get(key)!r}"
            )
            if len(differences) >= limit:
                return differences

    expected_subtrees = expected.get("subtree_digests", {})
    actual_subtrees = actual.get("subtree_digests", {})
    for path in sorted(set(expected_subtrees) | set(actual_subtrees)):
        if len(differences) >= limit:
            return differences
        expected_digest = expected_subtrees.get(path)
        actual_digest = actual_subtrees.get(path)
        if expected_digest != actual_digest:
            differences.append(
                f"subtree {path}: expected {expected_digest!r}, actual {actual_digest!r}"
            )

    top_level_differences = find_tree_differences(
        expected.get("top_level", []),
        actual.get("top_level", []),
        limit=max(0, limit - len(differences)),
    )
    differences.extend(f"top_level {difference}" for difference in top_level_differences)
    return differences[:limit]


def find_tree_differences(
    expected_tree: Iterable[dict],
    actual_tree: Iterable[dict],
    limit: int = 12,
) -> list[str]:
    differences: list[str] = []
    expected_nodes = list(_flatten_nodes(expected_tree))
    actual_nodes = list(_flatten_nodes(actual_tree))
    if len(expected_nodes) != len(actual_nodes):
        differences.append(
            f"preorder node length: expected {len(expected_nodes)}, actual {len(actual_nodes)}"
        )

    for index in range(max(len(expected_nodes), len(actual_nodes))):
        if len(differences) >= limit:
            break
        if index >= len(expected_nodes):
            path, node = actual_nodes[index]
            differences.append(f"extra actual node at {path}: {_summarize_node(node)}")
            continue
        if index >= len(actual_nodes):
            path, node = expected_nodes[index]
            differences.append(f"missing actual node at {path}: {_summarize_node(node)}")
            continue

        expected_path, expected_node = expected_nodes[index]
        actual_path, actual_node = actual_nodes[index]
        fields = ("path", "text", "values", "tags")
        if expected_path != actual_path:
            differences.append(f"node #{index} path: expected {expected_path}, actual {actual_path}")
            continue

        for field in fields:
            expected_value = expected_path if field == "path" else expected_node.get(field)
            actual_value = actual_path if field == "path" else actual_node.get(field)
            if expected_value != actual_value:
                differences.append(
                    f"{expected_path} {field}: expected {expected_value!r}, actual {actual_value!r}"
                )
                break

        expected_child_count = len(expected_node.get("children", []))
        actual_child_count = len(actual_node.get("children", []))
        if expected_child_count != actual_child_count:
            differences.append(
                f"{expected_path} child_count: "
                f"expected {expected_child_count}, actual {actual_child_count}"
            )

    return differences


def _capture_tree_snapshot(tree: tk.ttk.Treeview, metadata: dict) -> dict:
    records = list(_iter_canonical_records(tree, ""))
    node_count = len(records)
    digest = _digest_records(record for _, _, record in records)
    depth_histogram = _depth_histogram(records)
    fidelity = "full" if node_count <= FULL_FIDELITY_NODE_THRESHOLD else "digest"

    snapshot = {
        "metadata": metadata,
        "fidelity": fidelity,
        "node_count": node_count,
        "digest": digest,
    }

    if fidelity == "full":
        snapshot["tree"] = _serialize_children(tree, "")
        return snapshot

    snapshot["depth_histogram"] = depth_histogram
    snapshot["top_level"] = _serialize_top_level_decisions(tree)
    snapshot["subtree_digests"] = _subtree_digests(tree)
    return snapshot


def _serialize_children(
    tree: tk.ttk.Treeview,
    parent: str,
    path: tuple[int, ...] = (),
) -> list[dict]:
    serialized = []
    for index, item_id in enumerate(tree.get_children(parent)):
        child_path = (*path, index)
        serialized.append(_serialize_node(tree, item_id, child_path, max_depth=None))
    return serialized


def _serialize_top_level_decisions(tree: tk.ttk.Treeview) -> list[dict]:
    pairings_roots = tree.get_children("")
    if not pairings_roots:
        return []

    top_level = []
    pairings_root = pairings_roots[0]
    for index, item_id in enumerate(tree.get_children(pairings_root)):
        top_level.append(_serialize_node(tree, item_id, (0, index), max_depth=2))
    return top_level


def _serialize_node(
    tree: tk.ttk.Treeview,
    item_id: str,
    path: tuple[int, ...],
    max_depth: int | None,
) -> dict:
    item = tree.item(item_id)
    node = {
        "path": ".".join(str(part) for part in path),
        "text": item.get("text", ""),
        "values": list(item.get("values", ())),
        "tags": sorted(str(tag) for tag in item.get("tags", ())),
        "children": [],
    }

    effective_depth = _effective_depth(path)
    if max_depth is None or effective_depth < max_depth:
        children = []
        for index, child_id in enumerate(tree.get_children(item_id)):
            children.append(_serialize_node(tree, child_id, (*path, index), max_depth))
        node["children"] = children
    return node


def _iter_canonical_records(
    tree: tk.ttk.Treeview,
    parent: str,
    path: tuple[int, ...] = (),
) -> Iterable[tuple[str, int, str]]:
    for index, item_id in enumerate(tree.get_children(parent)):
        child_path = (*path, index)
        yield from _iter_canonical_records_for_item(tree, item_id, child_path)


def _iter_canonical_records_for_item(
    tree: tk.ttk.Treeview,
    item_id: str,
    path: tuple[int, ...],
) -> Iterable[tuple[str, int, str]]:
    item = tree.item(item_id)
    path_text = ".".join(str(part) for part in path)
    values = list(item.get("values", ()))
    tags = sorted(str(tag) for tag in item.get("tags", ()))
    record = "|".join(
        (
            path_text,
            str(item.get("text", "")),
            json.dumps(values, ensure_ascii=False, separators=(",", ":")),
            json.dumps(tags, ensure_ascii=False, separators=(",", ":")),
        )
    )
    yield path_text, _effective_depth(path), record
    for index, child_id in enumerate(tree.get_children(item_id)):
        yield from _iter_canonical_records_for_item(tree, child_id, (*path, index))


def _subtree_digests(tree: tk.ttk.Treeview) -> dict[str, str]:
    pairings_roots = tree.get_children("")
    if not pairings_roots:
        return {}

    pairings_root = pairings_roots[0]
    digests = {}
    for index, item_id in enumerate(tree.get_children(pairings_root)):
        path = (0, index)
        path_text = ".".join(str(part) for part in path)
        records = (record for _, _, record in _iter_canonical_records_for_item(tree, item_id, path))
        digests[path_text] = _digest_records(records)
    return digests


def _digest_records(records: Iterable[str]) -> str:
    digest = hashlib.sha256()
    first = True
    for record in records:
        if not first:
            digest.update(RECORD_SEPARATOR.encode("utf-8"))
        digest.update(record.encode("utf-8"))
        first = False
    return digest.hexdigest()


def _depth_histogram(records: Iterable[tuple[str, int, str]]) -> dict[str, int]:
    histogram: dict[str, int] = {}
    for _, depth, _ in records:
        key = str(depth)
        histogram[key] = histogram.get(key, 0) + 1
    return dict(sorted(histogram.items(), key=lambda item: int(item[0])))


def _effective_depth(path: tuple[int, ...]) -> int:
    return max(0, len(path) - 1)


def _count_nodes(nodes: Iterable[dict]) -> int:
    return sum(1 + _count_nodes(node.get("children", [])) for node in nodes)


def _flatten_nodes(nodes: Iterable[dict]) -> Iterable[tuple[str, dict]]:
    for node in nodes:
        yield node.get("path", ""), node
        yield from _flatten_nodes(node.get("children", []))


def _summarize_node(node: dict) -> str:
    return (
        f"text={node.get('text')!r} values={node.get('values')!r} "
        f"tags={node.get('tags')!r}"
    )
