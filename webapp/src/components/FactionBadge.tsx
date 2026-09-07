/**
 * The little coloured chip that says which army an opponent is playing.
 *
 * Longshanks marks a player's army with a faction logo, and at a glance that
 * logo is the fastest thing on the page to read -- you know who you are looking
 * at before you have read a word. This is the same idea without the artwork:
 * those logos are Privateer Press's, not ours to ship, and an app that has to
 * work with no signal cannot hotlink them either. A two-letter code on the
 * faction's own colour keeps the property that matters, which is that it is
 * recognisable without being read.
 *
 * An army the catalogue does not know still gets a chip, in grey, with the first
 * two letters of whatever Longshanks called it. New armies arrive between
 * releases and the alternative -- showing nothing -- would hide the fact that a
 * faction is known at all.
 */

import { armyInfo } from "../longshanks/factions";

export function FactionBadge({ army }: { army?: string }) {
  if (!army) return null;
  const info = armyInfo(army);
  const code = info?.code ?? army.replace(/[^A-Za-z]/g, "").slice(0, 2).toUpperCase();
  const label = info ? `${info.army} (${info.faction})` : army;
  return (
    <span className="faction-badge" style={{ background: info?.color ?? "#4b5563" }} title={label}>
      {code || "??"}
    </span>
  );
}
