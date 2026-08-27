/**
 * The board, and where it lives.
 *
 * Everything is kept in localStorage. That is not a shortcut: the app has to
 * work in a convention hall with no signal, standing at a table, and any design
 * that needs a round trip to a server fails exactly when it is needed. Storage
 * is local, the engine runs on the device, and nothing here talks to a network.
 *
 * Ratings are stored as fractions (see `scale.ts`) so a board entered on one
 * scale can be read on another without losing what was meant.
 */

import type { Matrix } from "../engine/boardAnalysis";
import type { LiveState } from "../engine/live";
import { fromFraction, scaleById, toFraction, type Scale } from "./scale";

export const TEAM_SIZE = 5;

export interface Board {
  id: string;
  opponent: string;
  ourPlayers: string[];
  theirPlayers: string[];
  /** Row-major, our player by their player, each 0..1. */
  fractions: number[][];
  scaleId: string;
  ourTeamFirst: boolean;
  updatedAt: number;
  /**
   * Set the first time a rating is written.
   *
   * Optional because boards saved before this field existed do not carry it;
   * `isRated` falls back to inspecting the fractions for those, so nothing in
   * localStorage needs migrating.
   */
  touched?: boolean;
  /**
   * Which of our players the captain has chosen to protect first when two or
   * more are equally exposed -- an index into `ourPlayers`.
   *
   * Optional and nullable: absent or null means "no preference", which is what
   * every board created before this field existed reads as, so nothing in
   * localStorage needs migrating (same pattern as `touched`). It rides backup
   * and restore for free because the whole board is JSON-serialised.
   *
   * This is a recorded decision, not an engine input. It is marked back on the
   * grid and persisted with the board, but it does NOT steer the pairing
   * suggestions -- feeding a protect preference into the live tiebreak is its
   * own piece of work (issue #90), because the only seam that could consume it
   * does not exist yet.
   *
   * Never trust the raw value: a stored index can outlive the exposure that
   * motivated it. Read it through `activeProtectPriority`, which returns null
   * for an index that is out of range or names a player who is no longer
   * exposed, so a stale choice is inert rather than silently marking the wrong
   * player.
   */
  protectPriority?: number | null;
}

const uid = (): string =>
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

export function emptyBoard(scaleId = "five"): Board {
  return {
    id: uid(),
    opponent: "",
    ourPlayers: Array.from({ length: TEAM_SIZE }, (_, i) => `Player ${i + 1}`),
    theirPlayers: Array.from({ length: TEAM_SIZE }, (_, i) => `Opponent ${i + 1}`),
    // Start every matchup at dead even. An unrated board should not look like a
    // board we are losing.
    fractions: Array.from({ length: TEAM_SIZE }, () => Array(TEAM_SIZE).fill(0.5)),
    scaleId,
    ourTeamFirst: true,
    updatedAt: Date.now(),
  };
}

/** The board as the engine sees it, in the units currently on screen. */
export function boardMatrix(board: Board, scale: Scale): Matrix {
  return board.fractions.map((row) => row.map((f) => fromFraction(f, scale)));
}

export function setRating(board: Board, ours: number, theirs: number, value: number, scale: Scale): Board {
  const fractions = board.fractions.map((row) => [...row]);
  fractions[ours][theirs] = toFraction(value, scale);
  return { ...board, fractions, touched: true, updatedAt: Date.now() };
}

/**
 * The captain's protect-first choice, but only when it still describes a real,
 * current decision. Returns the stored index when it is an in-range index into
 * `ourPlayers` AND that player is currently exposed; otherwise null.
 *
 * A board outlives its preference: re-rate it and the player the captain wanted
 * to protect can stop being exposed, or a roster slot can go away. Rather than
 * let a marker silently point at someone the choice no longer applies to, every
 * reader routes through here, so one stale index reads as "no preference"
 * everywhere at once.
 *
 * `exposed` is supplied by the caller -- the protection engine computes it --
 * so this stays a pure model helper with no engine dependency.
 */
export function activeProtectPriority(board: Board, exposed: Iterable<number>): number | null {
  const i = board.protectPriority;
  if (i == null || !Number.isInteger(i) || i < 0 || i >= board.ourPlayers.length) {
    return null;
  }
  for (const o of exposed) if (o === i) return i;
  return null;
}

/**
 * True once the board carries information beyond the all-even default.
 *
 * This gates three real behaviours: whether the board is autosaved, how the
 * screen orders itself, and whether the verdict says anything at all.
 *
 * The fractions alone cannot answer the question. A mid rating maps to exactly
 * 0.5 -- 3 on the 1-5 scale, amber on the stoplight -- which is also the value
 * an untouched board is seeded with. So a board deliberately rated all-even was
 * indistinguishable from one nobody had opened, and being read as untouched it
 * was never saved. Amber-across-the-board is a natural first pass, so that lost
 * real work rather than being a curiosity.
 *
 * `touched` records the act of rating instead of trying to infer it from the
 * result. The fraction check stays as the fallback for boards saved before the
 * flag existed, where it remains the best available signal.
 */
export function isRated(board: Board): boolean {
  if (board.touched) return true;
  return board.fractions.some((row) => row.some((f) => Math.abs(f - 0.5) > 1e-9));
}

/**
 * The storage key. Exported so the backup path cannot drift from the load path.
 *
 * Keeps the `qtr.` prefix on purpose, after the app was renamed to KLIK KLAK.
 * This is the address every saved board already lives at in localStorage.
 * Renaming it for consistency would not move the data -- it would point the app
 * at an empty shelf, and every board on the device would read as gone. The same
 * is true of the live-round and settings keys below.
 */
export const BOARDS_KEY = "qtr.boards.v1";
const KEY = BOARDS_KEY;

export function loadBoards(): Board[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Board[];
    return Array.isArray(parsed) ? parsed.filter(isValidBoard) : [];
  } catch {
    // A corrupt entry must not brick the app on event morning.
    return [];
  }
}

export function isValidBoard(b: unknown): b is Board {
  const x = b as Board;
  return (
    !!x &&
    typeof x.id === "string" &&
    Array.isArray(x.ourPlayers) &&
    Array.isArray(x.theirPlayers) &&
    Array.isArray(x.fractions) &&
    x.fractions.length === TEAM_SIZE &&
    x.fractions.every((r) => Array.isArray(r) && r.length === TEAM_SIZE)
  );
}

export function saveBoard(board: Board): Board[] {
  const boards = loadBoards();
  const idx = boards.findIndex((b) => b.id === board.id);
  const next = { ...board, updatedAt: Date.now() };
  if (idx >= 0) boards[idx] = next;
  else boards.unshift(next);
  boards.sort((a, b) => b.updatedAt - a.updatedAt);
  try {
    localStorage.setItem(KEY, JSON.stringify(boards));
  } catch {
    // Out of quota. The in-memory board still works for this round.
  }
  return boards;
}

export function deleteBoard(id: string): Board[] {
  const boards = loadBoards().filter((b) => b.id !== id);
  try {
    localStorage.setItem(KEY, JSON.stringify(boards));
  } catch {
    /* ignore */
  }
  return boards;
}

export const boardScale = (board: Board): Scale => scaleById(board.scaleId);

/*
 * The round in progress.
 *
 * Boards are the durable thing and have always been saved. The live round was
 * not, and it is the more expensive one to lose: a board can be retyped from
 * the sheet in front of you, but a half-played round is gone the moment the
 * page reloads. On a phone that happens without anyone doing anything wrong --
 * Android reclaims a backgrounded tab, the screen is tapped awake into a fresh
 * load, or a new build takes over. Standing at a table three pairings deep, that
 * is the worst possible time to be handed an empty round.
 *
 * Stored per board id, so returning to a board resumes where it was left and
 * switching boards does not inherit -- or destroy -- someone else's round. The
 * first version of this kept a single slot tagged with a board id, which met the
 * second half of that promise and quietly broke the first: starting a round on a
 * second board evicted the first board's. Two opponents in one day is the normal
 * case at an event, so that had to go.
 */
const LIVE_KEY = "qtr.live.v2";
/** The single-slot layout this replaced. Read once, to migrate, then dropped. */
const LEGACY_LIVE_KEY = "qtr.live.v1";

/**
 * How many boards may hold a round at once. Well above a day's worth of
 * opponents, and low enough that storage cannot grow without bound.
 */
const MAX_LIVE_ROUNDS = 12;

interface StoredLive {
  boardId: string;
  state: LiveState;
  savedAt: number;
}

type LiveMap = Record<string, StoredLive>;

function readLiveMap(): LiveMap {
  try {
    const raw = localStorage.getItem(LIVE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as LiveMap;
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    }
    // Nothing in the new layout. Someone updating mid-event may still have a
    // round in the old one, and that is precisely the round worth rescuing.
    const legacy = localStorage.getItem(LEGACY_LIVE_KEY);
    if (!legacy) return {};
    const one = JSON.parse(legacy) as StoredLive;
    return one && one.boardId ? { [one.boardId]: one } : {};
  } catch {
    // Same rule as boards: a corrupt entry must not brick the app on event
    // morning. Losing the round is bad; losing the app is worse.
    return {};
  }
}

function writeLiveMap(map: LiveMap, keep?: string): void {
  try {
    // Newest first, except that the round being played is never the one to
    // evict -- several saves can land in the same millisecond, and ordering by
    // timestamp alone would then drop by insertion order rather than by age.
    const entries = Object.values(map).sort((a, b) => {
      if (a.boardId === keep) return -1;
      if (b.boardId === keep) return 1;
      return b.savedAt - a.savedAt;
    });
    const kept: LiveMap = {};
    for (const e of entries.slice(0, MAX_LIVE_ROUNDS)) kept[e.boardId] = e;
    localStorage.setItem(LIVE_KEY, JSON.stringify(kept));
    // Only once the new layout has taken, so a failed write cannot strand the
    // round in neither place.
    localStorage.removeItem(LEGACY_LIVE_KEY);
  } catch {
    // Out of quota. The in-memory round still works for this round.
  }
}

export function loadLive(boardId: string): LiveState | null {
  const entry = readLiveMap()[boardId];
  if (!entry) return null;
  return isValidLive(entry.state) ? entry.state : null;
}

export function saveLive(boardId: string, state: LiveState | null): void {
  const map = readLiveMap();
  if (!state) {
    if (!(boardId in map)) return;
    delete map[boardId];
  } else {
    map[boardId] = { boardId, state, savedAt: Date.now() };
  }
  writeLiveMap(map, state ? boardId : undefined);
}

function isValidLive(s: unknown): s is LiveState {
  const x = s as LiveState;
  return (
    !!x &&
    typeof x.ourPool === "number" &&
    typeof x.theirPool === "number" &&
    typeof x.attacker === "number" &&
    (x.attackerSide === "our" || x.attackerSide === "their") &&
    typeof x.banked === "number" &&
    Array.isArray(x.committed) &&
    x.committed.every(
      (c) =>
        !!c &&
        typeof c.ours === "number" &&
        typeof c.theirs === "number" &&
        typeof c.value === "number",
    )
  );
}
