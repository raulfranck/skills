# reverse-engineer: an HTML report built from components, with a language pass

The first pilot runs produced a correct but unreadable report: twelve sections of equal weight, finding IDs in the middle of every sentence, vocabulary of the analysis method (lens, Reflexion, convergence) and academic jargon (sensitivity point) in the text, and code references that could not be clicked. Linting the brain-agriculture report found 388 inline IDs, 10 method or jargon terms and 23 specialised terms left unexplained.

## Decision

- **Layers.** The report opens with a section that stands on its own ("O sistema em 2 minutos"), then how it works, risks, where to change, history and open questions. Evidence moves to an appendix the script generates from the digest. See `REPORT-FORMAT.md`.
- **Components, not free HTML.** Agents write Markdown with a fixed set of components (lead, stats, card, risk, callout, flow, compare, timeline, details, diagram) and inline markers for code references, glossary terms and evidence. `reveng.py render` turns that into one self-contained HTML page. Agents never write HTML, so every report looks the same and stays valid.
- **The reader is chosen up front.** Scope asks whether the report is for a developer joining the project, a tech lead or a non-technical reader; the format and the lint adapt to it.
- **Language checked twice.** `reveng.py lint` flags method terms, jargon, inline IDs, unexplained specialised terms, long sentences and paragraphs, broken code references and unknown evidence IDs. A dedicated `reveng-editor` (sonnet) rewrites the draft against `STYLE.md` and the lint report until it is clean; the synthesizer keeps its effort for understanding.
- **Terms teach.** `assets/glossary.json` holds curated definitions of engineering terms, each marked basic or advanced. Marked terms get a tooltip, and the page ends with the terms it used.
- **Code references open the file.** A path such as `src/x.ts:12` becomes a `vscode://file/...:12` link when the file exists.
- **The chat stays quiet.** The orchestrator's last message is the path to `report.html` and the workspace.

## Consequences

- Diagrams use Mermaid from a CDN; offline, the page shows the diagram source instead.
- Findings stay in English and show as such in the appendix; only the report body is in the reader's language.
- The editor adds one sonnet run to every analysis.
