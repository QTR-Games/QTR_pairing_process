"""Tk-free pairing tree model and projection adapter."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PairingNode:
    text: str
    base: int
    depth: int
    is_opponent_choice: bool
    parent: "PairingNode | None" = None
    children: list["PairingNode"] = field(default_factory=list)
    cumulative: int = 0
    cumulative2: int = 0
    confidence: int = 0
    confidence2: int = 0
    floor: int = 0
    ceiling: int = 0
    floor2: int = 0
    ceiling2: int = 0
    regret2: int = 0
    resistance: int = 0
    resistance2: int = 0
    strategic: int = 0
    strategic3: int = 0
    strategic3_exploit: int = 0
    tag_mask: int = 0
    sort_value: int = 0
    display_confidence: int = 0
    display_resistance: int = 0


class TreeProjector:
    """Project a PairingNode tree into a ttk.Treeview and map ids back."""

    _TAG_ORDER = (
        "cumulative_",
        "confidence_",
        "floor_",
        "ceiling_",
        "resistance_",
        "cumulative2_",
        "confidence2_",
        "regret2_",
        "floor2_",
        "ceiling2_",
        "resistance2_",
        "strategic3_",
        "strategic3_exploit_",
        "strategic_",
    )
    _PREFIX_TO_ATTR = {
        "cumulative_": "cumulative",
        "confidence_": "confidence",
        "floor_": "floor",
        "ceiling_": "ceiling",
        "resistance_": "resistance",
        "cumulative2_": "cumulative2",
        "confidence2_": "confidence2",
        "regret2_": "regret2",
        "floor2_": "floor2",
        "ceiling2_": "ceiling2",
        "resistance2_": "resistance2",
        "strategic_": "strategic",
        "strategic3_": "strategic3",
        "strategic3_exploit_": "strategic3_exploit",
    }
    _PREFIX_BITS = {prefix: 1 << index for index, prefix in enumerate(_TAG_ORDER)}

    def __init__(self) -> None:
        self.widget_to_node: dict[str, PairingNode] = {}
        self.node_to_widget: dict[int, str] = {}
        self._active_prefixes: dict[int, set[str]] = {}
        self._sort_values: dict[int, int] = {}
        self._confidence_values: dict[int, int] = {}
        self._resistance_values: dict[int, int] = {}

    def reset_state(self) -> None:
        self.widget_to_node.clear()
        self.node_to_widget.clear()
        self._active_prefixes.clear()
        self._sort_values.clear()
        self._confidence_values.clear()
        self._resistance_values.clear()

    def initialize_node(
        self,
        node: PairingNode,
        *,
        sort_value: int = 0,
        confidence_value: int | None = None,
        resistance_value: int | None = None,
    ) -> None:
        node.sort_value = int(sort_value)
        node.display_confidence = int(
            node.confidence if confidence_value is None else confidence_value
        )
        node.display_resistance = int(
            node.resistance if resistance_value is None else resistance_value
        )

    def set_sort_value(self, node: PairingNode, value: int | float) -> None:
        node.sort_value = int(value)

    def set_confidence_value(self, node: PairingNode, value: int | float) -> None:
        node.display_confidence = int(value)

    def set_resistance_value(self, node: PairingNode, value: int | float) -> None:
        node.display_resistance = int(value)

    def mark_metric(self, node: PairingNode, prefix: str) -> None:
        node.tag_mask |= self._PREFIX_BITS[prefix]

    def mark_metrics(self, node: PairingNode, prefixes: tuple[str, ...] | list[str]) -> None:
        for prefix in prefixes:
            node.tag_mask |= self._PREFIX_BITS[prefix]

    def clear_metric(self, node: PairingNode, prefix: str) -> None:
        node.tag_mask &= ~self._PREFIX_BITS[prefix]

    def has_metric(self, node: PairingNode, prefix: str) -> bool:
        return bool(node.tag_mask & self._PREFIX_BITS[prefix])

    def node_for(self, widget_id: str) -> PairingNode:
        return self.widget_to_node[widget_id]

    def widget_id_for(self, node: PairingNode) -> str | None:
        return self.node_to_widget.get(id(node))

    def project(self, model: PairingNode | None, treeview) -> None:
        tree = treeview.tree if hasattr(treeview, "tree") else treeview
        tree.delete(*tree.get_children())
        self.widget_to_node.clear()
        self.node_to_widget.clear()
        if model is None:
            return
        self._project_node(model, tree, "")

    def _project_node(self, node: PairingNode, tree, parent_id: str) -> str:
        if node.parent is None and node.depth == 0:
            widget_id = tree.insert(parent_id, "end", text=node.text, tags=self._tags_for(node))
        else:
            widget_id = tree.insert(
                parent_id,
                "end",
                text=node.text,
                values=self._values_for(node),
                tags=self._tags_for(node),
            )
        self.widget_to_node[widget_id] = node
        self.node_to_widget[id(node)] = widget_id
        for child in node.children:
            self._project_node(child, tree, widget_id)
        return widget_id

    def _values_for(self, node: PairingNode) -> tuple[int, int, int, int]:
        return self.values_for(node)

    @classmethod
    def values_for(cls, node: PairingNode) -> tuple[int, ...]:
        if node.parent is None and node.depth == 0:
            return ()
        return (
            int(node.base),
            int(node.sort_value),
            int(node.display_confidence),
            int(node.display_resistance),
        )

    def _tags_for(self, node: PairingNode) -> tuple[str, ...]:
        return self.tags_for(node)

    @classmethod
    def tags_for(cls, node: PairingNode) -> tuple[str, ...]:
        tags = [] if node.parent is None and node.depth == 0 else [str(node.base)]
        for prefix in cls._TAG_ORDER:
            if node.tag_mask & cls._PREFIX_BITS[prefix]:
                attr = cls._PREFIX_TO_ATTR[prefix]
                tags.append(f"{prefix}{int(getattr(node, attr))}")
        return tuple(tags)
