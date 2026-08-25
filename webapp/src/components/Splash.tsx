/*
  The launch screen.

  Deliberately timid about getting in the way. This app's job is to be open on a
  table with a clock running, so the splash is built so that it can never be the
  reason someone is waiting:

    - it dismisses itself after a fixed, short interval
    - any tap, click or key press dismisses it immediately
    - `prefers-reduced-motion` drops the animation and shortens the hold
    - the timer is the only thing that can hold it, so a failed image load or a
      dropped event cannot strand anyone on it

  The logo is a placeholder and is rendered at a fixed 128px rather than a
  percentage so that swapping in art of a different size cannot change the
  layout.
*/
import { useEffect, useRef, useState } from "react";
import { BRAND } from "../brand";

/** How long the splash holds before it retires itself. */
const HOLD_MS = 1500;
/** Length of the fade out. Must match the CSS transition. */
const FADE_MS = 320;

function prefersReducedMotion(): boolean {
  return (
    typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function Splash({ onDone }: { onDone: () => void }) {
  const [leaving, setLeaving] = useState(false);
  // Guards against the tap handler and the timer both firing onDone.
  const finished = useRef(false);
  const reduced = prefersReducedMotion();

  useEffect(() => {
    const dismiss = () => {
      if (finished.current) return;
      finished.current = true;
      if (reduced) {
        onDone();
        return;
      }
      setLeaving(true);
      window.setTimeout(onDone, FADE_MS);
    };

    const hold = window.setTimeout(dismiss, reduced ? 400 : HOLD_MS);
    window.addEventListener("keydown", dismiss);
    window.addEventListener("pointerdown", dismiss);
    return () => {
      window.clearTimeout(hold);
      window.removeEventListener("keydown", dismiss);
      window.removeEventListener("pointerdown", dismiss);
    };
  }, [onDone, reduced]);

  return (
    <div
      className={`splash${leaving ? " leaving" : ""}${reduced ? " still" : ""}`}
      role="status"
      aria-label={`${BRAND.product} by ${BRAND.name}`}
      data-testid="splash"
    >
      <div className="splash-mark">
        <img src={BRAND.logo} alt="" width={128} height={124} draggable={false} />
        <p className="splash-name">{BRAND.name}</p>
        <p className="splash-tagline">{BRAND.tagline}</p>
      </div>
      <p className="splash-skip">Tap to continue</p>
    </div>
  );
}
