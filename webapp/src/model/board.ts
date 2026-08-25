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
  return { ...board, fractions, updatedAt: Date.now() };
}

/** True once the board carries information beyond the all-even default. */
export function isRated(board: Board): boolean {
  return board.fractions.some((row) => row.some((f) => Math.abs(f - 0.5) > 1e-9));
}

const KEY = "qtr.boards.v1";

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

function isValidBoard(b: unknown): b is Board {
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
