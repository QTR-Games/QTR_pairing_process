/**
 * What a Longshanks event roster looks like once it is off the web and in a
 * shape this app can use.
 *
 * This is the seam between the scrape and the boards. The parser (`parse.ts`)
 * produces a `Roster`; the board builder (`buildBoards.ts`) turns the chosen
 * team's opponents into playable boards. Keeping the roster as its own plain
 * type means the parser can be tested against saved event HTML without any of
 * the board machinery, and the builder can be tested against a hand-written
 * roster without any HTML at all.
 *
 * Everything past a player's name is optional on purpose. The reliable spine of
 * a Longshanks team event is "team -> five names"; the faction, the leader and
 * the lists a player brings are only present once that player has actually been
 * entered, which on the morning of an event is often not yet true. A roster
 * that demanded them would refuse exactly the early import the owner wants.
 */

/**
 * One army a player brought -- a faction and the model leading it.
 *
 * A Warmachine player registers more than one list for an event, so a member
 * carries a small array of these rather than a single pair. Both fields are
 * optional because a title on Longshanks can name only the army, and because a
 * pre-event import may have the player without any list yet.
 */
export interface RosterList {
  /** The faction / army, e.g. "House Kallyss". */
  army?: string;
  /** The model leading it, e.g. "Hellyth". */
  leader?: string;
}

export interface RosterMember {
  /** Longshanks user id, used only to join the two panels. May be absent. */
  userId?: string;
  name: string;
  /** Distinct lists this player brought, in the order first seen. */
  lists: RosterList[];
}

export interface RosterTeam {
  /** Longshanks team id (`pop_team(<id>)`), used as a stable key. May be absent. */
  teamId?: string;
  name: string;
  members: RosterMember[];
}

export interface Roster {
  eventId: string;
  eventName?: string;
  teams: RosterTeam[];
}
