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
import { useEffect, useRef, useState } from "react";
import { BRAND, LINKS } from "../brand";
import { GUIDES } from "../content/docs";
import { DocViewer } from "./DocViewer";

export interface AboutHelpProps {
  onBack: () => void;
  /** Names where the back control returns to, which is not always the menu. */
  backLabel?: string;
  /**
   * Open straight onto a section of a guide, as the contextual help "?" does.
   * Null is the ordinary route in from the menu: the list of guides.
   */
  initialGuide?: { id: string; anchor: string } | null;
}

export function AboutHelp({ onBack, backLabel = "Menu", initialGuide = null }: AboutHelpProps) {
  const [openId, setOpenId] = useState<string | null>(initialGuide?.id ?? null);
  const open = openId ? (GUIDES.find((g) => g.id === openId) ?? null) : null;

  /*
    Land on the section that was asked for rather than the top of a long
    document. Once only: reopening the same guide by hand afterwards is a
    deliberate act, and yanking the reader back to the anchor then would be the
    screen fighting them. jsdom leaves scrollIntoView undefined, so it is
    guarded the same way DocViewer guards its own anchor jumps.
  */
  const jumped = useRef(false);
  useEffect(() => {
    if (jumped.current || !initialGuide || open?.id !== initialGuide.id) return;
    jumped.current = true;
    const el = document.getElementById(initialGuide.anchor);
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [open, initialGuide]);

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
          ‹ {backLabel}
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
