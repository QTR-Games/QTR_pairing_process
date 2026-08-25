import { useMemo, useState } from "react";
import type { Matrix } from "../../engine/boardAnalysis";
import type { LiveState } from "../../engine/live";
import { moveOptions, newRound, pickOptions } from "../../engine/live";
import { solveCache } from "../../engine/protocol";
import type { Board } from "../../model/board";

interface Props {
  board: Board;
  matrix: Matrix;
  /** The line between winning the round and not, for colouring outcomes. */
  tau: number;
  onHighlight?: (cells: Set<string>) => void;
}

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(2));

/**
 * The first three plies of the nomination protocol, laid out as a tree.
 *
 * The engine has always searched this tree exactly -- `solveProtocol` walks the
 * real turn-taking rules, not a matching heuristic -- and the phone shows you
 * only where the search came out. That is the right call on a phone: the
 * opening ply alone is five branches, the reply ply is ten more under each of
 * them, and fifty rows of numbers on a 390px screen is not a decision aid.
 *
 * On a laptop the same fifty rows fit in three columns side by side, which is
 * the difference between being told an answer and being shown why it is the
 * answer. Every value is a *final round total* under perfect play from that
 * point, so the three columns are directly comparable to each other and to the
 * threshold -- there is no arithmetic to do while reading across.
 *
 * Three plies rather than the whole tree because the fourth is where the
 * branching stops being legible, and because the round is re-solved from the
 * live state after every real commitment anyway.
 */
export function ProtocolTree({ board, matrix, tau, onHighlight }: Props) {
  const n = board.ourPlayers.length;
  const root = useMemo(() => newRound(n, board.ourTeamFirst), [n, board.ourTeamFirst]);

  // One search for the whole tree. `offers` explores a child of the state
  // `openers` just valued, and `picks` a child of that, so nearly everything
  // the second and third calls need is already in the cache.
  const cache = useMemo(() => solveCache(matrix), [matrix]);

  const openers = useMemo(() => moveOptions(matrix, root, cache), [matrix, root, cache]);
  const weOpen = board.ourTeamFirst;

  const [opener, setOpener] = useState<number | null>(null);
  const chosenOpener = opener ?? bestOpener(openers, weOpen);

  const afterOpen: LiveState | null = useMemo(() => {
    if (chosenOpener === null) return null;
    return {
      ourPool: weOpen ? root.ourPool & ~(1 << chosenOpener) : root.ourPool,
      theirPool: weOpen ? root.theirPool : root.theirPool & ~(1 << chosenOpener),
      attacker: chosenOpener,
      attackerSide: weOpen ? "our" : "their",
      banked: 0,
      committed: [],
    };
  }, [chosenOpener, root, weOpen]);

  const offers = useMemo(
    () => (afterOpen ? moveOptions(matrix, afterOpen, cache) : []),
    [matrix, afterOpen, cache],
  );

  // The offering side is whoever did not open, and they are minimising our
  // total, so their best offer is the one with zero regret from their side.
  const theirBestOffer = offers.find((o) => o.regret === 0) ?? offers[0];
  const [offerKey, setOfferKey] = useState<string | null>(null);
  const chosenOffer =
    offers.find((o) => o.pair && key(o.pair) === offerKey) ?? theirBestOffer;

  const picks = useMemo(
    () =>
      afterOpen && chosenOffer?.pair
        ? pickOptions(matrix, afterOpen, chosenOffer.pair, cache)
        : [],
    [matrix, afterOpen, chosenOffer, cache],
  );

  const nameOpener = (i: number) =>
    (weOpen ? board.ourPlayers[i] : board.theirPlayers[i]) || `P${i + 1}`;
  // The side that did not open is the side that offers a pair.
  const nameOffered = (i: number) =>
    (weOpen ? board.theirPlayers[i] : board.ourPlayers[i]) || `P${i + 1}`;

  const cellFor = (offered: number) =>
    weOpen ? `${chosenOpener}-${offered}` : `${offered}-${chosenOpener}`;

  return (
    <section className="panel tree">
      <h2>Protocol tree</h2>
      <p className="hint">
        Every value is the final round total under perfect play from that point.
        The threshold is {fmt(tau)}.
      </p>

      <div className="tree-cols">
        <div className="tree-col">
          <h3 className="panel-sub">{weOpen ? "You put up" : "They put up"}</h3>
          {openers.map((o) => {
            const who = (weOpen ? o.ours : o.theirs) ?? 0;
            return (
              <button
                key={who}
                type="button"
                className={
                  "tree-node" +
                  (who === chosenOpener ? " on" : "") +
                  (o.regret === 0 ? " best" : "")
                }
                onClick={() => {
                  setOpener(who);
                  setOfferKey(null);
                }}
              >
                <span className="tree-name">{nameOpener(who)}</span>
                <span className={"tree-val " + band(o.value, tau)}>{fmt(o.value)}</span>
              </button>
            );
          })}
        </div>

        <div className="tree-col">
          <h3 className="panel-sub">{weOpen ? "They offer" : "You offer"}</h3>
          <div className="tree-scroll">
            {offers.map((o) => {
              if (!o.pair) return null;
              const k = key(o.pair);
              return (
                <button
                  key={k}
                  type="button"
                  className={
                    "tree-node" +
                    (chosenOffer?.pair && k === key(chosenOffer.pair) ? " on" : "") +
                    (o.regret === 0 ? " best" : "")
                  }
                  onClick={() => setOfferKey(k)}
                  onMouseEnter={() =>
                    onHighlight?.(new Set(o.pair!.map((p) => cellFor(p))))
                  }
                  onMouseLeave={() => onHighlight?.(new Set())}
                >
                  <span className="tree-name">
                    {nameOffered(o.pair[0])} / {nameOffered(o.pair[1])}
                  </span>
                  <span className={"tree-val " + band(o.value, tau)}>{fmt(o.value)}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="tree-col">
          <h3 className="panel-sub">{weOpen ? "You take" : "They take"}</h3>
          {picks.map((p) => (
            <button
              key={p.player}
              type="button"
              className={"tree-node" + (p.best ? " best on" : "")}
              onMouseEnter={() => onHighlight?.(new Set([cellFor(p.player)]))}
              onMouseLeave={() => onHighlight?.(new Set())}
            >
              <span className="tree-name">{nameOffered(p.player)}</span>
              <span className={"tree-val " + band(p.value, tau)}>{fmt(p.value)}</span>
            </button>
          ))}
          {picks.length > 0 && (
            <p className="hint">
              Then the declined player carries the initiative into the next
              nomination, and the search restarts from there.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

const key = (pair: readonly [number, number]) => `${pair[0]}-${pair[1]}`;

/** The opener the side to move should choose, given who is moving. */
function bestOpener(
  options: { ours?: number; theirs?: number; regret: number }[],
  weOpen: boolean,
): number | null {
  const best = options.find((o) => o.regret === 0) ?? options[0];
  if (!best) return null;
  return (weOpen ? best.ours : best.theirs) ?? null;
}

/** Colour by which side of the threshold the outcome lands on. */
function band(value: number, tau: number): string {
  if (value > tau + 1e-9) return "win";
  if (value < tau - 1e-9) return "loss";
  return "draw";
}
