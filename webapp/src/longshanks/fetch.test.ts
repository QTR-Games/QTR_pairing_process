// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { createDesktopHttp } from "../desktop/http";
import { setDesktopHttp } from "../desktop/platform";
import {
  fetchHtml,
  fetchRoster,
  isRetryable,
  listUrl,
  LongshanksHttpError,
  panelUrl,
  parseEventId,
  withRetry,
} from "./fetch";

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

  it("accepts the game subdomain a phone or a public link produces", () => {
    // Copying an event link on a phone yields the warmachine host rather than
    // the bare one the desktop site shows. Same event, same id.
    expect(parseEventId("https://warmachine.longshanks.org/event/36052/")).toBe("36052");
    expect(parseEventId("https://guildball.longshanks.org/event/36052")).toBe("36052");
  });

  it("accepts an event id carried as a query parameter", () => {
    expect(parseEventId("https://longshanks.org/events/detail/?event=36052")).toBe("36052");
  });

  it("rejects anything that is not an event reference", () => {
    expect(parseEventId("")).toBeNull();
    expect(parseEventId("longshanks.org")).toBeNull();
    expect(parseEventId("https://longshanks.org/player/24679/")).toBeNull();
    expect(parseEventId("not a url")).toBeNull();
  });
});

describe("listUrl", () => {
  it("builds the army-list popup url Longshanks' own list icon opens", () => {
    expect(listUrl("36052", "25112")).toBe(
      "https://longshanks.org/admin/players/pop_info.php?player=25112&event=36052&tab=list",
    );
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

/** Panel HTML for whichever section the URL asks for. */
const panelFor = (url: string): string => (url.includes("section=team") ? TEAM : PLAYER);

/** Any real URL; the retry tests care about attempts, not about which panel. */
const URL_TEAM = panelUrl("33997", "team");

/** Retry options that keep the schedule but cost no real time. */
const instant = { sleep: async () => {} };

describe("LongshanksHttpError", () => {
  it("carries the status", () => {
    expect(new LongshanksHttpError(403).status).toBe(403);
  });

  it("explains a 403 as the transient refusal it is, and says it retried", () => {
    const message = new LongshanksHttpError(403).message;
    expect(message).toContain("403");
    expect(message).toMatch(/retried/i);
  });

  it("explains a 404 as a wrong event id, without promising a retry", () => {
    const message = new LongshanksHttpError(404).message;
    expect(message).toContain("404");
    expect(message).not.toMatch(/retried/i);
  });
});

describe("isRetryable", () => {
  it("retries the intermittent refusal and the transient statuses", () => {
    for (const status of [403, 408, 429, 500, 502, 503]) {
      expect(isRetryable(new LongshanksHttpError(status)), `status ${status}`).toBe(true);
    }
  });

  it("does not retry a missing event or another permanent 4xx", () => {
    for (const status of [400, 401, 404, 410]) {
      expect(isRetryable(new LongshanksHttpError(status)), `status ${status}`).toBe(false);
    }
  });

  it("retries a network-level failure, which carries no status at all", () => {
    expect(isRetryable(new TypeError("Failed to fetch"))).toBe(true);
  });
});

describe("withRetry", () => {
  it("returns the first success without sleeping", async () => {
    const sleep = vi.fn(async () => {});
    const fetcher = vi.fn(async () => "ok");

    await expect(withRetry(fetcher, { sleep })(URL_TEAM)).resolves.toBe("ok");
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(sleep).not.toHaveBeenCalled();
  });

  it("retries a 403 and returns the body that eventually arrives", async () => {
    let calls = 0;
    const fetcher = vi.fn(async () => {
      calls += 1;
      if (calls < 3) throw new LongshanksHttpError(403);
      return "late success";
    });

    await expect(withRetry(fetcher, instant)(URL_TEAM)).resolves.toBe("late success");
    expect(fetcher).toHaveBeenCalledTimes(3);
  });

  it("backs off on the configured schedule, in order", async () => {
    const slept: number[] = [];
    const fetcher = vi.fn(async () => {
      throw new LongshanksHttpError(403);
    });

    await expect(
      withRetry(fetcher, {
        delays: [10, 20, 30],
        sleep: async (ms) => {
          slept.push(ms);
        },
      })(URL_TEAM),
    ).rejects.toBeInstanceOf(LongshanksHttpError);

    expect(slept).toEqual([10, 20, 30]);
    expect(fetcher).toHaveBeenCalledTimes(4);
  });

  it("gives up after the schedule is spent and rethrows the last failure", async () => {
    const fetcher = vi.fn(async () => {
      throw new LongshanksHttpError(503);
    });

    await expect(
      withRetry(fetcher, { delays: [1, 1], sleep: async () => {} })(URL_TEAM),
    ).rejects.toThrow(/Longshanks is having trouble/);
    expect(fetcher).toHaveBeenCalledTimes(3);
  });

  it("does not retry a 404 -- a missing event is not going to appear", async () => {
    const sleep = vi.fn(async () => {});
    const fetcher = vi.fn(async () => {
      throw new LongshanksHttpError(404);
    });

    await expect(withRetry(fetcher, { sleep })(URL_TEAM)).rejects.toThrow(/no event with that id/);
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(sleep).not.toHaveBeenCalled();
  });
});

describe("fetchRoster", () => {
  it("fetches both panels for the resolved id and joins them", async () => {
    const fetcher = vi.fn(async (url: string) => panelFor(url));
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

  /*
    The case this feature was built for. Two panels fetched in parallel is two
    independent chances to be refused, so on a bad morning a clean import was
    close to a coin flip. Each panel has to recover on its own.
  */
  it("survives a 403 on one panel and still returns a complete roster", async () => {
    const refused = new Set<string>();
    const fetcher = vi.fn(async (url: string) => {
      if (url.includes("section=team") && !refused.has(url)) {
        refused.add(url);
        throw new LongshanksHttpError(403);
      }
      return panelFor(url);
    });

    const roster = await fetchRoster("33997", fetcher, instant);

    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(roster.teams[0].name).toBe("Alpha");
    expect(roster.teams[0].members[0].lists).toEqual([{ leader: "Caine", army: "Gravediggers" }]);
  });

  it("surfaces the refusal when every attempt is refused", async () => {
    const fetcher = vi.fn(async () => {
      throw new LongshanksHttpError(403);
    });

    await expect(fetchRoster("33997", fetcher, instant)).rejects.toThrow(/refused the request/);
  });
});

/*
  Army lists are the only source of an opponent's leader before the event has
  been played, and they cost a request per player -- so the rules about when
  that request happens, and what a failed one does, are the whole design.
*/
describe("fetchRoster with lists", () => {
  /** Two teams of two, none of whom have played, so nothing is known yet. */
  const PRE_EVENT_TEAM = `
    <div class="player" id="player_1"><div class="name team"><a class='player_link' onclick='pop_team(1);'>Alpha</a>
      <div class="team_members">
        <a class='player_link' onclick='pop_user(10,36052);'>Ann</a>
        <a class='player_link' onclick='pop_user(11,36052);'>Bo</a>
      </div></div>
      <div class="factions">
        <div class='logobox'><img class="logo" title="Kithguard" /></div><div class='logobox'><img class="logo" title="Storm Legion" /></div>
      </div>
    </div>`;

  const listFor = (userId: string): string =>
    userId === "10"
      ? `<div id="edit_player_list"><table class="list"><tr><th class="center">Abe!</th></tr><tr><td>Southern Kriels - Kithguard<br />Major Abraham Stormcraw</td></tr></table></div>`
      : `<div id="edit_player_list"><table class="list"><tr><th class="center">Caine Too</th></tr><tr><td>Cygnar - Storm Legion<br />Major Allister Caine</td></tr></table></div>`;

  const preEventFetcher = () =>
    vi.fn(async (url: string) => {
      const list = /player=(\d+)/.exec(url);
      if (list) return listFor(list[1]);
      return url.includes("section=team") ? PRE_EVENT_TEAM : "";
    });

  it("reads each player's registered lists when the results panels are empty", async () => {
    const roster = await fetchRoster("36052", preEventFetcher(), { withLists: true });

    expect(roster.teams[0].members).toEqual([
      { userId: "10", name: "Ann", faction: "Kithguard", lists: [{ name: "Abe!", army: "Kithguard", leader: "Stormcraw" }] },
      { userId: "11", name: "Bo", faction: "Storm Legion", lists: [{ name: "Caine Too", army: "Storm Legion", leader: "Caine 4" }] },
    ]);
  });

  it("does not fetch lists unless asked, so an ordinary roster stays two requests", async () => {
    const fetcher = preEventFetcher();
    await fetchRoster("36052", fetcher);
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("skips players the results panels already described", async () => {
    // Ann played, so her leader is already known exactly and for free; only Bo
    // is worth a request. This is what makes the cost fall away mid-event.
    const played = `<div class="player accordion 10"><div class="factions"><div class="logo subfaction" title="Craghorn - Kithguard Leader"></div></div></div>`;
    const fetcher = vi.fn(async (url: string) => {
      const list = /player=(\d+)/.exec(url);
      if (list) return listFor(list[1]);
      return url.includes("section=team") ? PRE_EVENT_TEAM : played;
    });

    const roster = await fetchRoster("36052", fetcher, { withLists: true });

    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(fetcher).not.toHaveBeenCalledWith(listUrl("36052", "10"));
    expect(roster.teams[0].members[0].lists).toEqual([{ leader: "Craghorn", army: "Kithguard" }]);
  });

  it("reports progress so a long import can show where it is", async () => {
    const onProgress = vi.fn();
    await fetchRoster("36052", preEventFetcher(), { withLists: true, onProgress });

    expect(onProgress).toHaveBeenCalledWith(0, 2);
    expect(onProgress).toHaveBeenLastCalledWith(2, 2);
  });

  it("keeps the roster when one player's list popup fails outright", async () => {
    // Losing one opponent's leaders is a hole in reference material. Losing the
    // roster means retyping every board by hand.
    const fetcher = vi.fn(async (url: string) => {
      const list = /player=(\d+)/.exec(url);
      if (list) {
        if (list[1] === "11") throw new LongshanksHttpError(404);
        return listFor(list[1]);
      }
      return url.includes("section=team") ? PRE_EVENT_TEAM : "";
    });

    const roster = await fetchRoster("36052", fetcher, { withLists: true, ...instant });

    expect(roster.teams[0].members[0].lists).toHaveLength(1);
    expect(roster.teams[0].members[1].lists).toEqual([]);
  });
});

describe("fetchHtml on desktop", () => {
  afterEach(() => setDesktopHttp(null));

  it("goes through the desktop bridge rather than the webview's fetch", async () => {
    // The bridge existing at all is the point: on desktop a plain fetch would be
    // CORS-blocked, so if this ever fell through to `fetch` the feature is dead.
    const getText = vi.fn(async () => ({ status: 200, body: TEAM }));
    setDesktopHttp({ getText });
    const spy = vi.spyOn(globalThis, "fetch");

    await expect(fetchHtml(URL_TEAM)).resolves.toBe(TEAM);
    expect(getText).toHaveBeenCalledWith(URL_TEAM, expect.objectContaining({ Accept: expect.any(String) }));
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it("turns a refusal into the error retry knows how to classify", async () => {
    setDesktopHttp({ getText: async () => ({ status: 403, body: "" }) });

    await expect(fetchHtml(URL_TEAM)).rejects.toMatchObject({ status: 403 });
    await expect(fetchHtml(URL_TEAM)).rejects.toSatisfy(isRetryable);
  });
});

describe("createDesktopHttp", () => {
  it("reports the status instead of throwing, leaving the verdict to the caller", async () => {
    const http = createDesktopHttp(async () => ({ status: 403, text: async () => "nope" }));

    await expect(http.getText(URL_TEAM, {})).resolves.toEqual({ status: 403, body: "nope" });
  });

  it("passes the browser-shaped headers straight through", async () => {
    const fetchFn = vi.fn(async () => ({ status: 200, text: async () => "ok" }));
    const http = createDesktopHttp(fetchFn);

    await http.getText(URL_TEAM, { "User-Agent": "Mozilla/5.0" });

    expect(fetchFn).toHaveBeenCalledWith(URL_TEAM, {
      method: "GET",
      headers: { "User-Agent": "Mozilla/5.0" },
    });
  });
});
