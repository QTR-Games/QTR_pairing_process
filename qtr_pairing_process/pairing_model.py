"""Tk-free pairing tree model and projection adapter."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PairingNode:
    text: str
    base: int
    depth: int
    is_opponent_choice: bool
    parent: PairingNode | None = None
    children: list[PairingNode] = field(default_factory=list)
    counts_toward_total: bool = False
    base_for_our_team: int = 0
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
    state_attacker: str | None = None
    state_attacker_side: str = ""
    state_choosing_side: str = ""
    state_our_pool: frozenset[str] = field(default_factory=frozenset)
    state_opponent_pool: frozenset[str] = field(default_factory=frozenset)
    state_choice_pool: frozenset[str] = field(default_factory=frozenset)
    # Risk summary, populated only when QTR_RISK is enabled. -1.0 means "not
    # computed" so the projection can tell an unscored node from a genuine 0%.
    risk_win_prob: float = -1.0
    risk_floor: int = 0
    risk_p10: int = 0
    risk_std: float = -1.0


class TreeProjector:
    """Project a PairingNode tree into a ttk.Treeview and map ids back."""

    LAZY_PLACEHOLDER_TAG = "__qtr_lazy_placeholder__"

    #: Append the risk columns to every projected row. Off by default so the
    #: golden-master digests -- which hash the projected ``values`` tuple --
    #: stay byte-identical unless risk reporting is explicitly requested.
    RISK_COLUMNS_ENABLED = False

    RISK_COLUMNS = ("P(win)", "Floor", "P10", "Sigma")

    # Column id -> model attribute, for sorting. Kept next to RISK_COLUMNS so a
    # renamed column cannot silently stop being sortable.
    RISK_SORT_FIELDS = {
        "P(win)": "risk_win_prob",
        "Floor": "risk_floor",
        "P10": "risk_p10",
        "Sigma": "risk_std",
    }

    #: ``annotate_risk`` fills every risk field in one pass, so this single
    #: field answers "was this node scored at all". Floor and P10 cannot carry
    #: their own sentinel: 0 is a legitimate banked total, so a per-field check
    #: would sort genuinely-zero rows as if they were blank.
    RISK_ANNOTATION_FIELD = "risk_win_prob"

    @classmethod
    def risk_sort_key(cls, node, column_id, reverse):
        """Sort key for ``column_id``, or ``None`` when it is not a risk column.

        Shared by the eager and lazy sort paths so the two can never disagree
        about which rows are blank. Unannotated nodes sink to the bottom in
        both directions rather than masquerading as a genuinely low score.
        """
        field = cls.RISK_SORT_FIELDS.get(column_id)
        if field is None:
            return None
        annotation = float(getattr(node, cls.RISK_ANNOTATION_FIELD, -1.0))
        if annotation < 0.0:
            return float("-inf") if reverse else float("inf")
        return float(getattr(node, field, 0.0))

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

    def project(
        self,
        model: PairingNode | None,
        treeview,
        *,
        lazy: bool = False,
        expanded_node_ids: set[int] | None = None,
    ) -> None:
        tree = treeview.tree if hasattr(treeview, "tree") else treeview
        if expanded_node_ids is None:
            expanded_node_ids = self.expanded_node_ids(tree)
        yview = None
        try:
            yview = tree.yview()
        except Exception:
            yview = None
        selected_node_ids: list[int] = []
        try:
            for widget_id in tree.selection():
                node = self.widget_to_node.get(widget_id)
                if node is not None:
                    selected_node_ids.append(id(node))
        except Exception:
            selected_node_ids = []
        focus_node_id = None
        try:
            focus_widget_id = tree.focus()
        except Exception:
            focus_widget_id = ""
        if focus_widget_id:
            focus_node = self.widget_to_node.get(focus_widget_id)
            if focus_node is not None:
                focus_node_id = id(focus_node)
        tree.delete(*tree.get_children())
        self.widget_to_node.clear()
        self.node_to_widget.clear()
        if model is None:
            return
        if lazy:
            self._project_node_lazy(
                model,
                tree,
                "",
                materialize_through_depth=1,
                expanded_node_ids=expanded_node_ids or set(),
            )
        else:
            self._project_node(model, tree, "", expanded_node_ids=expanded_node_ids or set())
        if yview:
            try:
                tree.yview_moveto(yview[0])
            except Exception:
                pass
        if selected_node_ids:
            restored_selection = [
                widget_id
                for node_id in selected_node_ids
                if (widget_id := self.node_to_widget.get(node_id)) is not None
            ]
            if restored_selection:
                try:
                    tree.selection_set(restored_selection)
                except Exception:
                    pass
        if focus_node_id is not None:
            restored_focus = self.node_to_widget.get(focus_node_id)
            if restored_focus is not None:
                try:
                    tree.focus(restored_focus)
                except Exception:
                    pass

    def _project_node(
        self,
        node: PairingNode,
        tree,
        parent_id: str,
        *,
        expanded_node_ids: set[int],
    ) -> str:
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
        if id(node) in expanded_node_ids:
            try:
                tree.item(widget_id, open=True)
            except Exception:
                pass
        for child in node.children:
            self._project_node(
                child,
                tree,
                widget_id,
                expanded_node_ids=expanded_node_ids,
            )
        return widget_id

    def _project_node_lazy(
        self,
        node: PairingNode,
        tree,
        parent_id: str,
        *,
        materialize_through_depth: int,
        expanded_node_ids: set[int],
    ) -> str:
        widget_id = self._insert_node(node, tree, parent_id)
        is_expanded = id(node) in expanded_node_ids
        if is_expanded:
            tree.item(widget_id, open=True)

        should_materialize_children = (
            node.depth < materialize_through_depth or is_expanded
        )
        if should_materialize_children:
            for child in node.children:
                self._project_node_lazy(
                    child,
                    tree,
                    widget_id,
                    materialize_through_depth=materialize_through_depth,
                    expanded_node_ids=expanded_node_ids,
                )
        elif node.children:
            self._insert_placeholder(tree, widget_id)
        return widget_id

    def _insert_node(self, node: PairingNode, tree, parent_id: str) -> str:
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
        return widget_id

    def _insert_placeholder(self, tree, parent_id: str) -> str:
        return tree.insert(parent_id, "end", text="", tags=(self.LAZY_PLACEHOLDER_TAG,))

    def is_placeholder(self, tree, widget_id: str) -> bool:
        try:
            tags = tree.item(widget_id, "tags") or ()
        except Exception:
            return False
        if isinstance(tags, str):
            tags = (tags,)
        return self.LAZY_PLACEHOLDER_TAG in set(str(tag) for tag in tags)

    def expanded_node_ids(self, tree) -> set[int]:
        expanded: set[int] = set()
        for widget_id, node in list(self.widget_to_node.items()):
            try:
                if tree.item(widget_id, "open"):
                    expanded.add(id(node))
            except Exception:
                continue
        return expanded

    def materialize_children(self, treeview, widget_id: str) -> bool:
        tree = treeview.tree if hasattr(treeview, "tree") else treeview
        node = self.widget_to_node.get(widget_id)
        if node is None or not node.children:
            return False

        existing_children = tree.get_children(widget_id)
        if existing_children and not all(
            self.is_placeholder(tree, child_id) for child_id in existing_children
        ):
            return False

        if existing_children:
            tree.delete(*existing_children)

        for child in node.children:
            self._project_node_lazy(
                child,
                tree,
                widget_id,
                materialize_through_depth=child.depth,
                expanded_node_ids=set(),
            )
        return True

    def _values_for(self, node: PairingNode) -> tuple[int, int, int, int]:
        return self.values_for(node)

    @classmethod
    def values_for(cls, node: PairingNode) -> tuple[int, ...]:
        if node.parent is None and node.depth == 0:
            return ()
        values: tuple = (
            int(node.base),
            int(node.sort_value),
            int(node.display_confidence),
            int(node.display_resistance),
        )
        if cls.RISK_COLUMNS_ENABLED:
            values = values + cls.risk_values_for(node)
        return values

    @classmethod
    def risk_values_for(cls, node: PairingNode) -> tuple[str, ...]:
        """Human-readable risk cells.

        Rendered as strings because these are the numbers a user is meant to
        read directly -- a probability in percent and totals in points -- not
        packed integers to be parsed back out again.
        """
        if node.risk_win_prob < 0.0:
            return ("", "", "", "")
        return (
            f"{node.risk_win_prob * 100.0:.1f}%",
            str(int(node.risk_floor)),
            str(int(node.risk_p10)),
            f"{node.risk_std:.1f}",
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
