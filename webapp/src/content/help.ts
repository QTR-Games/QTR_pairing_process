/*
  What each part of the screen is, in one short paragraph each.

  The contextual help overlay (see components/HelpOverlay.tsx) turns a tap into
  a lookup in this table: every explainable piece of UI carries a `data-help`
  attribute naming one of the ids below. Keeping the copy in
  one file rather than beside each component is deliberate -- it is prose about
  the app, written to be read in one voice, and it wants reviewing as a set the
  way the guides do.

  Each entry may name a section of a bundled guide. That link is the escape
  hatch, not the explanation: the card has to answer "what is this?" on its own,
  standing at a table mid-round, and the guide is there for the person who then
  wants the full detail.

  `anchor` is the GitHub-style heading slug the DocViewer assigns (see `slug`
  there). help.test.ts checks every one of them actually resolves to a heading
  in the guide it names, so a retitled section fails the suite rather than
  silently landing the reader at the top of the document. It also checks that
  every tag in the source has an entry here.
*/

export interface HelpTopic {
  /** Matches the `data-help` value on the element being explained. */
  id: string;
  /** Card heading -- what the thing is called. */
  title: string;
  /** Two or three sentences: what it is, and what it is for. */
  body: string;
  /** The guide section with the full detail, if one is worth offering. */
  guide?: {
    /** A `GUIDES` id from content/docs.ts. */
    id: string;
    /** Heading slug within that guide. */
    anchor: string;
    /** Button label, naming the section rather than saying "read more". */
    label: string;
  };
}

export const HELP_TOPICS: readonly HelpTopic[] = [
  {
    id: "header",
    title: "The header",
    body: `The board you have open, named after the opponent. Menu takes you back
      to the front screen, where the settings, the saved boards and the guides
      live. Nothing is lost by leaving -- boards and rounds save themselves as
      you go.`,
    guide: {
      id: "users-guide",
      anchor: "the-three-screens",
      label: "The three screens",
    },
  },
  {
    id: "tabs",
    title: "Board, Round and Saved",
    body: `Board is where you rate the matchups and read what the grid says.
      Round is the live pairing session you run at the table. Saved is every
      board you have kept, and the place to start a new one.`,
    guide: {
      id: "users-guide",
      anchor: "the-three-screens",
      label: "The three screens",
    },
  },
  {
    id: "verdict-reading",
    title: "The verdict",
    body: `The one-line read on this board, in plain words, with the chip above
      it summarising it in a single term. It updates as you rate, so it is worth
      a glance after every few cells rather than only at the end.`,
    guide: {
      id: "users-guide",
      anchor: "reading-the-verdict",
      label: "Reading the verdict",
    },
  },
  {
    id: "verdict-numbers",
    title: "Guaranteed, Typical and Ceiling",
    body: `Guaranteed is what you hold if the opponent hunts you perfectly.
      Typical is what tends to happen when they play their own board instead.
      Ceiling is the best still reachable. Use Guaranteed when you must not
      lose and Typical when you must win.`,
    guide: {
      id: "users-guide",
      anchor: "three-numbers-guaranteed--typical--ceiling",
      label: "Three numbers: Guaranteed / Typical / Ceiling",
    },
  },
  {
    id: "insight-card",
    title: "An insight card",
    body: `One thing worth knowing about this board -- a protection, a trade-off,
      a player who can be forced into a bad game. Tapping a card highlights the
      cells it is talking about on the grid.`,
    guide: {
      id: "users-guide",
      anchor: "the-insight-cards",
      label: "The insight cards",
    },
  },
  {
    id: "currency-toggle",
    title: "The pts / % pill",
    body: `Switches this card between rating points and round-win chance. They
      are two different currencies and never add up: points are game-by-game
      totals, the percentage is the chance of taking three of the five games.
      Holding the card does the same thing.`,
    guide: {
      id: "users-guide",
      anchor: "two-currencies",
      label: "Two currencies",
    },
  },
  {
    id: "dodge",
    title: "Pricing your worst matchup",
    body: `Works out which matchup hurts most and what staying out of it would
      cost, in round-win chance. Some are free to refuse, some cost real chance,
      and some cannot be dodged at all -- which is worth knowing before you spend
      nominations trying.`,
    guide: {
      id: "how-to",
      anchor: "decide-whether-to-dodge-your-worst-matchup",
      label: "Decide whether to dodge your worst matchup",
    },
  },
  {
    id: "protect-choice",
    title: "Protect first",
    body: `When two players are equally exposed the app has nothing left to
      separate them, so the call is yours. Your choice is saved with the board
      and marked on the grid; it does not change the pairing suggestions.`,
    guide: {
      id: "users-guide",
      anchor: "the-insight-cards",
      label: "The insight cards",
    },
  },
  {
    id: "scale",
    title: "The rating scale",
    body: `How you score each matchup -- 1 to 5, a stoplight, or whatever the
      list offers. It only changes the labels you tap; the maths underneath is
      the same, and switching scales keeps the ratings you have already given.`,
    guide: {
      id: "users-guide",
      anchor: "rating-the-grid",
      label: "Rating the grid",
    },
  },
  {
    id: "first-up",
    title: "Who puts a player up first",
    body: `The protocol's opening move, settled by a dice-off before any name is
      called. Set it to match the roll. If the board cares which way it goes, a
      line underneath says so and offers to set it for you.`,
    guide: {
      id: "users-guide",
      anchor: "setting-up-a-board",
      label: "Setting up a board",
    },
  },
  {
    id: "rosters",
    title: "The rosters",
    body: `Your five players and theirs. Names are optional -- the grid works
      with the defaults -- but naming them makes the reading and the live round
      say who they mean instead of "ours 3".`,
    guide: {
      id: "users-guide",
      anchor: "setting-up-a-board",
      label: "Setting up a board",
    },
  },
  {
    id: "grid",
    title: "The grid",
    body: `Every one of your players against every one of theirs. Tap a cell to
      rate that matchup from your side; hold one to price it -- what opening
      there would cost and what refusing it would cost. Everything else on this
      screen is read off these 25 numbers.`,
    guide: {
      id: "users-guide",
      anchor: "rating-the-grid",
      label: "Rating the grid",
    },
  },
  {
    id: "start-round",
    title: "Start the round",
    body: `Opens the live session for this board and steps you through the
      pairing protocol at the table. The board and its ratings stay exactly as
      they are, and you can come back to them at any point.`,
    guide: {
      id: "users-guide",
      anchor: "running-a-live-round",
      label: "Running a live round",
    },
  },
  {
    id: "round-prompt",
    title: "Where the round stands",
    body: `The decision in front of you right now, with how many tables are set
      and what the round is worth so far underneath. It changes after every
      commit, so it is always describing the next call rather than the last
      one.`,
    guide: {
      id: "users-guide",
      anchor: "running-a-live-round",
      label: "Running a live round",
    },
  },
  {
    id: "round-controls",
    title: "Back and Restart",
    body: `Back undoes the last step, as often as you need -- the phone's own
      back gesture does the same thing. Restart clears the whole round and
      begins again from an empty table plan. Neither touches your ratings.`,
    guide: {
      id: "users-guide",
      anchor: "stepping-back",
      label: "Stepping back",
    },
  },
  {
    id: "round-options",
    title: "The options",
    body: `Every move available at this point in the protocol, best first, with
      what each one costs against that best. Tap the one that actually happened
      at the table -- these are suggestions to read, not instructions, and the
      round follows whatever you tap.`,
    guide: {
      id: "how-to",
      anchor: "run-a-round-at-the-table",
      label: "Run a round at the table",
    },
  },
  {
    id: "round-advice",
    title: "The advice lines",
    body: `Prose about why the top options rank the way they do, and which of
      your players still has leverage. How much of it you get -- or none at all
      -- is the advice level setting in the menu.`,
    guide: {
      id: "users-guide",
      anchor: "settings",
      label: "Settings",
    },
  },
  {
    id: "surprise-alert",
    title: "Surprise-pick alert",
    body: `Their last choice gave up more than your grid says it should have.
      Either they read a matchup very differently from you, or they are playing
      for something you have not spotted -- so re-read the board before you
      commit the next one.`,
    guide: {
      id: "users-guide",
      anchor: "surprisepick-alerts",
      label: "Surprise-pick alerts",
    },
  },
  {
    id: "committed",
    title: "Tables set",
    body: `The pairings agreed so far. Hold one to record which table it is on,
      and Copy puts the whole list on the clipboard for the team chat.`,
    guide: {
      id: "users-guide",
      anchor: "table-tracking",
      label: "Table tracking",
    },
  },
  {
    id: "boards",
    title: "Saved boards",
    body: `Every board on this device, most recently touched first. Opening one
      resumes its round if it had one. Backing up and restoring the lot is in
      Menu, not here.`,
    guide: {
      id: "users-guide",
      anchor: "saved-boards-backup--restore",
      label: "Saved boards, backup & restore",
    },
  },
  {
    id: "reach",
    title: "Reach",
    body: `Which of your players can still be steered into which of their
      players, given what is already committed. A matchup you can no longer
      reach is not worth planning around, however well it rates.`,
    guide: {
      id: "users-guide",
      anchor: "glossary",
      label: "Glossary",
    },
  },
] as const;

const BY_ID = new Map(HELP_TOPICS.map((t) => [t.id, t]));

/** The topic for a `data-help` id, or null if there is nothing written for it. */
export function helpTopic(id: string | null | undefined): HelpTopic | null {
  return id ? (BY_ID.get(id) ?? null) : null;
}
