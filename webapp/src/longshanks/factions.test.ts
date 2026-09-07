/**
 * The army table, and the leader search that leans on it.
 *
 * Two things are worth guarding here. The badge codes have to stay unique --
 * they were hand-assigned precisely because derived initials collided, and a
 * regenerated table that quietly reintroduces a collision would put the same
 * chip on two different armies. And `findLeader` has to keep refusing to guess:
 * every case below where it returns undefined is a case where a plausible answer
 * existed and was rejected, which is the behaviour that makes a leader on a
 * board worth trusting.
 *
 * The list snippets are shortened from real event-36052 registrations.
 */
import { describe, expect, it } from "vitest";
import { ARMIES, armyInfo, findLeader } from "./factions";

describe("ARMIES", () => {
  it("gives every army a unique badge code", () => {
    const codes = ARMIES.map((a) => a.code);
    expect(new Set(codes).size).toBe(codes.length);
  });

  it("names every army uniquely, since the name is the lookup key", () => {
    const names = ARMIES.map((a) => a.army.toLowerCase());
    expect(new Set(names).size).toBe(names.length);
  });

  it("gives every army a two-letter code and a colour", () => {
    for (const a of ARMIES) {
      expect(a.code).toMatch(/^[0-9A-Z]{2}$/);
      expect(a.color).toMatch(/^#[0-9a-f]{6}$/);
    }
  });
});

describe("armyInfo", () => {
  it("looks an army up regardless of case or padding", () => {
    expect(armyInfo("  storm legion ")?.code).toBe("SL");
    expect(armyInfo("Kithguard")?.faction).toBe("Southern Kriels");
  });

  it("returns nothing for an army it does not know", () => {
    expect(armyInfo("Some New Army")).toBeUndefined();
    expect(armyInfo(undefined)).toBeUndefined();
    expect(armyInfo("")).toBeUndefined();
  });
});

describe("findLeader", () => {
  it("finds the leader inside the full model name the list writes out", () => {
    expect(findLeader("Southern Kriels - Kithguard\nMajor Abraham Stormcraw\n29 Fortress King", "Kithguard"))
      .toEqual({ leader: "Stormcraw", army: "Kithguard" });
  });

  it("matches a leader whose Longshanks name carries a disambiguating number", () => {
    // "Caine 4" is how Longshanks distinguishes the Storm Legion Caine; the
    // list only ever says "Major Allister Caine".
    expect(findLeader("Grand Melee - 100 pts\nMajor Allister Caine\n7 Courser 1", "Storm Legion"))
      .toEqual({ leader: "Caine 4", army: "Storm Legion" });
  });

  it("finds a leader whose whole name is the model name", () => {
    expect(findLeader("The King of Nothing\n12 Cage Rager", "Grymkin"))
      .toEqual({ leader: "The King of Nothing", army: "Grymkin" });
  });

  it("widens past the hinted army when the player brought a second army's list", () => {
    // Longshanks shows one badge per player. This player's badge says Sea
    // Raiders; the list is a Cygnar one.
    expect(findLeader("Right in the Hux\nCaptain Raef Huxley\n7 Courser 1", "Sea Raiders"))
      .toEqual({ leader: "Huxely", army: "Storm Legion" });
  });

  it("takes the first of a Grand Melee list's two casters", () => {
    // A 100pt list fields two warcasters, both free, and the one written first
    // is the one the player leads with -- and the one the list is named after.
    expect(
      findLeader("Sergeant Hulder Craghorn\nGeneral Gunnbjorn\n10 Scrappers", "Kithguard"),
    ).toEqual({ leader: "Craghorn", army: "Kithguard" });
  });

  it("orders casters by position, not by the order of the army table", () => {
    expect(findLeader("Master Necrosurgeon Sepsira\nLich Lord Dekathus")?.leader).toBe("Sepsira");
    expect(findLeader("Lich Lord Dekathus\nMaster Necrosurgeon Sepsira")?.leader).toBe("Dekathus");
  });

  it("passes over a leader the list paid points for", () => {
    // Constance Blaize is a leader in her own right and a 20-point purchase in
    // anyone else's list. The points are what say she is not running this one.
    expect(
      findLeader("Major Allister Caine\n20 Constance Blaize, Radiance Of Morrow\nGallant"),
    ).toEqual({ leader: "Caine", army: "First Army" });
  });

  it("refuses to guess when every candidate was paid for", () => {
    // Nobody here is leading: both are purchases, and the list's actual caster
    // is one this table does not know. Answering would be inventing a leader.
    expect(
      findLeader("20 Constance Blaize, Radiance Of Morrow\n9 Eiryss, Fury of Retribution"),
    ).toBeUndefined();
  });

  it("treats one person shared by two armies as a single answer", () => {
    // Caine leads both First Army and Gravediggers. Two rows, one caster.
    expect(findLeader("Major Allister Caine\n9 Trencher Infantry")?.leader).toBe("Caine");
  });

  it("does not match a leader name buried inside a longer word", () => {
    // "Grim" leads Storm of the North and is a prefix of "Grimtusk", who leads
    // Kithguard. A naive substring match would answer "Grim" from the hinted
    // army and never look further; the word boundary sends it to the right one.
    expect(findLeader("Warchief Grimtusk\n10 Scrappers", "Storm of the North")).toEqual({
      leader: "Grimtusk",
      army: "Kithguard",
    });
  });

  it("takes a hint that names a faction rather than one of its armies", () => {
    // Longshanks badges some players with the army and others with the parent
    // faction. Read as an army, "Dusk" matches nothing at all.
    expect(findLeader("Scyrafael, Nis-Issyr of Desolations\n14 Eidolon 1", "Dusk")).toEqual({
      leader: "Scyrafael",
      army: "House Kallyss",
    });
  });

  it("finds a leader the list writes under another name", () => {
    // Longshanks calls her "Old Witch"; the card says "Zevanna Agha".
    expect(findLeader("Zevanna Agha, the Fate Keeper\n12 Cage Rager", "Grymkin")).toEqual({
      leader: "Old Witch",
      army: "Grymkin",
    });
  });

  it("returns nothing for a list with no recognisable leader", () => {
    expect(findLeader("Made ya look\nTOTAL POINTS 100/100", "Convergence of Cyriss")).toBeUndefined();
  });

  it("tells two printings of one character apart by their card titles", () => {
    // Both Skarres lead Blackfleet, so neither the name nor the badge separates
    // them. The title the list was exported with does.
    expect(findLeader("Pirate Queen Skarre\n18 Kraken", "Blackfleet")).toEqual({
      leader: "Skarre 1",
      army: "Blackfleet",
    });
    expect(findLeader("Skarre, Admiral of the Black Fleet\n18 Kraken", "Blackfleet")).toEqual({
      leader: "Skarre 3",
      army: "Blackfleet",
    });
    expect(findLeader("Lylyth, Herald of Everblight\n15 Ravagore", "Ravens of War")).toEqual({
      leader: "Lylyth 1",
      army: "Ravens of War",
    });
    expect(findLeader("Lylyth, Reckoning of Everblight\n15 Ravagore", "Ravens of War")).toEqual({
      leader: "Lylyth 3",
      army: "Ravens of War",
    });
  });

  it("drops the number when a list names a character without their title", () => {
    // Nothing in the list says which Skarre, so nothing on screen should either.
    expect(findLeader("Skarre\n18 Kraken", "Blackfleet")).toEqual({
      leader: "Skarre",
      army: "Blackfleet",
    });
  });

  it("keeps the number where a character has only one printing in the army", () => {
    // Storm Legion fields one Caine, so "Caine 4" is not a guess.
    expect(findLeader("Major Allister Caine\n17 Deuce", "Storm Legion")).toEqual({
      leader: "Caine 4",
      army: "Storm Legion",
    });
  });
});
