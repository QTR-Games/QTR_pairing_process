import { useMemo } from "react";
import type { Matrix } from "../../engine/boardAnalysis";
import { reachReport } from "../../engine/reach";
import { protocolFloor } from "../../engine/protocol";
import type { Board } from "../../model/board";
import type { Scale } from "../../model/scale";
import { ratingColor, toFraction } from "../../model/scale";

interface Props {
  board: Board;
  scale: Scale;
  matrix: Matrix;
  onHighlight?: (cells: Set<string>) => void;
}

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

/**
 * Reach: the gap between what the grid promises and what the protocol delivers.
 *
 * This is the panel that replaces `canPin` / `isPinned` / `pinReport`. Those
 * three are fully built and tested and wired to nothing, and the brief that
 * produced this screen assumed the reason was space. It is not. Measured at the
 * midpoint threshold across all 31 saved boards they answer:
 *
 *     offensive pins achievable : 154 / 155
 *     defensive pins suffered   :   0 / 155
 *
 * A panel reporting "yes" and "no" that reliably is decoration, and it would
 * have been decoration at any screen size. What was missing was the threshold,
 * not the pixels -- so this asks for the *highest* threshold that still holds
 * (see engine/reach.ts) and the answer stops being a constant.
 *
 * Both columns are worth reading for the same reason: they disagree with the
 * obvious reading of the grid often enough to change a decision.
 *
 *     forced ceiling below the column best : 25 / 155 (16%)
 *     forced floor above the row worst     : 64 / 155 (41%)
 *
 * The second number is the more useful of the two and the one nothing in the
 * app has ever said. Two times in five, your player's worst cell is a matchup
 * the protocol will not actually let them be dragged into, and the instinct to
 * protect them from it is spending a nomination on nothing.
 */
export function ReachPanel({ board, scale, matrix, onHighlight }: Props) {
  const report = useMemo(() => {
    const base = protocolFloor(matrix, board.ourTeamFirst).value;
    return reachReport(matrix, base, board.ourTeamFirst);
  }, [matrix, board.ourTeamFirst]);

  const overstated = report.ceilings.filter((c) => c.overstated).length;
  const shielded = report.floors.filter((f) => f.protectedByProtocol).length;

  return (
    <section className="panel reach">
      <h2>Reach</h2>
      <p className="hint">
        What the protocol lets either side actually force, against what the grid
        appears to offer. Hover a row to light the cells up on the sheet.
      </p>

      <h3 className="panel-sub">Best we can force on each of theirs</h3>
      <table className="reach-table">
        <thead>
          <tr>
            <th>Their player</th>
            <th>Forced</th>
            <th>Grid</th>
            <th>Using</th>
          </tr>
        </thead>
        <tbody>
          {report.ceilings.map((c) => (
            <tr
              key={c.theirs}
              className={c.overstated ? "gap" : ""}
              onMouseEnter={() =>
                onHighlight?.(new Set(c.via.map((i) => `${i}-${c.theirs}`)))
              }
              onMouseLeave={() => onHighlight?.(new Set())}
            >
              <th scope="row">{board.theirPlayers[c.theirs] || `Their ${c.theirs + 1}`}</th>
              <td>
                <span
                  className="pip"
                  style={{
                    background:
                      c.level === null ? "var(--line)" : ratingColor(toFraction(c.level, scale)),
                  }}
                >
                  {c.level === null ? "--" : fmt(c.level)}
                </span>
              </td>
              <td className={c.overstated ? "muted strike" : "muted"}>{fmt(c.columnBest)}</td>
              <td className="via">
                {c.via.length === 0
                  ? "--"
                  : c.via.map((i) => board.ourPlayers[i] || `P${i + 1}`).join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hint">
        {overstated === 0
          ? "Every column delivers its best cell here -- the grid reads true."
          : `${overstated} of ${report.ceilings.length} columns read better than they play. ` +
            "The struck-through number is a matchup you cannot actually insist on."}
      </p>

      <h3 className="panel-sub">Worst they can force on each of ours</h3>
      <table className="reach-table">
        <thead>
          <tr>
            <th>Our player</th>
            <th>Exposed</th>
            <th>Grid</th>
            <th>Via</th>
          </tr>
        </thead>
        <tbody>
          {report.floors.map((f) => (
            <tr
              key={f.ours}
              className={f.protectedByProtocol ? "shield" : ""}
              onMouseEnter={() => onHighlight?.(new Set(f.via.map((j) => `${f.ours}-${j}`)))}
              onMouseLeave={() => onHighlight?.(new Set())}
            >
              <th scope="row">{board.ourPlayers[f.ours] || `Our ${f.ours + 1}`}</th>
              <td>
                <span
                  className="pip"
                  style={{ background: ratingColor(toFraction(f.level, scale)) }}
                >
                  {fmt(f.level)}
                </span>
              </td>
              <td className={f.protectedByProtocol ? "muted strike" : "muted"}>
                {fmt(f.rowWorst)}
              </td>
              <td className="via">
                {f.via.map((j) => board.theirPlayers[j] || `T${j + 1}`).join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hint">
        {shielded === 0
          ? "Every player can be dragged into their own worst matchup here."
          : `${shielded} of ${report.floors.length} of your players cannot be dragged into their ` +
            "worst cell at all. Spending a nomination to protect them from it buys nothing."}
      </p>
    </section>
  );
}
