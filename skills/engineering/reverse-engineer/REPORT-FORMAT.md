# Report format

The report is one Markdown file written with the components below. `reveng.py render` turns it into `report.html` at the workspace root: layout, table of contents, links to code, term tooltips, a "Termos usados" section and the evidence appendix are all added by the script. Write only the content.

- The synthesizer writes `synthesis/report.draft.md`.
- The editor turns it into `synthesis/report.md`.
- Language rules live in [STYLE.md](STYLE.md); they bind both.

## Reader

`manifest.audience` sets how deep each part goes:

| Audience | Who | Adjust |
|---|---|---|
| `dev` | a developer joining the project | full depth; code paths everywhere they help |
| `lead` | a tech lead or architect deciding priorities | sections 1, 3 and 4 carry the weight; "Como funciona" stays short |
| `non-technical` | product or management | plain language only; code paths only in the "Onde" line of risks; every technical term gets a tooltip; skip "Histórico do projeto" |

## Structure

Section titles below are for `pt-BR`; translate them for other report languages. Keep the order. Target 1,500 to 3,000 words in total.

`# <system name>` (one H1, used as the page title)

### 1. `## O sistema em 2 minutos`

Complete on its own: a reader who stops here knows what the system is, how it works and the three things that matter most.

1. `::: lead`: 2 to 4 sentences. What the system does, for whom, and its shape (for example "uma API NestJS e um front-end React sobre PostgreSQL").
2. `::: stats`: 4 to 6 numbers that frame the system (lines of code, endpoints, entities, integrations, contributors).
3. `::: flow`: the main flow in 3 to 6 steps.
4. Three `::: card` blocks under a `### O que você precisa saber` heading: the three facts with the most consequence, each with a tone.
5. `### Por onde começar a ler o código`: an ordered list of 3 to 5 files, each with a reason of a few words.

### 2. `## Como funciona`

- `### Partes do sistema`: one `::: diagram` (Mermaid `flowchart`) of the deployable units, modules and external systems, plus a short table: part, what it does, where it lives.
- `### Fluxos principais`: one `::: flow` per critical flow (at most 4). Put failure paths and edge cases in a `::: details` under each flow.
- `### Dados e regras de negócio`: a table of the main entities (what each is, key fields), then a table of business rules (rule, where it is enforced, weak spot). A Mermaid `erDiagram` helps when there are 4 or more entities.
- `### Integrações`: a table of every system it talks to (with whom, how, what happens when it fails). Omit when there is nothing beyond the database.
- `### O que a documentação diz e o que o código faz`: one `::: compare` with `left="A documentação diz"` and `right="O código faz"`. Omit when they agree.

### 3. `## Riscos e prioridades`

- At most 5 `::: risk` blocks, most severe first, each with `severity` and `likelihood` (`alta`, `média`, `baixa`) and three bold labels in its body: **O que acontece**, **Onde**, **O que fazer**.
- `### Outros pontos de atenção`: a table (ponto, impacto, onde) for the remaining risks.
- One `::: callout tone="ok" title="O que está bem resolvido"` listing what the design handles well.

### 4. `## Por onde mudar`

At most 5 `::: card` blocks for the likeliest changes: where to start, what else moves, what could break.

### 5. `## Histórico do projeto`

A `::: timeline` of the phases, then short paragraphs on where change concentrates (the [[hotspot]] files) and how knowledge is spread.

### 6. `## Perguntas em aberto`

- For each focus question: a `###` with the question, then the answer, or what is missing to answer it.
- The open questions that matter, each with who or what could answer it.
- One `::: details title="Próximos passos da análise"` listing up to 10 questions worth another targeted pass.

## Components

Blocks open with `::: name attributes` and close with `:::` on its own line. Their bodies are Markdown, except where noted.

| Component | Use it for | Body |
|---|---|---|
| `::: lead` | the opening summary | Markdown |
| `::: stats` | key numbers | list items `- value \| label` |
| `::: card title="..." tone="risk\|warn\|ok\|info\|neutral"` | one idea with a title; consecutive cards form a grid | Markdown |
| `::: risk title="..." severity="alta" likelihood="média"` | a risk | Markdown with **O que acontece**, **Onde**, **O que fazer** |
| `::: callout tone="..." title="..."` | a highlighted note | Markdown |
| `::: flow title="..."` | a sequence of steps | list items `- Step \| what happens` |
| `::: compare title="..." left="..." right="..."` | two sides side by side | list items `- left \| right` |
| `::: timeline` | history | list items `- when \| what` |
| `::: details title="..."` | depth the reader may skip | Markdown |
| `::: diagram title="..."` | a diagram | Mermaid source |

Plain Markdown also works: headings, paragraphs, lists, tables, `**bold**`, `*italic*`, `[links](https://...)`, `> quotes` and fenced code.

Example:

```markdown
::: risk title="Todos os dados somem a cada reinício" severity="alta" likelihood="alta"
**O que acontece:** o script de inicialização apaga o banco inteiro antes de subir a API. Qualquer restart ou deploy zera produtores, fazendas e safras. ^[A3-012 B2-009]

**Onde:** `apps/backend/entrypoint.sh:5`

**O que fazer:** remover o reset ou condicioná-lo a uma variável que só exista em desenvolvimento.
:::
```

## Inline markers

| Marker | Renders as |
|---|---|
| `` `apps/backend/entrypoint.sh:5` `` | a link that opens the file at that line in VS Code. Use `repo:path:line` when there is more than one repository. |
| `[[idempotência]]` | the word with a tooltip from the glossary (`assets/glossary.json`) |
| `[[termo\|definição curta]]` | a tooltip with your definition, for a term the glossary lacks |
| `^[A1-003 B2-009]` | a small evidence marker linking to the appendix. Put it at the end of a sentence, a list item or a card, with at most 3 IDs. |

Every claim that matters carries an evidence marker. IDs appear nowhere else in the text.
