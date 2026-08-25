import { useEffect, useState } from "react";

/**
 * The width at which the desktop workspace takes over.
 *
 * 1024 rather than something narrower because the workspace lays out three
 * columns and the middle one carries a 5x5 grid at a size you can read across
 * a table. Below this the phone layout is used verbatim -- not a reflowed
 * version of the desktop one -- so nothing here can regress the build that
 * goes to an event on a phone.
 */
export const WIDE = 1024;

/**
 * True when there is room for the desktop workspace.
 *
 * Listens rather than sampling once: a laptop gets docked and window-snapped,
 * and a layout that only reads the width at mount is wrong within a minute of
 * someone dragging the window to half the screen.
 */
export function useWideViewport(): boolean {
  const [wide, setWide] = useState(
    () => typeof window !== "undefined" && window.matchMedia(`(min-width: ${WIDE}px)`).matches,
  );

  useEffect(() => {
    const mq = window.matchMedia(`(min-width: ${WIDE}px)`);
    const onChange = (e: MediaQueryListEvent) => setWide(e.matches);
    mq.addEventListener("change", onChange);
    setWide(mq.matches);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return wide;
}
