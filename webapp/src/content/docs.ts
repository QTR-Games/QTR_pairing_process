/*
  The end-user guides, bundled into the app.

  These are the same Markdown files that live at the repository root under
  `docs/` and are published on GitHub -- imported here as raw strings so the
  About & Help screen can render them in-app, formatted and scrollable, with no
  network. That offline promise is the whole point: the guides have to be
  readable standing at a table in aeroplane mode, which rules out linking out to
  GitHub as the primary path.

  The import reaches up out of `webapp/` into the repo root on purpose. Keeping
  one canonical copy means the on-GitHub docs and the in-app docs can never
  drift; the alternative -- a second copy under src/ kept in sync by a script --
  buys nothing here and adds a way to forget. Vite bakes the string into the
  bundle at build time, so nothing outside `webapp/` is needed at runtime. The
  dev server also has to be allowed to read it: see `server.fs.allow` in
  vite.config.ts.
*/
import usersGuide from "../../../docs/klikklak-users-guide.md?raw";
import tipSheet from "../../../docs/klikklak-tip-sheet.md?raw";
import howTo from "../../../docs/klikklak-how-to.md?raw";

/** Where each guide lives on GitHub, for the "read it online" fallback. */
const DOCS_BASE =
  "https://github.com/QTR-Games/QTR_pairing_process/blob/main/docs";

export interface Guide {
  /** Stable id, also used as the test handle and the detail-view key. */
  id: string;
  /** Button label on the list. */
  title: string;
  /** One line under the title saying what it is for. */
  blurb: string;
  /** The raw Markdown, rendered in-app. */
  body: string;
  /** The same document on GitHub, for the external-open fallback. */
  href: string;
}

/*
  Ordered the way someone new should meet them: the full guide first for the
  person reading ahead of the event, the tip sheet second for the person who
  wants one screen at the table, the how-to last for the specific "how do I..."
  question.
*/
export const GUIDES: readonly Guide[] = [
  {
    id: "users-guide",
    title: "User's Guide",
    blurb: "The full walkthrough, start to finish.",
    body: usersGuide,
    href: `${DOCS_BASE}/klikklak-users-guide.md`,
  },
  {
    id: "tip-sheet",
    title: "Tip Sheet",
    blurb: "One page to keep open at the table.",
    body: tipSheet,
    href: `${DOCS_BASE}/klikklak-tip-sheet.md`,
  },
  {
    id: "how-to",
    title: "How-to Guide",
    blurb: "Short recipes for specific tasks.",
    body: howTo,
    href: `${DOCS_BASE}/klikklak-how-to.md`,
  },
] as const;
