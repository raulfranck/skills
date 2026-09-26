# Report style

Write the report the way a senior engineer writes a system overview for their own team: technical and precise, in plain language, about this system and nothing else. The reader wants to understand the system and decide what to do; how the analysis was carried out does not interest them.

`reveng.py lint` checks the mechanical parts of these rules. Everything else depends on the writer.

## Voice

- **Lead with the consequence.** Say what happens, then why. "Um restart apaga todos os dados" comes before the name of the script that does it.
- **Be concrete.** Name the file, the function, the number. "26 endpoints sem autenticação" beats "a superfície da API está exposta".
- **One idea per paragraph**, at most about 110 words. Sentences of at most about 40 words.
- **Use the reader's language.** Keep established technical English where Brazilian engineers use it (deploy, build, commit, endpoint, pull request, cache, bug); translate everything else.

## Terms

| Kind | Examples | Rule |
|---|---|---|
| Everyday engineering terms | API, banco de dados, endpoint, deploy, teste, módulo, dependência | Use freely. |
| Specialised terms | idempotência, condição de corrida, invariante, hotspot, fator ônibus, CORS, SSRF | Use them when they are the right word, and wrap the first occurrence in `[[...]]` so it gets a tooltip. For the `non-technical` reader, wrap every technical term. |
| Terms of the analysis method | finding, lente, onda, recon, digest, Reflexion, convergência | Never. Describe the fact instead. |
| Academic jargon | ponto de sensibilidade, utility tree, connascence, subdomínio genérico | Never. Say the same thing in ordinary words. |

A term missing from the glossary gets its own short definition: `[[bulkhead|isolar recursos por cliente para que a falha de um não derrube os outros]]`.

## Certainty in words

The evidence appendix records how sure each claim is. Let the wording match it, without labels:

| Certainty | Wording |
|---|---|
| fact | a plain statement |
| inference | "provavelmente", "tudo indica que" |
| hypothesis | "pode", "vale verificar se" |
| unknown | a question, with who or what could answer it |

## Evidence markers

Put `^[...]` at the end of the sentence, list item or card it supports, never in the middle of a sentence, with at most 3 IDs. A paragraph of connected claims can share one marker at its end.

## Leave out

- The story of the analysis: counts of findings, verification statistics, which worker found what, refuted hypotheses.
- Hedging that adds nothing ("é importante notar que", "vale ressaltar").
- Restating the same risk in several sections. Say it once, where it belongs, and link to it.

## Before and after

| Before | After |
|---|---|
| O invariante de unicidade de página foi refutado: os geradores concatenam `config.pages` com a varredura de `contentDir` sem deduplicação [A1-006]. | Uma mesma página pode aparecer duas vezes no `llms.txt`: se ela existe no build e também como `.md` na pasta de conteúdo, os geradores juntam as duas listas sem remover repetidas. ^[A1-006] |
| **Ponto de sensibilidade.** A existência do bloco `DROP SCHEMA` é a única decisão que determina se o sistema é armazenamento durável ou ambiente efêmero [B2-017]. | Uma única linha decide se o banco guarda dados de verdade: o `DROP SCHEMA` em `entrypoint.sh`. Enquanto ela existir, todo deploy começa com o banco vazio. ^[B2-017] |
| *Convergência*: o grafo de entidades declarado no recon corresponde exatamente às relações TypeORM [A3-005]. | As relações entre as entidades são exatamente as que o README descreve. ^[A3-005] |
| Fator de bus 1: cada módulo é 100% de um único autor [A3-022]. | Todo o código foi escrito por uma pessoa só, então hoje o [[fator ônibus]] é 1: sem ela, ninguém conhece o sistema por dentro. ^[A3-022] |
| Os 26 endpoints [...] estão abertos a qualquer chamador que alcance a rede [A2-002][A2-003][B2-012][B2-022]. | Nenhum dos 26 endpoints pede login, e o [[CORS]] aceita qualquer origem: quem alcançar a API pode ler e apagar todos os produtores, inclusive seus CPFs. ^[A2-002 B2-012 B2-022] |
