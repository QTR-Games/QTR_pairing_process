/*
  About & Help.

  The one place in the app that is not a pairing decision: what this is, who
  made it, and the end-user guides themselves. It is reached from the menu and
  is a screen of its own rather than another <details> in the menu, because the
  guides are long and want the whole viewport to be read at a table.

  Two views, one screen. The list of guides is the front of it; tapping one
  swaps in the reader for that guide, and a back control returns to the list.
  There is no router -- App owns which screen is up, and this owns which guide
  is open -- which keeps the phone's back button doing whatever the browser
  does and nothing this screen has to promise.
*/
import { useState } from "react";
import { BRAND, LINKS } from "../brand";
import { GUIDES } from "../content/docs";
import { DocViewer } from "./DocViewer";

export function AboutHelp({ onBack }: { onBack: () => void }) {
  const [openId, setOpenId] = useState<string | null>(null);
  const open = openId ? (GUIDES.find((g) => g.id === openId) ?? null) : null;

  if (open) {
    return (
      <div className="about" data-testid="about">
        <header className="about-head">
          <button className="ghost app-menu" onClick={() => setOpenId(null)}>
            ‹ All guides
          </button>
        </header>
        <DocViewer markdown={open.body} onOpenGuide={setOpenId} />
        <div className="about-links">
          <a className="ghost wide" href={open.href} target="_blank" rel="noreferrer">
            View this guide on GitHub
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="about" data-testid="about">
      <header className="about-head">
        <button className="ghost app-menu" onClick={onBack}>
          ‹ Menu
        </button>
        <h1>About &amp; Help</h1>
      </header>

      <p className="hint about-intro">
        {BRAND.product} &mdash; {BRAND.tagline} Everything is stored on this
        device only; nothing is uploaded, and the guides below work with no
        signal.
      </p>

      <div className="about-guides">
        {GUIDES.map((g) => (
          <button
            key={g.id}
            className="about-guide"
            data-testid={`guide-${g.id}`}
            onClick={() => setOpenId(g.id)}
          >
            <span className="about-guide-title">{g.title}</span>
            <span className="hint">{g.blurb}</span>
          </button>
        ))}
      </div>

      <div className="about-links">
        <a
          className="ghost wide"
          href="https://github.com/QTR-Games/QTR_pairing_process"
          target="_blank"
          rel="noreferrer"
        >
          The project on GitHub
        </a>
        <a className="ghost wide" href={LINKS.bugs} target="_blank" rel="noreferrer">
          Log a bug
        </a>
      </div>

      <p className="hint about-by">by {BRAND.name}</p>
    </div>
  );
}
