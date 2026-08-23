# Refactor Execution Plan

Companion to [`REFACTOR_ANALYSIS.md`](REFACTOR_ANALYSIS.md), which contains the
measurements this plan acts on. Read that first.

Date: 2026-08-23
Fallback point: **`v2.1.4-fallback`** → `2ed26e6` (pushed). Restore with
`git checkout v2.1.4-fallback`.

---

## Ordering and why

Requested order was rendering → math → sensitivity. That is correct, and the
dependency graph confirms it:

```
p0 fallback tag  (done)
        │
p1a golden master  ────────────┐   safety net; nothing else is safe without it
        │                      │
p1b domain model               │
        │                      │
p1c adapter + feature flag ────┤   the keystone
        │                      │
        ├── p2  virtualize rendering ──── p5 split god class (deferred)
        │
        ├── p3a canonical memo ── p3b alpha-beta ── p4 decision-sensitivity
        │
        └── p3c fix v1 optimistic propagation
```

**Decision-sensitivity must come last** because it is not a display feature. It
needs the exact guaranteed floor for *every* opening move to compute the swing
between best and worst. That requires the solver from p3b. Sequencing it earlier
would mean computing it from the current fused heuristic, which would produce a
confident-looking number with no defensible meaning.

**p2 and p3 are independent of each other.** Both depend only on p1c. Rendering
touches the projection layer; math touches the solver. They can run in parallel
once the seam exists.

---

## The keystone insight

While mapping the call sites, a pattern emerged that changes the risk profile of
this work. `ui_manager_v2` contains a large amount of machinery whose *only*
purpose is avoiding the Tk tax:

| Mechanism | What it actually is |
|---|---|
| `_suppress_display_updates` | skip widget writes during compute |
| `_confidence_aux_tags_enabled` | skip writing `floor2_`/`ceiling2_` tags |
| `_materialize_strategic_tags_on_memo_hit` | skip tag writes on memo hit |
| `_is_metric_stale` / `_mark_metric_fresh` | avoid recomputing because recompute is expensive |
| `lazy_sort_on_expand`, `recurse_mode="expanded"` | sort only expanded nodes |
| `_capture_tree_snapshot` / `_restore_tree_snapshot` | serialize the whole widget to skip regeneration |
| persistent memo export/import | persist across sessions because rebuild is slow |

None of this is domain logic. It is all scar tissue from storing solver state in
a widget. **The refactor should therefore make `ui_manager_v2` smaller, not
bigger.** That materially lowers the risk of p5 later, and it means p1 pays for
itself twice.

Do not delete this machinery in p1. Leave it inert and remove it in a later,
separate pass once the model path is proven — one behavioral change at a time.

---

## Phase 1 — scope

### p1a. Golden-master characterization harness

*Status: in progress.*

Capture the exact current output of the engine — node text, `values`, sorted
`tags`, and **sibling order** — for deterministic 3v3 / 4v4 / 5v5 fixtures across
every sort mode, serialized to committed JSON. Tk item IDs are normalized out
(they are allocation-order dependent and would produce false diffs).

Adds new files only. No production code touched. This is the oracle every later
phase is graded against.

### p1b. Tk-free domain model

New module `qtr_pairing_process/pairing_model.py`:

```python
@dataclass(slots=True)
class PairingNode:
    text: str
    base: int
    depth: int                    # stored, not derived by walking to root
    children: list["PairingNode"]
    parent: "PairingNode | None"
    is_opponent_choice: bool      # resolved once at build time
    cumulative: int = 0
    cumulative2: int = 0
    confidence: int = 0
    confidence2: int = 0
    floor2: int = 0
    ceiling2: int = 0
    regret2: int = 0
    resistance: int = 0
    resistance2: int = 0
    strategic3: int = 0
    strategic3_exploit: int = 0
```

Two changes here are worth calling out because they delete whole classes of cost:

- **`depth` is stored.** `_calculate_node_depth` currently walks to the root via
  `tree.parent()` for every node on every pass. Depth is known for free during
  construction.
- **`is_opponent_choice` is resolved once at build time.** It is currently
  recomputed per node per pass, and each computation triggers the depth walk
  above.

`TreeGenerator` computation methods are rewritten to traverse `PairingNode`
objects. Field access replaces tag serialization — no `f'cumulative_{v}'`
formatting, no `int(str(tag).replace(...))` parsing.

Two latent hazards in the current tag scheme disappear as a side effect, and
they are worth naming because both are the kind of bug that stays silent:

**Prefix collision.** The tag namespace is flat and untyped, so
`strategic3_` is a string prefix of `strategic3_exploit_`. Reading the former
matches the latter, and `_extract_prefixed_tag_value` only survives it because
`int("exploit_42")` happens to raise, at which point it *continues the loop*
(line 690). It works by accident of the sibling value being non-numeric. A tag
like `strategic3_v2_` would silently return the wrong field. Dataclass
attributes cannot collide by prefix.

**Silent zeros.** The same accessor wraps its Tk call in `except TypeError:
pass` and falls through to `default=0`. A widget-layer failure therefore yields
a *plausible score* rather than an error — a wrong answer that looks right and
propagates into sorting. In the model, a missing value is an `AttributeError`
at the point of the mistake.

### p1c. Projection adapter + feature flag

New `TreeProjector` owns the model↔widget boundary and the only Tk calls:

- `project(model, treeview)` — writes the model into the widget
- `node_for(widget_id) -> PairingNode` — bidirectional map

The map matters: `ui_manager_v2` calls `get_strategic3_from_tags(node_id)` with a
**widget** id (line 2294), and `ui_manager_v1_original` does the same for
confidence/resistance/cumulative. Those accessors must keep working unchanged, so
they become `self.projector.node_for(node_id).strategic3`. **The public API of
`TreeGenerator` does not change in p1.** Callers are untouched.

Feature flag `QTR_ENGINE` (`widget` default, `model` opt-in) selects the path.
Both engines can run against the same fixture and be diffed via the p1a harness.
Ship with the flag defaulting to the old path; flip only after equivalence is
proven on all fixtures.

### Phase 1 exit criteria

1. Golden-master suite passes identically under `QTR_ENGINE=widget` and
   `QTR_ENGINE=model` for every fixture and every sort mode.
2. No change to `TreeGenerator`'s public method signatures.
3. Pre-existing test suite passes with no new failures.
4. A recorded before/after timing on the 5v5 fixture.

Expected: the 69x on solver-internal work; end-to-end gain capped by rendering
until p2 lands.

---

## Phase 2 — virtualize rendering

`lazy_tree_view.py` lazily creates *scrollbars*, not rows; `populate_tree` is dead
in production (`enable_demo_population` is off). All 48,750 nodes are inserted to
show ~40.

Project only visible/expanded nodes into the widget and fill children on
`<<TreeviewOpen>>` from the model. This is where the 4,135 ms redraw and the
4.2 s freeze die. It requires no change of UI toolkit.

Once this works, `_capture_tree_snapshot`/`_restore_tree_snapshot` and the
persistent tree cache become largely redundant — rebuilding the model is ~30 ms.

Exit: `teams.change.redraw` and `event_loop.lag` both under ~100 ms on a 5v5,
measured through the existing `perf` spans.

---

## Phase 3 — math

### p3a. Canonical-state memo key

Replace the path-text key
(`_build_structural_memo_key`, which walks ancestors calling `tree.item()` and is
invoked **twice per node**) with:

```python
(attacker, side, frozenset(our_pool), frozenset(their_pool))
```

Order of prior picks is irrelevant; only who remains matters. This is what
collapses the measured 36.6x redundancy (48,750 evaluations → 625 distinct
states). Note this **invalidates persisted memo snapshots** — bump
`_memo_schema_version` so old payloads are rejected rather than misread.

### p3b. Alpha-beta pruning

Cut branches provably worse than one already secured. Sound — never changes the
result. PoC measured 142.74 ms → 3.64 ms (39.2x) with asserted-identical values.

### p3c. Fix v1 optimistic propagation

`calculate_all_path_values` propagates `max()` at opponent levels while
`sort_children_by_cumulative` sorts those levels adversarially. The score assumes
the opponent cooperates. Either align it with the correct v2 handling
(`alpha*min + (1-alpha)*mean`) or retire the v1 mode.

**This one changes results by design** — it is the only phase that will
legitimately fail the golden master. Re-baseline deliberately, with the diff
reviewed, and document it in release notes.

---

## Phase 4 — decision-sensitivity

Two user-facing additions, both cheap once p3b lands:

1. **Guaranteed floor per opening move** — replaces the opaque fused score with
   *"put up A4: guaranteed ≥ 14 pts."* A defensible claim.
2. **Decision-sensitivity indicator** — the swing between best and worst opener.

Measured basis for (2):

| Rating structure | Mean swing | % of rosters where choice worth ≥2 pts |
|---|---|---|
| tiered skill ladder | 0.50 | **0%** |
| uniform random | 1.38 | 32% |
| specialists / counters | 1.95 | **65%** |

The app currently sounds equally confident in all three cases. Telling the user
*"this is worth 0.5 pts, don't agonize"* vs *"this is worth 4 pts, think hard"*
directs scarce attention during a live round.

---

## Phase 5 — split `ui_manager_v2` (deferred)

7,999 lines / 367 methods / one class. Only after 1–3, and after the scar-tissue
removal pass, because both shrink the target. Carve along the seams already
visible in method prefixes: events (56 `on_*`), accessors (22 `get_*`), rendering
(19 `update_*`, 12 `build_*`, 8 `create_*`), persistence (8 `load_*`, 5 `save_*`,
6 `import_*`), sorting (6), cache invalidation (4).

---

## Phase 6 — evaluate React (optional)

Only meaningful after p1c. With a UI-independent core this becomes a bounded
experiment against the same solver, with `v2.1.4-fallback` and the Tk path both
intact. Deliberately last.

---

## Risk controls

- `v2.1.4-fallback` tag pushed before any code changes.
- Golden master gates every phase; the one intentional break (p3c) is
  re-baselined deliberately with a reviewed diff.
- Feature flag keeps the old engine live and selectable through Phase 1.
- One outcome per PR, per repo convention.
- Scar-tissue removal is its own pass, never bundled with a behavioral change.
