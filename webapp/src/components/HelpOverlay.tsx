/*
  Contextual help: a floating "?" and a tap-to-explain mode.

  Nobody arrives at an event having read the guides, and mid-round there is no
  time to leave the screen and look something up. This is the discoverability
  layer over the UI that already exists: tap the "?", then tap the thing you do
  not recognise, and a card says what it is. Tap the "?" again to leave.

  It explains rather than acts. While help mode is on, every pointer and mouse
  event is caught in the CAPTURE phase on `document` and stopped there, so
  nothing underneath runs -- no rating gets typed, no pairing gets committed, no
  long-press fires. That matters more here than anywhere else in the app: the
  screens this floats over are the ones where a stray tap costs a round.

  Capture-and-stop, rather than a full-screen transparent catcher, because the
  overlay has to know WHAT was tapped. A catcher would swallow the coordinates
  and leave us reaching for `elementsFromPoint`; catching the event on its way
  down means the real target is right there, and the dim behind the card can
  stay `pointer-events: none` decoration.

  The mapping is a `data-help` attribute on the element, or on any ancestor of
  it, naming one of the HELP_TOPICS ids in content/help.ts. Anything not tagged
  says so plainly instead of guessing.

  Deliberately not mounted on the splash or the main menu: the menu is a list of
  labelled buttons that needs no gloss, and a help mode over a screen with two
  controls is noise.
*/
import { useEffect, useRef, useState } from "react";
import { helpTopic, type HelpTopic } from "../content/help";

export interface HelpLayerProps {
  /** Open a bundled guide at one of its sections. */
  onOpenGuide: (guideId: string, anchor: string) => void;
}

/*
  Every way a tap can reach the app. Swallowing the mouse pair as well as the
  pointer pair keeps native defaults -- a select opening, an input taking focus
  -- from firing on browsers that still emit both, and `click` is swallowed on
  its own account because preventing a pointerdown does not prevent the click
  that follows it.
*/
const SWALLOWED = [
  "pointerdown",
  "pointerup",
  "mousedown",
  "mouseup",
  "click",
  "dblclick",
  "contextmenu",
] as const;

/** Our own controls stay live while help mode is on. */
const HELP_UI = ".help-ui";

export function HelpLayer({ onOpenGuide }: HelpLayerProps) {
  const [on, setOn] = useState(false);
  const [topic, setTopic] = useState<HelpTopic | null>(null);
  // A tap that landed on nothing explainable. Distinct from "nothing tapped
  // yet", which still shows the invitation.
  const [missed, setMissed] = useState(false);

  /*
    A tap fires pointerdown and then click, and both are worth handling: the
    pointer event is what a phone produces, the click is what a keyboard
    produces on a focused control. Resolving on both would answer twice, so the
    click is ignored when a pointer event has just answered for it. A timestamp
    rather than a flag, because a pointerdown that never becomes a click --
    dragged off the element, cancelled by a scroll -- must not leave the next
    keyboard activation permanently ignored.
  */
  const lastPointerAt = useRef(0);

  useEffect(() => {
    if (!on) return;

    const explain = (target: EventTarget | null) => {
      const el = target instanceof Element ? target.closest("[data-help]") : null;
      const found = helpTopic(el?.getAttribute("data-help"));
      setTopic(found);
      setMissed(found === null);
    };

    const handle = (e: Event) => {
      const target = e.target;
      // Leave our own buttons alone, or the overlay could not be closed from
      // inside itself.
      if (target instanceof Element && target.closest(HELP_UI)) return;

      e.preventDefault();
      e.stopPropagation();

      if (e.type === "pointerdown" || e.type === "mousedown") {
        lastPointerAt.current = Date.now();
        explain(target);
      } else if (e.type === "click" && Date.now() - lastPointerAt.current > 1000) {
        explain(target);
      }
    };

    const exitOnEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOn(false);
    };

    for (const type of SWALLOWED) document.addEventListener(type, handle, true);
    document.addEventListener("keydown", exitOnEscape, true);
    return () => {
      for (const type of SWALLOWED) document.removeEventListener(type, handle, true);
      document.removeEventListener("keydown", exitOnEscape, true);
    };
  }, [on]);

  const toggle = () => {
    setOn((was) => !was);
    setTopic(null);
    setMissed(false);
  };

  return (
    <>
      {/*
        Decoration only: the dim says the screen is in a different mode, and
        `pointer-events: none` keeps it from being the thing that gets tapped.
        The capture listener above is what actually intercepts.
      */}
      {on && <div className="help-scrim" data-testid="help-scrim" />}

      {/*
        One fixed dock holds both, so the card can never land under the button
        that opened it. The dock itself takes no taps -- only its children do --
        or it would be a full-width strip swallowing the bottom of the screen.
      */}
      <div className="help-dock help-ui">
        <button
          type="button"
          className={"help-fab" + (on ? " on" : "")}
          data-testid="help-fab"
          aria-pressed={on}
          aria-label={on ? "Leave help mode" : "What is this? Explain the screen"}
          onClick={toggle}
        >
          ?
        </button>

        {on && (
          <div
            className="help-card"
            role="dialog"
            aria-label="Contextual help"
            data-testid="help-card"
          >
            {topic ? (
              <Explanation
                topic={topic}
                onOpenGuide={(guideId, anchor) => {
                  onOpenGuide(guideId, anchor);
                  setOn(false);
                }}
              />
            ) : (
              <>
                <p className="help-card-title">
                  {missed ? "Nothing to explain there" : "What is this?"}
                </p>
                <p className="help-card-body">
                  {missed
                    ? `That part of the screen has no explanation of its own. Try a card,
                       the grid, a control, or the header.`
                    : `Tap anything on the screen and this card will say what it is.
                       Nothing you tap will change the board or the round while this is
                       open.`}
                </p>
                <p className="help-card-hint">Done leaves help mode.</p>
              </>
            )}
            <button type="button" className="primary wide" onClick={toggle}>
              Done
            </button>
          </div>
        )}
      </div>
    </>
  );
}

/**
 * One topic, with its way out to the full detail.
 *
 * A component rather than a branch inline above so the optional guide link can
 * be read off a narrowed local. The link closes help mode on the way out --
 * leaving it armed would put the reader on the About screen with a mode running
 * over a screen it was never mounted on.
 */
function Explanation({
  topic,
  onOpenGuide,
}: {
  topic: HelpTopic;
  onOpenGuide: (guideId: string, anchor: string) => void;
}) {
  const guide = topic.guide;
  return (
    <>
      <p className="help-card-title">{topic.title}</p>
      <p className="help-card-body">{topic.body}</p>
      {guide && (
        <button
          type="button"
          className="ghost wide"
          onClick={() => onOpenGuide(guide.id, guide.anchor)}
        >
          Read “{guide.label}”
        </button>
      )}
      <p className="help-card-hint">
        Tap anything else to explain it, or Done to go back to using the app.
      </p>
    </>
  );
}
