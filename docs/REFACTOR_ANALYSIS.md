# Refactor Analysis — QTR Pairing Process

Status: analysis only. No production code changed by this document.
Date: 2026-08-23
Measured on: this repo @ `repo-refactor-analysis`, Windows, CPython.

---

## TL;DR

**Your math is not slow. Your math is fine.** It is being run through a UI widget.

The single most consequential finding: `TreeGenerator` has no data model. The
`ttk.Treeview` widget *is* the data structure. Every intermediate value the
solver computes is serialized into a widget tag as a string
(`cumulative_7`), then parsed back out with
`int(str(tag).replace('cumulative_', ''))` on the next pass. There are **77
direct Tk widget calls inside the math engine.**

Three numbers frame the whole rest of this document:

| Measurement | Value | Source |
|---|---|---|
| Actual scoring math for a 5v5 | **~38 ms** | your own `perf_log.txt` |
| Redraw for the same operation | **~4,135 ms** | your own `perf_log.txt` |
| Longest logged UI freeze | **4,214 ms** | `event_loop.lag` |

You spent March and April optimizing the 38 ms.

---

## 1. What the tree actually costs

Headless replica of `generate_nested_combinations` (structure only, no Tk):

| Size | Nodes generated | Distinct game states | Redundancy |
|---|---|---|---|
| 3v3 | 117 | 27 | 2.0x |
| 4v4 | 1,944 | 136 | 6.7x |
| 5v5 | **48,750** | **625** | **36.6x** |

Two things fall out of this:

1. A 5v5 materializes **48,750 nodes** — into a widget that shows ~40 rows.
2. There are only **625 genuinely distinct positions**. The engine computes
   each one an average of **36.6 times**.

The pure-Python structural walk of all 48,750 nodes takes **36.6 ms**, which
matches your logged `grid.scenario_calculations` of 38.19 ms almost exactly.
That confirms the model: the computation is already near the speed of simply
*enumerating* the tree. There is nothing left to squeeze in the arithmetic.

---

## 2. The widget-as-database tax (measured)

I benchmarked the exact access patterns from `tree_generator.py` — node
insert, `item()` read + tag rewrite, tag parse-back, and the `parent()` walk
in `_calculate_node_depth` — against the same work on plain Python objects.
20,000 nodes each:

| Operation | Tk-backed | Python model |
|---|---|---|
| insert nodes | 416.0 ms | 10.2 ms |
| read item + rewrite `cumulative_` tag | 212.4 ms | 0.8 ms |
| parse value back out of tags | 138.4 ms | 0.6 ms |
| `parent()` walk to derive depth | 76.6 ms | 0.7 ms |
| **Total** | **843.4 ms** | **12.2 ms** |

**69x**, on identical work. Extrapolated to a real 5v5: **~2.1 s vs ~30 ms** —
and that is one pass. Sorting by strategic score runs *four* full traversals
(cumulative2 → confidence2 → resistance2 → strategic3), each paying this tax.

### Specific hot spots this creates

- **`_calculate_node_depth` (line 1619)** walks to the root via `tree.parent()`
  for every node, and is called by `_is_opponent_choice_level` on every sort
  and scoring pass. Depth is free during recursion — you already know it. This
  is O(N x depth) Tcl round-trips to recover information you threw away.

- **`_build_structural_memo_key` (line 832)** builds the cache key by walking
  the whole ancestor chain calling `tree.item()` per ancestor, and is called
  **twice per node** in `calculate_strategic3_scores` (lines 1148 and 1183). At
  depth 9 that is ~18 Tcl calls to construct a key. **The cache key costs more
  than the computation it is caching.**

- **The memo key is path-text based** (`"structural_path_text_base_rating"`).
  Because it keys on the root-to-node *text path*, two identical game positions
  reached by different orderings hash differently. This is precisely why the
  memo cannot touch the 36.6x redundancy above — it is structurally incapable
  of collapsing transpositions.

- **`collect_nodes("")` (line 1115)** walks the entire tree to gather node IDs,
  then performs 3 x 48,750 tag reads purely to compute min/max ranges for
  normalization.

---

## 3. A correctness bug worth more than the performance work

`calculate_all_path_values` (line 249) — the v1 cumulative sort — propagates
`max()` at **every** level:

```python
max_cumulative = max(max_cumulative, total_cumulative)
```

But `sort_children_by_cumulative` (line 292) correctly recognizes that opponent
levels are adversarial and sorts them ascending, "opponent picks what's worst
for us."

So the ordering acknowledges the opponent fights you, while the score assumes
the opponent cooperates. **The v1 cumulative score is systematically
optimistic.** It reports the value of a line the opponent will never let you
have.

`calculate_all_path_values_enhanced` (line 937) fixes this properly with
`alpha * min + (1 - alpha) * mean` at opponent levels. `calculate_strategic3_scores`
also handles it correctly (line 1203). **The v2/v3 paths are sound; v1 is
still shipped and still reachable.** If any of your March/April "the numbers
seem off" instincts traced back to cumulative sort, this is why.

---

## 4. Can the math be done better? Yes — 39x, exactly.

This is a sequential game with alternating adversarial choice. That is
textbook minimax, and it admits two classical optimizations the current engine
does not use. I built a working solver mirroring your exact branching
structure (`files/poc_minimax.py`):

| Variant | Time | Nodes visited | Cutoffs |
|---|---|---|---|
| exhaustive (current approach) | 142.74 ms | 51,705 | 0 |
| + transposition table | 12.99 ms | 3,555 | 0 |
| + alpha-beta pruning | 12.61 ms | 5,133 | 3,363 |
| **+ both** | **3.64 ms** | **995** | 609 |

**39.2x faster, and the results are asserted identical** — the solver verifies
every variant agrees on the optimal value before reporting.

The two wins are independent and compound:

- **Transposition table keyed on canonical state** — `(attacker, side,
  frozenset(our_pool), frozenset(their_pool))`. Order of prior picks does not
  matter, only who is left. This is the fix for the 36.6x redundancy, and it is
  a *key design change*, not a bigger cache.
- **Alpha-beta pruning** — once a branch is proven worse than one already
  secured, stop evaluating it. Sound: it never changes the answer.

Critically, both require the domain model from section 2 to exist first. You
cannot alpha-beta prune a tree whose nodes must be materialized into a widget
before they can be scored — pruning saves nothing if you already paid to
insert the node.

---

## 5. "Smart sort" — and what would actually be better

Today's strategic3 fuses normalized cumulative/confidence/resistance into one
number and ranks branches by it. It is a reasonable heuristic, but it answers
a question the user did not ask. It reports *"this branch scored 247."* 247 of
what? Against whom? Compared to what?

Three upgrades, in increasing order of value:

### 5a. Report a guaranteed floor, not a fused score

Minimax naturally produces the statement that actually matters at the table:

```
put up A4: guaranteed >= 14 pts
put up A2: guaranteed >= 14 pts
put up A0: guaranteed >= 14 pts
put up A3: guaranteed >= 13 pts
```

*"If you put up A4, you cannot do worse than 14 no matter what they do."*
That is a claim you can defend to a teammate. A fused 0-to-N score is not.

### 5b. Tell the user when the decision does not matter

This is the finding I did not expect. I solved 40 random rosters under three
different rating structures and measured the spread between the best and worst
opening move (`files/poc_sensitivity.py`):

| Rating structure | Mean swing | Max swing | % of rosters where choice is worth >= 2 pts |
|---|---|---|---|
| uniform random | 1.38 | 3 | 32% |
| specialists / hard counters | 1.95 | 4 | **65%** |
| tiered skill ladder | 0.50 | 1 | **0%** |

**When your roster is a straight skill ladder, the pairing decision is nearly
irrelevant — 0% of rosters had a choice worth 2+ points.** When there is real
counter-structure, it is worth up to 4 points and matters in 65% of rosters.

Right now the app presents a confidently-ranked list in both cases. It implies
its top pick is meaningfully better even when every option is within a point.
A **decision-sensitivity indicator** — *"this pairing is worth ~0.5 pts, don't
agonize"* vs *"this one is worth 4 pts, think hard"* — is cheap to compute
(you already have the values) and is the single most purposeful piece of
analysis you could add. It tells the user where to spend their scarce attention
during a live round.

### 5c. Model the opponent, don't assume perfection

Minimax assumes the opponent plays optimally. Real opponents do not. Since you
would have the full state space solved in ~4 ms, you can afford to also report:

- **Exploitability** — how much you give up by playing the safe line if they
  misplay. You already compute a `strategic3_exploit_` spread; with a real
  solver it becomes meaningful.
- **Regret** — for each opening, the cost if you guess their behavior wrong.
- **Risk profile toggle** — maximin (protect the floor) vs expected value
  (assume average play). These genuinely diverge, and which one you want
  depends on whether you are ahead or behind in the match.

---

## 6. The UI

### The god class

`ui_manager_v2.py` is **7,999 lines, 367 methods, one class.** Method-prefix
buckets show at least six distinct responsibilities fused together: event
handling (56 `on_*`), data access (22 `get_*`), rendering (19 `update_*`,
12 `build_*`, 8 `create_*`), persistence (8 `load_*`, 5 `save_*`, 6 `import_*`),
sorting (6), and cache invalidation (4).

### There is no virtualization

`lazy_tree_view.py` is a misnomer. It lazily creates **scrollbars**, not rows.
`enable_demo_population` is disabled in production, so `populate_tree` never
runs. All 48,750 nodes are eagerly inserted so the user can look at ~40 of
them. This is the direct cause of the 4,135 ms redraw.

Virtualization — materializing only visible rows and filling children on
expand — is the highest-leverage UI change available, and it does not require
changing UI toolkits. `ttk.Treeview` supports it fine; the machinery just was
never wired up to real data.

### On moving to React

Honest answer: **the UI toolkit is not your bottleneck, and switching first
would be a mistake.**

A React rewrite would not have fixed any of the top four problems in this
document. Rendering 48,750 DOM nodes would also be slow. Storing solver state
in React component state and re-deriving it every pass would also be slow. You
would carry the same architecture into a new runtime, pay a full rewrite of
8,000 lines of working UI, take on a browser/Electron/Tauri runtime and a
Python-to-JS boundary, and land somewhere similar.

But there is a real version of this idea. **Extract the domain core first.**
Once `TreeGenerator` operates on plain Python objects with no Tk imports:

- The current Tk UI gets dramatically faster (sections 2 and 4) with no rewrite.
- The solver becomes unit-testable without a Tk preflight — directly relevant
  to the testing rigor you just added, since `conftest.py` currently has to
  skip Tk-dependent tests.
- The UI becomes genuinely replaceable, because the thing that made it
  irreplaceable was that the solver lived inside it.
- You can then prototype a React front end against the *same* core, side by
  side, and compare honestly — with a working fallback the entire time.

That sequencing gets you the performance win immediately and preserves the
option on React, instead of betting the app on a rewrite up front. Given this
is a codebase you have personally invested years in and explicitly want to
protect, optionality is worth more than a big-bang migration.

---

## 7. Recommended sequencing

Ordered by (value / risk). Each phase is independently shippable and leaves
the app working.

**Phase 0 — Mark the fallback.** You already keep `*-fallback` tags
(`v2.0.0-fallback`, `v2.0-fallback-2026-03-18`); latest release is `v2.1.4`.
Cut `v2.1.4-fallback` before any refactor lands. *(Not done — awaiting your
go-ahead, see below.)*

**Phase 1 — Extract the domain model.** A `PairingNode` dataclass with real
fields (`base`, `cumulative`, `confidence`, `resistance`, `depth`, `children`).
`TreeGenerator` computes against it and never touches Tk. A thin adapter
projects the model into the widget. This is the keystone; everything else
depends on it. Expected: the 69x, and depth becomes O(1).

**Phase 2 — Virtualize rendering.** Materialize visible rows only, populate
children on expand. Expected: kills the 4,135 ms redraw and the 4.2 s freeze.

**Phase 3 — Replace the memo key with canonical state, add alpha-beta.**
Expected: the 39x, exact same answers. Cheap once Phase 1 exists.

**Phase 4 — Retire or fix v1 cumulative.** Resolve the max/min inconsistency in
section 3 so no shipped sort mode is systematically optimistic.

**Phase 5 — Decision-sensitivity indicator + guaranteed floor.** The new
user-facing capability from section 5. Small code, high perceived polish.

**Phase 6 — Split `ui_manager_v2`.** Only after 1-3. Splitting a god class is
much safer once the solver is no longer entangled with it. Carve along the
responsibility seams already visible in the method prefixes.

**Phase 7 — (Optional) Evaluate React against the extracted core.** With a
working fallback and a UI-independent domain layer, this becomes a bounded
experiment rather than a bet.

---

## Appendix — reproducing these numbers

Scripts live in the session artifacts directory (not committed):

- `bench_tree.py` — node counts, depth histogram, transposition redundancy
- `bench_tk_vs_model.py` — Tk-as-datastore vs plain Python, same access patterns
- `poc_minimax.py` — exact solver; asserts all variants agree before reporting
- `poc_sensitivity.py` — decision-value across rating structures

All are standalone and touch no production code.
