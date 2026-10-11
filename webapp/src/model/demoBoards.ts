/**
 * Three boards that show what the app is for, without typing anything in.
 *
 * The problem this solves is the first thirty seconds. Every claim the app
 * makes -- that it solves the real nomination sequence, that it reports what
 * you can hold rather than what you would like, that it says so when a board
 * has no shape -- only becomes visible on a *rated* board. A blank grid
 * demonstrates none of it, and rating twenty-five cells before you have any
 * reason to trust the thing is a fair amount to ask of someone who has just
 * opened it.
 *
 * So these three are already rated, and each one is here because it makes a
 * different point. They are kept honest by `demoBoards.test.ts`, which asserts
 * the property each board is supposed to show still holds -- if the engine ever
 * stops producing the behaviour a board was chosen for, that test fails rather
 * than the demo quietly becoming a lie.
 *
 * PROVENANCE. The ratings are real: they are three of the thirty-one boards in
 * `engine/__fixtures__/wtc2024Boards.json`, captured from WTC 2024 and already
 * anonymised there (`Opponent 01`, `List 39`). The names below are invented, so
 * nothing here attributes an opinion about a matchup to a real player. Real
 * numbers, fictional names.
 */

import { deleteBoard, saveBoards, type Board } from "./board";
import { scaleById, toFraction } from "./scale";

/** The scale the captured ratings were recorded on. */
const DEMO_SCALE = "five";

export interface DemoBoard {
  /** Stable id for the definition, so a reload replaces rather than duplicates. */
  key: string;
  /** Shown in the picker. */
  title: string;
  /** One line on what this board is here to demonstrate. */
  teaches: string;
  board: Board;
}

interface Spec {
  key: string;
  title: string;
  teaches: string;
  opponent: string;
  ourPlayers: string[];
  theirPlayers: string[];
  /** Row-major, our player by theirs, on the 1-5 scale. */
  ratings: number[][];
}

/** Our side is the same five across all three, because it is meant to read as one team. */
const OURS = ["Ayla", "Brenn", "Cato", "Devi", "Esker"];

const SPECS: Spec[] = [
  {
    key: "demo-too-close",
    title: "Too close to call",
    teaches:
      "Almost every matchup on this board is even. The round is a coin flip, and the app says so instead of inventing a recommendation.",
    opponent: "Harbour Watch",
    ourPlayers: OURS,
    theirPlayers: ["Isolde", "Jarek", "Kesh", "Lior", "Mira"],
    // WTC 2024, Opponent 01. Nineteen of the twenty-five cells are the same
    // value. Typical outcome 0.493 with a standard error of 0.005, so the
    // estimate cannot tell this board from a coin flip and the verdict declines.
    ratings: [
      [3, 3, 2, 3, 3],
      [3, 3, 2, 2, 2],
      [3, 3, 3, 3, 3],
      [2, 3, 3, 3, 3],
      [3, 3, 1, 3, 3],
    ],
  },
  {
    key: "demo-false-tie",
    title: "The false tie",
    teaches:
      "Several opening pairings look identical if you only read the best case. Four guaranteed points separate the best of them from the worst.",
    opponent: "Granite Hollow",
    ourPlayers: OURS,
    theirPlayers: ["Nadia", "Oren", "Pia", "Quill", "Rhys"],
    // WTC 2024, Opponent 12. Among the pairings tied on reachable ceiling, the
    // guaranteed floor spans 4.0 points -- the largest hidden floor cost in the
    // captured set, and invisible to any tool that ranks on one number.
    ratings: [
      [2, 2, 3, 3, 3],
      [2, 3, 2, 3, 3],
      [3, 3, 3, 1, 3],
      [3, 3, 4, 1, 3],
      [1, 3, 4, 3, 3],
    ],
  },
  {
    key: "demo-optimistic-matching",
    title: "The optimistic matching",
    teaches:
      "The best matching on paper scores 18 and wins comfortably. Against an opponent who is also trying, you can only hold 15 -- dead even.",
    opponent: "Sablewood Pact",
    ourPlayers: OURS,
    theirPlayers: ["Soren", "Tove", "Ulla", "Vex", "Wren"],
    // WTC 2024, Opponent 24. Best assignment 18, worst 10, protocol floor 15
    // receiving and 14 opening. The three-point drop from 18 is the part a
    // permutation-only view cannot see: you do not get to choose the matching.
    ratings: [
      [2, 4, 2, 3, 3],
      [3, 2, 2, 4, 3],
      [3, 2, 3, 3, 3],
      [4, 3, 3, 3, 2],
      [4, 3, 1, 3, 3],
    ],
  },
];

function toBoard(spec: Spec, stamp: number, i: number): Board {
  const scale = scaleById(DEMO_SCALE);
  return {
    // Deterministic and namespaced, so loading the demo twice replaces the same
    // three boards rather than stacking up copies of them.
    id: spec.key,
    opponent: spec.opponent,
    ourPlayers: [...spec.ourPlayers],
    theirPlayers: [...spec.theirPlayers],
    fractions: spec.ratings.map((row) => row.map((v) => toFraction(v, scale))),
    scaleId: DEMO_SCALE,
    ourTeamFirst: true,
    // Decrement so the first spec keeps the highest stamp and therefore sorts
    // to the top of the saved list, matching what `saveBoards` does on import.
    updatedAt: stamp - i,
    // These are rated boards. Without this they read as untouched, which gates
    // autosave and leaves the verdict with nothing to say.
    touched: true,
  };
}

/** The demo set, freshly built. */
export function demoBoards(): DemoBoard[] {
  const stamp = Date.now();
  return SPECS.map((spec, i) => ({
    key: spec.key,
    title: spec.title,
    teaches: spec.teaches,
    board: toBoard(spec, stamp, i),
  }));
}

/** Just the boards, in the order they should land in the saved list. */
export const demoBoardList = (): Board[] => demoBoards().map((d) => d.board);

/** True when a saved board came from the demo set, so the UI can offer to clear it. */
export const isDemoBoard = (board: Board): boolean =>
  SPECS.some((s) => s.key === board.id);

export const DEMO_IDS: readonly string[] = SPECS.map((s) => s.key);

/**
 * Put the demo set into saved boards, and hand back the new list.
 *
 * Deletes first, then writes the three in one go. The delete is what makes this
 * safe to press twice: the demo ids are fixed, so a second load refreshes the
 * same three boards instead of stacking duplicate copies. That matters because
 * this is the button someone presses when they are not yet sure what it does.
 *
 * `saveBoards` rather than repeated `saveBoard` calls, because it stamps
 * `updatedAt` as `stamp - i` and so pins the on-screen order to the order these
 * are defined in. Saving them one at a time instead leaves the order at the
 * mercy of whether the clock happened to tick between two writes, which is a
 * coin toss on a fast machine and reverses the list when it lands wrong.
 */
export function installDemoBoards(): Board[] {
  for (const id of DEMO_IDS) deleteBoard(id);
  return saveBoards(demoBoardList());
}
