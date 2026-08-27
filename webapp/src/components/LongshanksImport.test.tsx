// @vitest-environment jsdom
/**
 * The import, checked at its two decisions.
 *
 * The parser, fetcher and board builder each have their own tests; this file is
 * only about the wiring between them and the screen -- that fetching reveals the
 * team picker, that picking a team and building calls back with saved boards, and
 * that a short-handed team is surfaced for the owner rather than swallowed.
 *
 * The network is the one thing mocked. `fetchRoster` is replaced with a canned
 * roster so the test never touches Longshanks; everything downstream (buildBoards,
 * saveBoards into localStorage) runs for real, because that is the wiring under
 * test.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Roster } from "../longshanks/types";
import { LongshanksImport } from "./LongshanksImport";

const fetchRoster = vi.fn<(input: string) => Promise<Roster>>();
vi.mock("../longshanks/fetch", () => ({
  fetchRoster: (input: string) => fetchRoster(input),
}));

const five = (prefix: string) =>
  Array.from({ length: 5 }, (_, i) => ({ userId: `${prefix}${i}`, name: `${prefix} P${i}`, lists: [] }));

const roster: Roster = {
  eventId: "33997",
  teams: [
    { teamId: "1", name: "Home Team", members: five("h") },
    { teamId: "2", name: "Rivals", members: five("r") },
    { teamId: "3", name: "Four Only", members: five("a").slice(0, 4) },
  ],
};

afterEach(cleanup);
beforeEach(() => {
  fetchRoster.mockReset();
  localStorage.clear();
});

function typeAndFetch(id: string) {
  fireEvent.change(screen.getByPlaceholderText(/33997/), { target: { value: id } });
  fireEvent.click(screen.getByRole("button", { name: /fetch/i }));
}

describe("LongshanksImport", () => {
  it("shows the team picker only after a roster is fetched", async () => {
    fetchRoster.mockResolvedValue(roster);
    render(<LongshanksImport onImported={vi.fn()} />);

    expect(screen.queryByRole("combobox")).toBeNull();
    typeAndFetch("33997");

    await waitFor(() => expect(screen.getByText(/found 3 teams/i)).toBeTruthy());
    expect(screen.getByRole("combobox")).toBeTruthy();
    expect(fetchRoster).toHaveBeenCalledWith("33997");
  });

  it("builds a board per other team and hands the saved list back", async () => {
    fetchRoster.mockResolvedValue(roster);
    const onImported = vi.fn();
    render(<LongshanksImport onImported={onImported} />);

    typeAndFetch("33997");
    await waitFor(() => screen.getByRole("combobox"));

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: /build boards/i }));

    expect(onImported).toHaveBeenCalledTimes(1);
    const saved = onImported.mock.calls[0][0];
    // Rivals imports; Four Only is short and is skipped; Home Team is us.
    const opponents = saved.map((b: { opponent: string }) => b.opponent);
    expect(opponents).toContain("Rivals");
    expect(opponents).not.toContain("Home Team");
    expect(opponents).not.toContain("Four Only");
  });

  it("surfaces a short-handed team as a downloadable skip, not a board", async () => {
    fetchRoster.mockResolvedValue(roster);
    const { container } = render(<LongshanksImport onImported={vi.fn()} />);

    typeAndFetch("33997");
    await waitFor(() => screen.getByRole("combobox"));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: /build boards/i }));

    expect(screen.getByText(/not having five named players/i)).toBeTruthy();
    const report = container.querySelector("textarea") as HTMLTextAreaElement;
    expect(report.value).toContain("Four Only");
    expect(report.value).toContain("Expected 5 players, found 4");
  });

  it("explains a bad id without touching the network", () => {
    render(<LongshanksImport onImported={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /fetch/i }));
    expect(screen.getByText(/paste a longshanks event/i)).toBeTruthy();
    expect(fetchRoster).not.toHaveBeenCalled();
  });

  it("reports a fetch failure in plain language", async () => {
    fetchRoster.mockRejectedValue(new Error("Longshanks returned status 500"));
    render(<LongshanksImport onImported={vi.fn()} />);
    typeAndFetch("33997");
    await waitFor(() => expect(screen.getByText(/status 500/i)).toBeTruthy());
    expect(screen.queryByRole("combobox")).toBeNull();
  });
});
