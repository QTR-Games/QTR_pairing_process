from __future__ import annotations

from qtr_pairing_process.pairing_model import PairingNode, TreeProjector
from qtr_pairing_process.tree_generator import TreeGenerator


def _node(
    text: str,
    base: int,
    *,
    parent: PairingNode | None = None,
    attacker: str = "Comet",
    attacker_side: str = "our",
    choosing_side: str = "opponent",
    our_pool: frozenset[str] = frozenset({"Comet", "Drift"}),
    opponent_pool: frozenset[str] = frozenset({"Gale", "Havoc"}),
    choice_pool: frozenset[str] = frozenset(),
) -> PairingNode:
    node = PairingNode(
        text=text,
        base=base,
        depth=0 if parent is None else parent.depth + 1,
        is_opponent_choice=choosing_side == "opponent",
        parent=parent,
        state_attacker=attacker,
        state_attacker_side=attacker_side,
        state_choosing_side=choosing_side,
        state_our_pool=our_pool,
        state_opponent_pool=opponent_pool,
        state_choice_pool=choice_pool,
    )
    if parent is not None:
        parent.children.append(node)
    return node


def test_canonical_key_ignores_ancestor_order_but_path_key_does_not():
    gen = TreeGenerator(treeview=None)
    gen.engine = "model"
    gen._model_team_size = 5

    root = _node("Pairings", 0, attacker=None, choosing_side="root")
    left_parent = _node(
        "North vs Sable (10/10) OR Talon (3/10)",
        10,
        parent=root,
        attacker="North",
        choice_pool=frozenset({"Sable", "Talon"}),
    )
    right_parent = _node(
        "North vs Sable (10/10) OR Umber (2/10)",
        10,
        parent=root,
        attacker="North",
        choice_pool=frozenset({"Sable", "Umber"}),
    )
    first = _node("Talon rating 3", 3, parent=left_parent)
    second = _node("Talon rating 3", 3, parent=right_parent)

    assert gen._build_canonical_memo_key_model(first) == gen._build_canonical_memo_key_model(second)
    assert gen._build_structural_path_memo_key_model(first) != gen._build_structural_path_memo_key_model(second)


def test_model_memo_hit_materializes_same_strategic_tags_as_fresh_node():
    gen = TreeGenerator(treeview=None)
    gen.engine = "model"
    gen._model_team_size = 5

    root = _node("Pairings", 0, attacker=None, choosing_side="root")
    gen.model_root = root
    first_parent = _node("Parent A", 4, parent=root, attacker="North")
    second_parent = _node("Parent B", 4, parent=root, attacker="North")
    fresh = _node("Talon rating 3", 3, parent=first_parent)
    memo_hit = _node("Talon rating 3", 3, parent=second_parent)

    for node in (root, first_parent, second_parent, fresh, memo_hit):
        gen._set_model_metrics(
            node,
            {
                "cumulative2_": 10 + node.depth,
                "confidence2_": 50 + node.depth,
                "floor2_": 45 + node.depth,
                "ceiling2_": 55 + node.depth,
                "regret2_": 10,
                "resistance2_": 60 - node.depth,
            },
        )

    gen._calculate_strategic3_scores_model("")

    stats = gen.get_memoization_stats()
    assert stats["hits"] >= 1
    assert TreeProjector.tags_for(memo_hit) == TreeProjector.tags_for(fresh)
    assert TreeProjector.values_for(memo_hit) == TreeProjector.values_for(fresh)
    assert "strategic3_exploit_0" in TreeProjector.tags_for(memo_hit)
