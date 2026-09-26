# Writing docs pages

Every shipped skill has a human-facing docs page at `docs/<area>/<skill>.md`, written in Brazilian Portuguese. The page is not the skill and not a copy of `SKILL.md`: it orients a reader around one skill so they know what it does, when to reach for it and where it sits among the others. Skills in `in-progress/`, `misc/` and `deprecated/` get no page.

Create or re-sync the page whenever a skill is added, renamed, moved between areas, or changes behaviour. A rename or move moves the page too.

## Page structure

Keep this order. The fixed frame (**O que faz**, **Quando usar**, **Onde se encaixa**) appears on every page; the other sections appear only when the skill has something to say in them.

1. `## O que faz`: one or two paragraphs. Lead with the skill's job in one sentence, then state its defining constraint, the one fact that makes it behave differently from the obvious default, as a plain sentence.
2. `## Quando usar`: the invocation mode (typed by you, or also fired by the agent) and the trigger boundary. When a sibling skill is easy to confuse with it, give a table of situation and skill.
3. `## Pré-requisitos`: only when something must be in place (plugin, tools, a workspace it writes, permissions).
4. One to three free sections in the skill's own vocabulary that make it click: the loop it runs, the artifact it produces. Surface the skill's leading words.
5. `## Perguntas comuns`: real questions, bold, answered below. Plainly obvious questions are allowed while no real ones exist yet; never pad.
6. `## Está funcionando se`: signals the reader can check without opening `SKILL.md`.
7. `## Onde se encaixa`: the skill's role (standalone, chain step, periodic) and its one or two neighbours, each with a reason.

## Conventions

- Explain the why, not the process: the reader choosing a tool does not need the runbook.
- Put choices in tables or lists, never in a paragraph.
- Keep links relative inside the repository.
