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
  parseListPanel,
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

/**
 * A team block carrying the `.factions` strip, as event 36052 serves it: one
 * logo per member, in member order, titled with the army they registered.
 */
const TEAM_WITH_FACTIONS = `
<div class="player" id="player_10994">
  <div class="data">
    <div class="name team split">
      <div><a class='player_link' onclick='pop_team(10994);'>You're So Fane</a></div>
      <div class="team_members">
        <a class='player_link' onclick='pop_user(25112,36052);'>Rick Coe</a><br/>
        <a class='player_link' onclick='pop_user(10566,36052);'>Akers</a><br/>
      </div>
    </div>
    <div class="factions">
      <div class='logobox'><img class="logo" src="/systems/warmachine/factions/kithguard.png" title="Kithguard" /></div><div class='logobox'><img class="logo" src="/systems/warmachine/factions/cyriss.png" title="Convergence of Cyriss" /></div>
    </div>
  </div>
</div>
`;

describe("parseTeamPanel factions", () => {
  it("gives each member the army shown against them, by position", () => {
    const [team] = parseTeamPanel(TEAM_WITH_FACTIONS);
    expect(team.members.map((m) => [m.name, m.faction])).toEqual([
      ["Rick Coe", "Kithguard"],
      ["Akers", "Convergence of Cyriss"],
    ]);
  });

  it("takes no faction at all when the two lists cannot be aligned", () => {
    // One logo, two members: which member it belongs to is unknowable, and a
    // faction on the wrong player is worse than none.
    const html = TEAM_WITH_FACTIONS.replace(
      /<div class='logobox'><img class="logo" src="\/systems\/warmachine\/factions\/cyriss.png" title="Convergence of Cyriss" \/><\/div>/,
      "",
    );
    const [team] = parseTeamPanel(html);
    expect(team.members.every((m) => m.faction === undefined)).toBe(true);
  });

  it("leaves faction unset when the panel has no factions strip at all", () => {
    expect(parseTeamPanel(TEAM_HTML)[0].members[0].faction).toBeUndefined();
  });
});

/**
 * The `tab=list` popup, in the shape Longshanks moved to when it replaced the
 * single free-text army-list box with named list objects. Bodies are trimmed
 * from real event-36052 registrations, `<br />` separators and all.
 */
const LIST_HTML = `
<div class="edit" id="edit_player_list" style='display:block;'>
  <div class="columns">
    <div class="column center">
      <table class='ledger toggles list'><tr><th class='center'>Abe!</th></tr><tr><td>Southern Kriels - Kithguard<br />Grand Melee - 100 pts<br /><br />PC CARD<br /><br />Trapdoor<br /><br />Major Abraham Stormcraw<br /><br />29 Fortress King<br />12 Vorogger</td></tr></table>
      <div class='game_tabs'><a onclick='copy_list(\`197646\`);'>Copy</a></div>
      <textarea id='list_197646'>Southern Kriels - Kithguard || Major Abraham Stormcraw</textarea>
    </div>
    <div class="column center">
      <table class='ledger toggles list'><tr><th class='center'>Novamourn</th></tr><tr><td>Wroughtmourn<br />Grand Melee - 100 pts<br /><br />PC CARD<br /><br />Trapdoor<br /><br />Fell Captain Mailis Wroughtmourn<br /><br />9 Steelbacks</td></tr></table>
    </div>
  </div>
</div>
`;

describe("parseListPanel", () => {
  it("reads a list object's title and resolves its leader and army", () => {
    expect(parseListPanel(LIST_HTML, "Kithguard")).toEqual([
      {
        name: "Abe!",
        army: "Kithguard",
        leader: "Stormcraw",
        body:
          "Southern Kriels - Kithguard\nGrand Melee - 100 pts\n\nPC CARD\n\nTrapdoor\n\nMajor Abraham Stormcraw\n\n29 Fortress King\n12 Vorogger",
      },
      {
        name: "Novamourn",
        army: "Kithguard",
        leader: "Wroughtmourn",
        body:
          "Wroughtmourn\nGrand Melee - 100 pts\n\nPC CARD\n\nTrapdoor\n\nFell Captain Mailis Wroughtmourn\n\n9 Steelbacks",
      },
    ]);
  });

  it("keeps the <br> line breaks, so the army header is its own line", () => {
    // Without them "Southern Kriels - KithguardGrand Melee" is line one and the
    // declared army no longer resolves.
    expect(parseListPanel(LIST_HTML)[0].army).toBe("Kithguard");
  });

  it("falls back to the hinted army when the list opens with a title instead", () => {
    // "Novamourn" opens with the caster's surname, not "<Faction> - <Army>".
    expect(parseListPanel(LIST_HTML, "Kithguard")[1].army).toBe("Kithguard");
  });

  it("reads the title from the body when the table has no header row", () => {
    /*
      Lists saved without a title render as a bare `td`, and the player's own
      title takes the top line -- pushing "<Faction> - <Army>" down to the
      second. Reading only the first line loses both the title and the army.
    */
    const html = `<div id="edit_player_list"><table class="list"><tr><td>talk shit get crit 3.0<br />Dusk - House Kallyss<br />Grand Melee - 100 pts<br /><br />PC CARD<br /><br />Scyrafael, Nis-Issyr of Desolations<br /><br />14 Eidolon 1</td></tr></table></div>`;
    expect(parseListPanel(html, "House Kallyss")).toEqual([
      {
        name: "talk shit get crit 3.0",
        army: "House Kallyss",
        leader: "Scyrafael",
        body:
          "talk shit get crit 3.0\nDusk - House Kallyss\nGrand Melee - 100 pts\n\nPC CARD\n\nScyrafael, Nis-Issyr of Desolations\n\n14 Eidolon 1",
      },
    ]);
  });

  it("still returns a list whose leader cannot be identified", () => {
    const html = `<div id="edit_player_list"><table class="list"><tr><th class="center">The OP shit</th></tr><tr><td>Made ya look<br />TOTAL POINTS 100/100</td></tr></table></div>`;
    expect(parseListPanel(html, "Convergence of Cyriss")).toEqual([
      {
        name: "The OP shit",
        army: "Convergence of Cyriss",
        body: "Made ya look\nTOTAL POINTS 100/100",
      },
    ]);
  });

  it("ignores a popup with no lists in it", () => {
    expect(parseListPanel(`<div id="edit_player_list"><div class="columns"></div></div>`)).toEqual([]);
    expect(parseListPanel("<div>nothing here</div>")).toEqual([]);
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
