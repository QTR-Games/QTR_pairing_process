# GronkSoft shared platform

KLIK KLAK is one of two GronkSoft apps that had independently grown the same
features — splash screen, Ko-fi button, bug reporting, wireless install. That
shared behaviour now lives in a package rather than being copied:

**[QTR-Games/Gronksoft-Core](https://github.com/QTR-Games/Gronksoft-Core)** —
see [`docs/platform.md`](https://github.com/QTR-Games/Gronksoft-Core/blob/main/docs/platform.md)
for the full design note.

The decisions are recorded there rather than here on purpose. Keeping a second
copy in each app repository would recreate exactly the drift the core package
exists to prevent.

## What this repository needs to know

- **Core owns behaviour; this app owns its identity.** `webapp/src/brand.ts` is
  where KLIK KLAK's name, logo and links live, and it is what gets passed into
  core. Nothing app-specific belongs in core.
- **Core exports logic, not markup.** This app's CSS and Jack Tracker's Tailwind
  are incompatible, so core ships hooks and schemas — `useSplash()`, not
  `<Splash/>`. The JSX in `webapp/src/components/` stays here.
- **`.github/ISSUE_TEMPLATE/bug_report.yml` becomes generated output.** Once core
  is adopted, edit the schema in the core repository and regenerate; hand edits
  will be reverted.
- **`Log a bug` is currently broken.** `LINKS.bugs` points at `issues/new` on
  this now-private repository, which 404s for anyone without access. The fix,
  and why it needs a small piece of non-GitHub runtime, is in the design note.
  Deferred deliberately while the author is the only person filing bugs.

## Adopting core

Not yet done. When it happens it should be one small, low-risk change: take the
Ko-fi URL and the splash timing from the package, leaving everything visual
alone.

```jsonc
// webapp/package.json
"dependencies": {
  "@gronksoft/core": "github:QTR-Games/Gronksoft-Core#v0.1.0"
}
```
