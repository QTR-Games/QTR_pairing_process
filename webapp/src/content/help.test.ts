/**
 * The help topics, checked against the two things they depend on.
 *
 * Both checks are for drift, and both fail silently in the app rather than
 * loudly: a `data-help` id with no topic behind it shows "nothing to explain
 * there" on a control that plainly has an explanation, and an anchor that no
 * longer matches a heading drops the reader at the top of a long guide. Neither
 * is visible to anyone writing the change that caused it, which is exactly the
 * kind of breakage worth a test.
 *
 * The source scan is deliberately crude -- a regular expression over the files,
 * not a parse -- in the same spirit as styles.safearea.test.ts. It only has to
 * catch a literal `data-help="..."`, which is how every one of them is written.
 */
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { GUIDES } from "./docs";
import { HELP_TOPICS, helpTopic } from "./help";
import { slug } from "../components/DocViewer";

const SRC = fileURLToPath(new URL("..", import.meta.url));

/** Every .tsx under src/, so a new screen's tags are covered without a list. */
function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const path = join(dir, e.name);
    if (e.isDirectory()) return sourceFiles(path);
    return e.isFile() && e.name.endsWith(".tsx") && !e.name.includes(".test.") ? [path] : [];
  });
}

/** The heading slugs a guide actually offers, the way DocViewer assigns them. */
function anchorsOf(markdown: string): Set<string> {
  const found = new Set<string>();
  for (const line of markdown.split("\n")) {
    const heading = /^#+\s+(.*)$/.exec(line);
    if (heading) found.add(slug(heading[1]));
  }
  return found;
}

describe("help topics", () => {
  it("has one entry per id", () => {
    const ids = HELP_TOPICS.map((t) => t.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("links only to guide sections that exist", () => {
    for (const topic of HELP_TOPICS) {
      if (!topic.guide) continue;
      const guide = GUIDES.find((g) => g.id === topic.guide!.id);
      expect(guide, `${topic.id} names an unknown guide`).toBeTruthy();
      expect(
        anchorsOf(guide!.body).has(topic.guide.anchor),
        `${topic.id} points at "#${topic.guide.anchor}", which is not a heading in ${guide!.title}`,
      ).toBe(true);
    }
  });

  it("covers every data-help tag in the app", () => {
    const tagged = new Set<string>();
    for (const file of sourceFiles(SRC)) {
      for (const m of readFileSync(file, "utf8").matchAll(/data-help="([^"]+)"/g)) {
        tagged.add(m[1]);
      }
    }

    // The tags are real, not a scan that found nothing and passed.
    expect(tagged.size).toBeGreaterThan(5);
    for (const id of tagged) {
      expect(helpTopic(id), `nothing written for data-help="${id}"`).toBeTruthy();
    }
  });
});
