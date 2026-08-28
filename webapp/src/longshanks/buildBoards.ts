/**
 * Turning an imported roster into boards to play against.
 *
 * This is the point of the whole import. The owner picks which team is theirs;
 * every other team in the event becomes a board with the owner's five players
 * down the left and that opponent's five across the top, the grid left neutral so
 * only the pairing itself has to be filled in on the day. The opposing roster
 * detail (faction, lists) is carried on the board as reference, not as anything
 * the engine reads.
 *
 * The builder is strict about one thing and lenient about everything else. Strict:
 * a board is only created for a team that has a full five named players, because a
 * board with a blank opponent slot is worse than no board -- it looks ready when
 * it is not. Lenient: missing factions or lists never block a board, since a
 * pre-event roster routinely lacks them and the names are what matter at pairing
 * time. Teams that fall short are not dropped silently; they come back as
 * `failures` so the UI can show them and offer the list for download, which is
 * exactly the "add the stragglers by hand" path the owner asked for.
 */

import { emptyBoard, TEAM_SIZE, type Board, type OpponentDetail } from "../model/board";
import type { Roster, RosterMember, RosterTeam } from "./types";

/** A team that could not be turned into a board, with enough detail to fix by hand. */
export interface BuildFailure {
  teamId?: string;
  team: string;
  reason: string;
  /** The member names that were found, for the downloadable report. */
  members: string[];
}

export interface BuildResult {
  /** One board per opposing team that imported cleanly. */
  boards: Board[];
  /** Teams skipped because they were not import-ready. */
  failures: BuildFailure[];
}

/** Non-empty, whitespace-tidied member names in roster order. */
function memberNames(team: RosterTeam): string[] {
  return team.members.map((m) => m.name.trim()).filter((n) => n.length > 0);
}

/** Pad or trim a name list to exactly five, filling gaps with a labelled placeholder. */
function toFive(names: string[], placeholder: (i: number) => string): string[] {
  return Array.from({ length: TEAM_SIZE }, (_, i) => names[i] ?? placeholder(i));
}

/** The faction for a member is the army of their first list, when known. */
function factionOf(member: RosterMember): string | undefined {
  return member.lists[0]?.army;
}

function detailFor(member: RosterMember): OpponentDetail {
  const detail: OpponentDetail = { name: member.name.trim() };
  const faction = factionOf(member);
  if (faction) detail.faction = faction;
  if (member.lists.length > 0) detail.lists = member.lists;
  return detail;
}

/**
 * Build one board per opposing team.
 *
 * `myTeamId` names the owner's team; its members become the home side of every
 * board. Every other team is a candidate opponent: it becomes a board when it has
 * a full five named players, and a `failure` otherwise. The owner's own team is
 * never turned into a board to play against itself.
 *
 * Throws only when `myTeamId` is not in the roster -- that is a programming error
 * (the id came from this same roster), not a data problem to report.
 */
export function buildBoards(roster: Roster, myTeamId: string, scaleId = "five"): BuildResult {
  const myTeam = roster.teams.find((t) => t.teamId === myTeamId);
  if (!myTeam) {
    throw new Error(`Team ${myTeamId} is not in this event`);
  }

  const ourPlayers = toFive(memberNames(myTeam), (i) => `Player ${i + 1}`);

  const boards: Board[] = [];
  const failures: BuildFailure[] = [];

  for (const team of roster.teams) {
    if (team.teamId === myTeamId) continue;

    const names = memberNames(team);
    if (names.length !== TEAM_SIZE) {
      failures.push({
        teamId: team.teamId,
        team: team.name,
        reason: `Expected ${TEAM_SIZE} players, found ${names.length}`,
        members: names,
      });
      continue;
    }

    const board = emptyBoard(scaleId);
    board.opponent = team.name;
    board.ourPlayers = [...ourPlayers];
    board.theirPlayers = names;
    board.theirDetails = team.members.map(detailFor);
    board.ourTeamFirst = true;
    boards.push(board);
  }

  return { boards, failures };
}
