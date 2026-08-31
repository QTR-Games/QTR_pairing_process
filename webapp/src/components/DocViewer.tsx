/*
  Renders one bundled guide as formatted, scrollable text.

  The guides are Markdown and lean on GFM tables heavily, so this is
  react-markdown with the gfm plugin rather than anything hand-rolled. Two kinds
  of link inside a guide need help, because the app runs from a file:// origin
  with no server behind it and nothing to resolve a relative path against:

    - in-page "#anchor" links (the User's Guide table of contents). Headings are
      given GitHub-compatible slug ids here so those anchors have somewhere to
      land, and a click scrolls to them rather than trying to navigate.
    - cross-doc ".md" links. When one points at a sibling guide we switch this
      viewer to it and stay in-app and offline; anything else (the legacy
      Tkinter docs) opens on GitHub in a new tab so a live round in this tab is
      never navigated away from.

  Absolute http(s) links always open in a new tab for the same reason.
*/
import type { ReactNode } from "react";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { GUIDES } from "../content/docs";

const GITHUB_DOCS_BASE =
  "https://github.com/QTR-Games/QTR_pairing_process/blob/main/docs";

/*
  GitHub's heading-slug rule, close enough for our headings: lowercase, drop
  everything that is not a word character, hyphen or space, then turn spaces
  into hyphens. Runs of spaces become runs of hyphens on purpose -- "backup &
  restore" is "backup--restore" on GitHub too -- so the ids match the "#anchor"
  targets the docs were written against.
*/
export function slug(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^\w\- ]+/g, "")
    .replace(/ /g, "-");
}

/** The plain text under a rendered node, for slugging a heading. */
function textOf(node: ReactNode): string {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  const el = node as { props?: { children?: ReactNode } };
  return el.props?.children != null ? textOf(el.props.children) : "";
}

function scrollToId(id: string): void {
  const el = document.getElementById(id);
  // jsdom leaves scrollIntoView undefined; guarding keeps the tests honest.
  if (el && typeof el.scrollIntoView === "function") {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

type Level = "h1" | "h2" | "h3" | "h4" | "h5" | "h6";

function heading(Tag: Level) {
  return function Heading({ children }: { children?: ReactNode }) {
    return <Tag id={slug(textOf(children))}>{children}</Tag>;
  };
}

export interface DocViewerProps {
  markdown: string;
  /** Switch to a sibling guide when the current one links to it. */
  onOpenGuide: (id: string) => void;
}

export function DocViewer({ markdown, onOpenGuide }: DocViewerProps) {
  const components: Components = {
    h1: heading("h1"),
    h2: heading("h2"),
    h3: heading("h3"),
    h4: heading("h4"),
    h5: heading("h5"),
    h6: heading("h6"),
    a({ href, children }) {
      const url = href ?? "";

      if (url.startsWith("#")) {
        return (
          <a
            href={url}
            onClick={(e) => {
              e.preventDefault();
              scrollToId(url.slice(1));
            }}
          >
            {children}
          </a>
        );
      }

      if (!/^https?:\/\//i.test(url)) {
        // A relative link. Its filename is the part before any anchor or query.
        const file = url.split(/[#?]/)[0].split("/").pop() ?? "";
        const sibling = GUIDES.find((g) => g.href.endsWith(file));
        if (sibling) {
          return (
            <a
              href={sibling.href}
              onClick={(e) => {
                e.preventDefault();
                onOpenGuide(sibling.id);
              }}
            >
              {children}
            </a>
          );
        }
        const external = file ? `${GITHUB_DOCS_BASE}/${file}` : url;
        return (
          <a href={external} target="_blank" rel="noreferrer">
            {children}
          </a>
        );
      }

      return (
        <a href={url} target="_blank" rel="noreferrer">
          {children}
        </a>
      );
    },
  };

  return (
    <div className="doc">
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </Markdown>
    </div>
  );
}
