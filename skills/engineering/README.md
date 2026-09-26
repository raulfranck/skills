# Engineering

Skills para trabalho com código, parte do plugin `raulfranck-skills`.

## User-invoked

Só rodam quando você digita o comando (`disable-model-invocation: true`).

- **[reverse-engineer](./reverse-engineer/SKILL.md)** (beta): engenharia reversa de um ou mais repositórios com subagentes especialistas em paralelo, gerando um modelo do sistema baseado em evidências. Comando: `/raulfranck-skills:reverse-engineer`.

## Model-invoked

Nenhuma ainda.

## Subagentes

Os workers das skills desta área ficam em [agents/](../../agents/), com o prefixo da skill dona:

- `reveng-*`: workers do `reverse-engineer` (recon, analyst, verifier, synthesizer, runtime).
