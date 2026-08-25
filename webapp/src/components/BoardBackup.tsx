import { useRef, useState } from "react";
import {
  BackupError,
  applyBackup,
  backupFilename,
  parseBackup,
  serializeBackup,
  type ImportMode,
} from "../model/backup";
import type { Board } from "../model/board";

interface Props {
  /** Called with the restored list so the app re-renders against it. */
  onRestored: (boards: Board[]) => void;
}

type Note = { tone: "ok" | "bad"; text: string } | null;

/**
 * Save a copy of every board, and put one back.
 *
 * Deliberately offers three ways out rather than one. A file download is the
 * obvious route and is what a laptop will use, but this app's main home is an
 * Android WebView, where an anchor with `download` is the least reliable thing
 * on the page -- it can silently do nothing. So the clipboard and a visible
 * textarea sit beside it, and at least one of the three works everywhere. The
 * textarea is also the honest one: the backup is not a black box, it is text,
 * and someone worried about losing a season of boards can see them in it.
 *
 * Restore accepts a pasted document as well as a chosen file, for the same
 * reason in reverse -- a file picker inside a WebView may not reach the place
 * the backup actually ended up, but paste always lands.
 */
export function BoardBackup({ onRestored }: Props) {
  const [text, setText] = useState("");
  const [note, setNote] = useState<Note>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const showBackup = () => {
    setText(serializeBackup());
    setNote({ tone: "ok", text: "This is your backup. Copy it, or save the file." });
  };

  const download = () => {
    const json = serializeBackup();
    try {
      const url = URL.createObjectURL(new Blob([json], { type: "application/json" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = backupFilename();
      a.click();
      URL.revokeObjectURL(url);
      setNote({ tone: "ok", text: `Saved as ${backupFilename()}.` });
    } catch {
      // Fall back to showing it, which is always available.
      setText(json);
      setNote({ tone: "bad", text: "This device would not save a file. Copy the text instead." });
    }
  };

  const copy = async () => {
    const json = serializeBackup();
    setText(json);
    try {
      await navigator.clipboard.writeText(json);
      setNote({ tone: "ok", text: "Copied. Paste it somewhere you keep things." });
    } catch {
      setNote({ tone: "bad", text: "Could not reach the clipboard. Select the text and copy it." });
    }
  };

  const restore = (raw: string, mode: ImportMode) => {
    if (!raw.trim()) {
      setNote({ tone: "bad", text: "Paste a backup first, or choose a file." });
      return;
    }
    try {
      const result = applyBackup(parseBackup(raw), mode);
      onRestored(result.boards);
      setNote({ tone: "ok", text: describe(result.added, result.updated, result.skipped) });
    } catch (e) {
      setNote({
        tone: "bad",
        text: e instanceof BackupError ? e.message : "That backup could not be read.",
      });
    }
  };

  const chooseFile = (file: File | undefined) => {
    if (!file) return;
    file
      .text()
      .then((raw) => {
        setText(raw);
        restore(raw, "merge");
      })
      .catch(() => setNote({ tone: "bad", text: "That file could not be opened." }));
  };

  return (
    <section className="backup">
      <h2>Save your boards</h2>
      <p className="hint">
        Boards live on this device only. Installing a new build can clear them, so keep a
        copy somewhere else.
      </p>

      <div className="controls">
        <button className="primary" onClick={download}>
          Save a copy
        </button>
        <button className="ghost" onClick={copy}>
          Copy
        </button>
        <button className="ghost" onClick={showBackup}>
          Show
        </button>
      </div>

      <textarea
        className="backup-text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste a backup here to restore it."
        spellCheck={false}
        rows={5}
      />

      <div className="controls">
        <button className="ghost" onClick={() => fileInput.current?.click()}>
          Choose a file
        </button>
        <button className="ghost" onClick={() => restore(text, "merge")}>
          Restore
        </button>
        <button
          className="ghost"
          onClick={() => {
            // Destructive, and the only button here that can lose anything.
            if (confirm("Replace every board on this device with the backup?")) {
              restore(text, "replace");
            }
          }}
        >
          Replace all
        </button>
      </div>

      <input
        ref={fileInput}
        type="file"
        accept="application/json,.json"
        hidden
        onChange={(e) => {
          chooseFile(e.target.files?.[0]);
          // Let the same file be chosen twice in a row.
          e.target.value = "";
        }}
      />

      {note && <p className={note.tone === "ok" ? "hint" : "hint bad"}>{note.text}</p>}
    </section>
  );
}

/** Says plainly when a restore changed nothing, rather than implying it worked. */
function describe(added: number, updated: number, skipped: number): string {
  if (added === 0 && updated === 0) {
    return skipped > 0
      ? "Everything in that backup was already here, and nothing was older. No change."
      : "That backup had no boards in it.";
  }
  const parts: string[] = [];
  if (added) parts.push(`${added} restored`);
  if (updated) parts.push(`${updated} updated`);
  if (skipped) parts.push(`${skipped} already current`);
  return `${parts.join(", ")}.`;
}
