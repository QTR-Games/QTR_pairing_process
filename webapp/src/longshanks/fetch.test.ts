// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";
import { fetchRoster, panelUrl, parseEventId } from "./fetch";

describe("parseEventId", () => {
  it("accepts a bare id", () => {
    expect(parseEventId("33997")).toBe("33997");
    expect(parseEventId("  33997  ")).toBe("33997");
  });

  it("pulls the id out of a full event URL", () => {
    expect(parseEventId("https://longshanks.org/event/33997/")).toBe("33997");
    expect(parseEventId("longshanks.org/event/33997")).toBe("33997");
    expect(parseEventId("http://longshanks.org/event/33997/standings")).toBe("33997");
  });

  it("rejects anything that is not an event reference", () => {
    expect(parseEventId("")).toBeNull();
    expect(parseEventId("longshanks.org")).toBeNull();
    expect(parseEventId("https://longshanks.org/player/24679/")).toBeNull();
    expect(parseEventId("not a url")).toBeNull();
  });
});

describe("panelUrl", () => {
  it("builds the standings AJAX url for each section", () => {
    expect(panelUrl("33997", "team")).toBe(
      "https://longshanks.org/events/detail/panel_standings.php?event=33997&section=team",
    );
    expect(panelUrl("33997", "player")).toBe(
      "https://longshanks.org/events/detail/panel_standings.php?event=33997&section=player",
    );
  });
});

const TEAM = `<div class="player" id="player_1"><div class="name team"><a class='player_link' onclick='pop_team(1);'>Alpha</a><div class="team_members"><a class='player_link' onclick='pop_user(10,33997);'>Ann</a></div></div></div>`;
const PLAYER = `<div class="player accordion 10"><div class="factions"><div class="logo subfaction" title="Caine - Gravediggers Leader"></div> vs <div class="logo subfaction" title="Lylyth - Shadowflame Shard Leader"></div></div></div>`;

describe("fetchRoster", () => {
  it("fetches both panels for the resolved id and joins them", async () => {
    const fetcher = vi.fn(async (url: string) =>
      url.includes("section=team") ? TEAM : PLAYER,
    );
    const roster = await fetchRoster("https://longshanks.org/event/33997/", fetcher);

    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(fetcher).toHaveBeenCalledWith(panelUrl("33997", "team"));
    expect(fetcher).toHaveBeenCalledWith(panelUrl("33997", "player"));
    expect(roster.eventId).toBe("33997");
    expect(roster.teams[0].name).toBe("Alpha");
    expect(roster.teams[0].members[0]).toEqual({
      userId: "10",
      name: "Ann",
      lists: [{ leader: "Caine", army: "Gravediggers" }],
    });
  });

  it("fails before any fetch when the input is not an event", async () => {
    const fetcher = vi.fn(async () => "");
    await expect(fetchRoster("nonsense", fetcher)).rejects.toThrow(/Longshanks event id/);
    expect(fetcher).not.toHaveBeenCalled();
  });
});
