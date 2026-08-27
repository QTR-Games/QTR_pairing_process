/**
 * Turning two Longshanks panels into a roster.
 *
 * A Longshanks team event does not put its roster in the main event page. The
 * page ships a shell and loads the interesting parts over AJAX, so what a browser
 * shows and what a plain fetch returns are different documents. Two of those
 * loaded panels between them hold everything we need, and they are fetched from
 * `panel_standings.php?event=<id>&section=<section>`:
 *
 *   - `section=team`   -- every team, its id, and the names + user ids of its
 *                         members. This is the spine: who is on which team.
 *   - `section=player` -- one row per player-game, each carrying the faction and
 *                         leader that player brought. Aggregated per user id it
 *                         becomes the set of lists a player is running.
 *
 * The two join on the Longshanks user id, which both panels expose in the
 * `pop_user(<uid>,<event>)` handler on a player's name. So the team panel gives
 * structure and names, the player panel gives the armies, and this module stitches
 * them together into a `Roster`.
 *
 * Parsing is done with `DOMParser` against the real class names Longshanks uses,
 * not regex over raw HTML. The markup is a moving target maintained by someone
 * else; querying by the same classes the site's own JavaScript keys off is the
 * most stable thing available, and it degrades to "missing field" rather than
 * "wrong field" when a selector stops matching.
 */

import type { Roster, RosterList, RosterMember, RosterTeam } from "./types";

/** First capture of `pop_team(9952)` / `pop_team(9952);` -> "9952". */
function popArg(onclick: string | null, fn: "pop_team" | "pop_user"): string | undefined {
  if (!onclick) return undefined;
  const m = new RegExp(`${fn}\\(\\s*(\\d+)`).exec(onclick);
  return m ? m[1] : undefined;
}

/** Collapse runs of whitespace and trim -- Longshanks titles carry stray doubles. */
const tidy = (s: string): string => s.replace(/\s+/g, " ").trim();

/**
 * Read one army out of a Longshanks subfaction title.
 *
 * The title reads "<Leader> - <Army> Leader", e.g. "Hellyth - House Kallyss
 * Leader". Occasionally only the army is present ("House Kallyss Leader"), so
 * the leader half is treated as optional rather than assumed.
 *
 * Returns null when there is nothing usable, so callers can skip empties instead
 * of storing blank lists.
 */
export function parseSubfactionTitle(title: string | null | undefined): RosterList | null {
  if (!title) return null;
  let t = tidy(title);
  if (!t) return null;
  // Drop the trailing role word the site appends to every one of these.
  t = t.replace(/\s+Leader$/i, "").trim();
  if (!t) return null;
  const dash = t.indexOf(" - ");
  if (dash >= 0) {
    const leader = t.slice(0, dash).trim();
    const army = t.slice(dash + 3).trim();
    return { army: army || undefined, leader: leader || undefined };
  }
  return { army: t };
}

const parseDoc = (html: string): Document =>
  new DOMParser().parseFromString(html, "text/html");

/**
 * The teams and their members, from `section=team`.
 *
 * Each team is a `div.player` with an `id` of `player_<teamId>`; the team name
 * is the `pop_team` link, and each member is a `pop_user` link inside the
 * `.team_members` block. Members with no `pop_user` link (an unregistered slot)
 * are skipped rather than stored as a nameless row.
 */
export function parseTeamPanel(html: string): RosterTeam[] {
  const doc = parseDoc(html);
  const teams: RosterTeam[] = [];

  for (const el of Array.from(doc.querySelectorAll("div.player[id]"))) {
    const id = el.getAttribute("id") ?? "";
    const idMatch = /^player_(\d+)$/.exec(id);
    if (!idMatch) continue;

    const links = Array.from(el.querySelectorAll("a.player_link"));
    const nameLink = links.find((a) => /pop_team\(/.test(a.getAttribute("onclick") ?? ""));
    const name = tidy(nameLink?.textContent ?? "");
    if (!name) continue;

    const members: RosterMember[] = [];
    const scope = el.querySelector(".team_members") ?? el;
    for (const a of Array.from(scope.querySelectorAll("a.player_link"))) {
      const onclick = a.getAttribute("onclick");
      const userId = popArg(onclick, "pop_user");
      if (!userId) continue;
      const memberName = tidy(a.textContent ?? "");
      if (!memberName) continue;
      members.push({ userId, name: memberName, lists: [] });
    }

    teams.push({ teamId: idMatch[1], name, members });
  }

  return teams;
}

/** The user id an accordion row belongs to, from `class="player accordion <uid>"`. */
function accordionOwnerId(className: string): string | undefined {
  const m = /(?:^|\s)accordion\s+(\d+)(?:\s|$)/.exec(className);
  return m ? m[1] : undefined;
}

/**
 * Each player's lists, keyed by user id, from `section=player`.
 *
 * The panel repeats, once per player, a standings row (`div.player`) followed by
 * that player's game rows (`div.player.accordion`). Each game row's owning player
 * is not in its text -- the `.name` link there is the *opponent* -- but in the
 * row's own class: `class="player accordion <uid>"`. Inside `.factions` the
 * owner's army is shown first, then "vs", then the opponent's, so the first
 * `.logo.subfaction` is always the owner's own list for that round. Verified
 * against event 33997: player 24679 (Shadowflame Shard) shows "Lylyth -
 * Shadowflame Shard" first in every one of his rows, opponents second.
 *
 * Read across all of a player's rows and deduplicated by army+leader, those
 * first armies are the lists that player brought: a caster run in three rounds
 * lands once, a genuine second list lands as its own entry.
 */
export function parsePlayerLists(html: string): Map<string, RosterList[]> {
  const doc = parseDoc(html);
  const byUser = new Map<string, RosterList[]>();

  for (const row of Array.from(doc.querySelectorAll("div.player.accordion"))) {
    const userId = accordionOwnerId(row.getAttribute("class") ?? "");
    if (!userId) continue;

    // Owner's army is the first subfaction logo; anything after "vs" is the
    // opponent's and must not be attributed to this player.
    const own = row.querySelector(".factions .logo.subfaction, .factions .subfaction");
    const list = parseSubfactionTitle(own?.getAttribute("title"));
    if (!list) continue;

    const existing = byUser.get(userId) ?? [];
    const seen = existing.some((l) => l.army === list.army && l.leader === list.leader);
    if (!seen) existing.push(list);
    byUser.set(userId, existing);
  }

  return byUser;
}

/**
 * Stitch the two panels into a roster.
 *
 * The team panel decides who exists; the player panel only enriches. A member
 * with no rows in the player panel (did not play, or dropped) keeps an empty
 * `lists`, which is the honest state rather than a fabricated army.
 */
export function parseRoster(
  teamHtml: string,
  playerHtml: string,
  eventId: string,
  eventName?: string,
): Roster {
  const teams = parseTeamPanel(teamHtml);
  const lists = parsePlayerLists(playerHtml);

  for (const team of teams) {
    for (const member of team.members) {
      if (member.userId && lists.has(member.userId)) {
        member.lists = lists.get(member.userId) ?? [];
      }
    }
  }

  return { eventId, eventName, teams };
}
