import { describe, expect, it } from "vitest";
import { buildBoards } from "./buildBoards";
import type { Roster } from "./types";

function team(teamId: string, name: string, members: [string, string][], lists: Record<string, { army?: string; leader?: string }[]> = {}) {
  return {
    teamId,
    name,
    members: members.map(([userId, mName]) => ({ userId, name: mName, lists: lists[userId] ?? [] })),
  };
}

const five = (prefix: string): [string, string][] =>
  Array.from({ length: 5 }, (_, i) => [`${prefix}${i}`, `${prefix} P${i}`] as [string, string]);

const roster: Roster = {
  eventId: "33997",
  teams: [
    team("1", "Home Team", five("h"), {
      h0: [{ army: "Gravediggers", leader: "Caine" }, { army: "Gravediggers", leader: "Hasker" }],
    }),
    team("2", "Rivals", five("r"), {
      r0: [{ army: "Shadowflame Shard", leader: "Lylyth" }],
    }),
    team("3", "Also Rans", five("a")),
  ],
};

describe("buildBoards", () => {
  it("builds one board per other team, never against itself", () => {
    const { boards } = buildBoards(roster, "1");
    expect(boards).toHaveLength(2);
    expect(boards.map((b) => b.opponent).sort()).toEqual(["Also Rans", "Rivals"]);
  });

  it("puts our team on the left of every board and the opponent on top", () => {
    const { boards } = buildBoards(roster, "1");
    const rivals = boards.find((b) => b.opponent === "Rivals")!;
    expect(rivals.ourPlayers).toEqual(["h P0", "h P1", "h P2", "h P3", "h P4"]);
    expect(rivals.theirPlayers).toEqual(["r P0", "r P1", "r P2", "r P3", "r P4"]);
  });

  it("leaves the grid neutral so only the pairing has to be filled in", () => {
    const { boards } = buildBoards(roster, "1");
    for (const row of boards[0].fractions) {
      for (const cell of row) expect(cell).toBe(0.5);
    }
  });

  it("carries opponent faction and lists as index-aligned detail", () => {
    const { boards } = buildBoards(roster, "1");
    const rivals = boards.find((b) => b.opponent === "Rivals")!;
    expect(rivals.theirDetails?.[0]).toEqual({
      name: "r P0",
      faction: "Shadowflame Shard",
      lists: [{ army: "Shadowflame Shard", leader: "Lylyth" }],
    });
    // A player with no imported list carries just a name, not a fabricated faction.
    expect(rivals.theirDetails?.[1]).toEqual({ name: "r P1" });
  });

  it("gives distinct board ids so both can be saved", () => {
    const { boards } = buildBoards(roster, "1");
    expect(new Set(boards.map((b) => b.id)).size).toBe(boards.length);
  });

  it("reports a short-handed team as a failure instead of a broken board", () => {
    const short: Roster = {
      eventId: "1",
      teams: [
        team("1", "Home", five("h")),
        team("2", "Four Only", [["a", "A"], ["b", "B"], ["c", "C"], ["d", "D"]]),
      ],
    };
    const { boards, failures } = buildBoards(short, "1");
    expect(boards).toHaveLength(0);
    expect(failures).toEqual([
      { teamId: "2", team: "Four Only", reason: "Expected 5 players, found 4", members: ["A", "B", "C", "D"] },
    ]);
  });

  it("throws when the chosen team is not in the event", () => {
    expect(() => buildBoards(roster, "999")).toThrow(/not in this event/);
  });
});
