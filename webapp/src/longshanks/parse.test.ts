// @vitest-environment jsdom
/**
 * Parser tests built from the real event-33997 markup.
 *
 * The fixtures below are trimmed copies of the actual Longshanks panels (class
 * names, `pop_team`/`pop_user` handlers, the "vs" ordering inside `.factions`,
 * even the stray double space in "Scyrafael  - House Kallyss"), so a change in
 * how the site nests these will surface here rather than on event morning.
 */
import { describe, expect, it } from "vitest";
import {
  parsePlayerLists,
  parseRoster,
  parseSubfactionTitle,
  parseTeamPanel,
} from "./parse";

const TEAM_HTML = `
<div class="player" id="player_9889">
  <div class="rank"><div>1</div></div>
  <div class="data">
    <div class="name team split">
      <div><span class='player_disp team'><a class='player_link' onclick='pop_team(9889);'>F*ck Mammoth</a></span></div>
      <div class="team_members">
        <span class='player_disp'><a class='player_link' onclick='pop_user(8784,33997);'>Brad <span class='nickname'>The Iron Lip</span> Park</a>&nbsp;<span class='id_number'>#8784</span></span><br/>
        <span class='player_disp'><a class='player_link' onclick='pop_user(24679,33997);'>Jake VanMeter</a>&nbsp;<span class='id_number'>#24679</span></span><br/>
      </div>
    </div>
  </div>
</div>
<div class="player" id="player_9952">
  <div class="data">
    <div class="name team split">
      <div><span class='player_disp team'><a class='player_link' onclick='pop_team(9952);'>Team Two</a></span></div>
      <div class="team_members">
        <span class='player_disp'><a class='player_link' onclick='pop_user(133,33997);'>Dan <span class='nickname'>Golden Lion</span> Riker</a>&nbsp;<span class='id_number'>#133</span></span><br/>
      </div>
    </div>
  </div>
</div>
`;

const PLAYER_HTML = `
<div class="player">
  <div class="rank" onclick="load_accordion(24679);"></div>
  <div class="data">
    <div class="name split"><div><span class='player_disp'><a class='player_link' onclick='pop_user(24679,33997);'>Jake VanMeter</a></span></div></div>
    <div class="factions"><div class="award_frame leader"><div class='logobox'><img class="logo award" title="Shadowflame Shard" /></div></div></div>
  </div>
</div>
<div class="player accordion 24679">
  <div class="rank opponent">R1</div>
  <div class="data">
    <div class='name'><span class='player_disp'><a class='player_link' onclick='pop_user(133,33997);'>Dan Riker</a></span></div>
    <div class="factions"><div class='logobox'><div class="logo subfaction" title="Lylyth - Shadowflame Shard Leader">Ly</div></div>&nbsp;vs&nbsp;<div class='logobox'><div class="logo subfaction" title="Morozov - Old Umbrey Leader">Mo</div></div></div>
  </div>
</div>
<div class="player accordion 24679">
  <div class="rank opponent">R2</div>
  <div class="data">
    <div class='name'><span class='player_disp'><a class='player_link' onclick='pop_user(42300,33997);'>Derek Sennstrom</a></span></div>
    <div class="factions"><div class='logobox'><div class="logo subfaction" title="Lylyth - Shadowflame Shard Leader">Ly</div></div>&nbsp;vs&nbsp;<div class='logobox'><div class="logo subfaction" title="Scyrafael  - House Kallyss Leader">Sc</div></div></div>
  </div>
</div>
<div class="player accordion 133">
  <div class="rank opponent">R1</div>
  <div class="data">
    <div class='name'><span class='player_disp'><a class='player_link' onclick='pop_user(24679,33997);'>Jake VanMeter</a></span></div>
    <div class="factions"><div class='logobox'><div class="logo subfaction" title="Morozov - Old Umbrey Leader">Mo</div></div>&nbsp;vs&nbsp;<div class='logobox'><div class="logo subfaction" title="Lylyth - Shadowflame Shard Leader">Ly</div></div></div>
  </div>
</div>
`;

describe("parseSubfactionTitle", () => {
  it("splits leader and army and drops the trailing role word", () => {
    expect(parseSubfactionTitle("Lylyth - Shadowflame Shard Leader")).toEqual({
      leader: "Lylyth",
      army: "Shadowflame Shard",
    });
  });

  it("tolerates the stray double space Longshanks emits", () => {
    expect(parseSubfactionTitle("Scyrafael  - House Kallyss Leader")).toEqual({
      leader: "Scyrafael",
      army: "House Kallyss",
    });
  });

  it("keeps the army when no leader is named", () => {
    expect(parseSubfactionTitle("House Kallyss Leader")).toEqual({ army: "House Kallyss" });
  });

  it("returns null for nothing usable", () => {
    expect(parseSubfactionTitle(null)).toBeNull();
    expect(parseSubfactionTitle("")).toBeNull();
    expect(parseSubfactionTitle("   ")).toBeNull();
  });
});

describe("parseTeamPanel", () => {
  const teams = parseTeamPanel(TEAM_HTML);

  it("finds every team with its id and name", () => {
    expect(teams.map((t) => [t.teamId, t.name])).toEqual([
      ["9889", "F*ck Mammoth"],
      ["9952", "Team Two"],
    ]);
  });

  it("reads members with user ids, flattening nicknames into the name", () => {
    expect(teams[0].members).toEqual([
      { userId: "8784", name: "Brad The Iron Lip Park", lists: [] },
      { userId: "24679", name: "Jake VanMeter", lists: [] },
    ]);
  });

  it("does not mistake the team name link for a member", () => {
    expect(teams[1].members).toEqual([
      { userId: "133", name: "Dan Golden Lion Riker", lists: [] },
    ]);
  });
});

describe("parsePlayerLists", () => {
  const lists = parsePlayerLists(PLAYER_HTML);

  it("keys lists by the accordion owner, not the opponent named in the row", () => {
    expect([...lists.keys()].sort()).toEqual(["133", "24679"]);
  });

  it("takes the owner's own army (first, before 'vs') and dedupes across rounds", () => {
    expect(lists.get("24679")).toEqual([{ leader: "Lylyth", army: "Shadowflame Shard" }]);
  });

  it("reads a second player's own list from their own rows", () => {
    expect(lists.get("133")).toEqual([{ leader: "Morozov", army: "Old Umbrey" }]);
  });

  it("ignores the standings row that has no accordion class", () => {
    // The Shadowflame Shard award logo on Jake's standings row must not become
    // a phantom list keyed to some other id.
    expect(lists.size).toBe(2);
  });
});

describe("parseRoster", () => {
  const roster = parseRoster(TEAM_HTML, PLAYER_HTML, "33997", "Grudge Match");

  it("carries the event id and name through", () => {
    expect(roster.eventId).toBe("33997");
    expect(roster.eventName).toBe("Grudge Match");
  });

  it("joins each member's lists on user id", () => {
    const jake = roster.teams[0].members.find((m) => m.userId === "24679");
    expect(jake?.lists).toEqual([{ leader: "Lylyth", army: "Shadowflame Shard" }]);
  });

  it("leaves members who never played with an empty list rather than a guess", () => {
    const brad = roster.teams[0].members.find((m) => m.userId === "8784");
    expect(brad?.lists).toEqual([]);
  });
});
