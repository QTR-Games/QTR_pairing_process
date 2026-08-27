import { useState } from "react";
import { fetchRoster } from "../longshanks/fetch";
import { buildBoards, type BuildFailure } from "../longshanks/buildBoards";
import type { Roster } from "../longshanks/types";
import { saveBoards, type Board } from "../model/board";

interface Props {
  /** Called with the full saved list once boards are imported, so the app re-renders. */
  onImported: (boards: Board[]) => void;
}

type Note = { tone: "ok" | "bad"; text: string } | null;

/**
 * Seed a whole event's worth of boards from Longshanks.
 *
 * The problem this solves is the morning of a team event: thirty opposing teams,
 * five players each, and the owner otherwise copying names off a sheet into a
 * blank board per table while a round is about to start. Here they paste the
 * event id once the night before, pick which team is theirs, and every other
 * team becomes a board with their five players already down the left and the
 * opponent's five across the top -- only the pairing is left to fill in.
 *
 * The flow is two steps on purpose. Fetching the roster and choosing your team
 * are different decisions: the first is "get the data", the second is "which of
 * these is us", and you cannot make the second until the first has told you who
 * is in the event. So the team picker only appears once a roster is in hand.
 *
 * Teams that come back short of five players are not silently dropped -- Longshanks
 * rosters are incomplete before an event, and a board with a blank opponent slot
 * is a trap. They surface as a list the owner can read and download, and add by
 * hand, which is faster than re-checking thirty teams to find the two that failed.
 */
export function LongshanksImport({ onImported }: Props) {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [roster, setRoster] = useState<Roster | null>(null);
  const [teamId, setTeamId] = useState("");
  const [note, setNote] = useState<Note>(null);
  const [failures, setFailures] = useState<BuildFailure[]>([]);
  const [report, setReport] = useState("");

  const reset = () => {
    setRoster(null);
    setTeamId("");
    setFailures([]);
    setReport("");
    setNote(null);
  };

  const fetchIt = async () => {
    if (!input.trim()) {
      setNote({ tone: "bad", text: "Paste a Longshanks event id or URL first." });
      return;
    }
    setBusy(true);
    setNote({ tone: "ok", text: "Fetching the event roster from Longshanks…" });
    reset();
    try {
      const r = await fetchRoster(input);
      if (r.teams.length === 0) {
        setNote({ tone: "bad", text: "That event has no teams yet, or is not a team event." });
        return;
      }
      setRoster(r);
      setNote({
        tone: "ok",
        text: `Found ${r.teams.length} teams. Which one is yours?`,
      });
    } catch (e) {
      setNote({ tone: "bad", text: e instanceof Error ? e.message : "Could not reach Longshanks." });
    } finally {
      setBusy(false);
    }
  };

  const build = () => {
    if (!roster || !teamId) {
      setNote({ tone: "bad", text: "Pick which team is yours first." });
      return;
    }
    const { boards, failures: failed } = buildBoards(roster, teamId);
    if (boards.length === 0 && failed.length === 0) {
      setNote({ tone: "bad", text: "That event only had your team in it -- no opponents to import." });
      return;
    }
    onImported(saveBoards(boards));
    setFailures(failed);
    setReport(failed.length > 0 ? reportText(roster, failed) : "");
    setNote({ tone: "ok", text: summarize(boards.length, failed.length) });
  };

  const downloadReport = () => {
    try {
      const url = URL.createObjectURL(new Blob([report], { type: "text/csv" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `longshanks-${roster?.eventId ?? "event"}-skipped.csv`;
      a.click();
      URL.revokeObjectURL(url);
      setNote({ tone: "ok", text: "Saved the skipped-teams list." });
    } catch {
      setNote({ tone: "bad", text: "This device would not save a file. Copy the text below instead." });
    }
  };

  const copyReport = async () => {
    try {
      await navigator.clipboard.writeText(report);
      setNote({ tone: "ok", text: "Copied the skipped-teams list." });
    } catch {
      setNote({ tone: "bad", text: "Could not reach the clipboard. Select the text below and copy it." });
    }
  };

  const teams = roster ? [...roster.teams].sort((a, b) => a.name.localeCompare(b.name)) : [];

  return (
    <section className="backup">
      <h2>Import from Longshanks</h2>
      <p className="hint">
        Paste an event id or link, choose your team, and get a board for every other
        team in the event with your players already down the side.
      </p>

      <div className="controls">
        <input
          className="grow"
          type="text"
          inputMode="text"
          value={input}
          placeholder="33997 or https://longshanks.org/event/33997/"
          onChange={(e) => setInput(e.target.value)}
          spellCheck={false}
        />
        <button className="primary" onClick={fetchIt} disabled={busy}>
          {busy ? "Fetching…" : "Fetch"}
        </button>
      </div>

      {roster && (
        <div className="controls">
          <label className="field inline grow">
            <span>Your team</span>
            <select value={teamId} onChange={(e) => setTeamId(e.target.value)}>
              <option value="">Select your team…</option>
              {teams.map((t, i) => (
                <option key={t.teamId ?? `i${i}`} value={t.teamId ?? ""}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          <button className="primary" onClick={build} disabled={!teamId}>
            Build boards
          </button>
        </div>
      )}

      {failures.length > 0 && (
        <>
          <p className="hint bad">
            {failures.length === 1 ? "1 team was" : `${failures.length} teams were`} skipped for
            not having five named players. Add them by hand, or download the list to check what
            was missing.
          </p>
          <textarea className="backup-text" value={report} readOnly spellCheck={false} rows={5} />
          <div className="controls">
            <button className="ghost" onClick={downloadReport}>
              Save the list
            </button>
            <button className="ghost" onClick={copyReport}>
              Copy
            </button>
          </div>
        </>
      )}

      {note && <p className={note.tone === "ok" ? "hint" : "hint bad"}>{note.text}</p>}
    </section>
  );
}

/** Plain-language result line, honest about the skips. */
function summarize(built: number, skipped: number): string {
  const boards = built === 1 ? "1 board" : `${built} boards`;
  if (skipped === 0) return `Imported ${boards}. They are in your saved boards.`;
  const teams = skipped === 1 ? "1 team was" : `${skipped} teams were`;
  return `Imported ${boards}; ${teams} skipped (see below).`;
}

/** A small CSV of the skipped teams, so a failed import can be debugged or fixed by hand. */
function reportText(roster: Roster, failures: BuildFailure[]): string {
  const rows = [
    `Longshanks event ${roster.eventId} -- teams skipped during import`,
    "",
    "Team,Reason,Players found",
    ...failures.map(
      (f) => `${csv(f.team)},${csv(f.reason)},${csv(f.members.join("; "))}`,
    ),
  ];
  return rows.join("\n");
}

/** Quote a CSV field only when it needs it, and escape embedded quotes. */
function csv(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}
