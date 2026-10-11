/*
  The answer to "what does this actually do", for someone who has not typed
  anything in yet.

  Every claim the app makes only becomes visible on a rated board, and a blank
  grid demonstrates none of them. Rather than ask for twenty-five judgements up
  front from someone with no reason to trust the thing yet, this hands them
  three real boards and says what each one is for.

  The list is rendered from the demo definitions rather than written out here,
  so the descriptions on screen cannot drift away from the boards that actually
  load -- and those boards are pinned by `demoBoards.test.ts`, which asserts
  each one still does what its line claims.
*/
import { demoBoards } from "../model/demoBoards";

interface Props {
  /** Install the demo set and open the first board. */
  onLoad: () => void;
}

export function DemoBoards({ onLoad }: Props) {
  const demos = demoBoards();

  return (
    <section className="backup" data-testid="demo-boards">
      <h2>Example boards</h2>
      <p className="hint">
        Three real boards from WTC 2024, already rated, so you can see what the
        app says before entering anything of your own. The ratings are genuine;
        the names are invented.
      </p>

      <ul className="demo-list">
        {demos.map((d) => (
          <li key={d.key}>
            <strong>{d.title}</strong>
            <span className="hint"> &mdash; {d.teaches}</span>
          </li>
        ))}
      </ul>

      <div className="controls">
        <button className="primary" onClick={onLoad}>
          Load the examples
        </button>
      </div>
      <p className="hint">
        They are added to your board list and can be deleted from there at any
        time. Loading them again refreshes the same three rather than making
        copies.
      </p>
    </section>
  );
}
