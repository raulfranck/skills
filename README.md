# Skills

Skills para agentes de código, organizadas por área e distribuídas como um plugin do Claude Code. Depois de instalado, cada skill aparece como `/raulfranck-skills:<skill>`.

## Instalação

Dentro do Claude Code:

```text
/plugin marketplace add raulfranck/skills
/plugin install raulfranck-skills@raulfranck
```

A partir da versão 2.1.275 dá para fazer os dois passos de uma vez: `/plugin install raulfranck-skills --marketplace raulfranck/skills`.

Pelo terminal:

```bash
claude plugin marketplace add raulfranck/skills
```

```bash
claude plugin install raulfranck-skills@raulfranck
```

### Atualizações

Cada mudança publicada na branch principal é uma nova versão. Para recebê-las automaticamente, ative o auto-update do marketplace: `/plugin`, aba **Marketplaces**, `raulfranck`, **Enable auto-update**. Sem o auto-update, atualize quando quiser:

```bash
claude plugin update raulfranck-skills@raulfranck
```

## Skills

Uma skill **user-invoked** só roda quando você digita o comando. Uma **model-invoked** também pode ser acionada pelo agente quando a tarefa pede.

### Engineering

Skills para trabalho com código.

**User-invoked**

- **[reverse-engineer](./skills/engineering/reverse-engineer/SKILL.md)** (beta): engenharia reversa de um ou mais repositórios com subagentes especialistas em paralelo. Entrega um modelo do sistema baseado em evidências: domínio, arquitetura, integrações, dados, infraestrutura, evolução e riscos. Comando: `/raulfranck-skills:reverse-engineer`. [Documentação](./docs/engineering/reverse-engineer.md).

## Estrutura

```text
.claude-plugin/plugin.json          o plugin raulfranck-skills
.claude-plugin/marketplace.json     o marketplace, com uma entrada: este repositório
agents/                             subagentes usados pelas skills, prefixados pela skill dona
skills/<área>/<skill>/              SKILL.md, arquivos de referência e scripts/
skills/in-progress/                 skills em beta, fora do plugin
skills/misc/                        guardadas e pouco usadas, fora do plugin
skills/deprecated/                  aposentadas
docs/<área>/<skill>.md              documentação de cada skill publicada
.agents/                            referências de manutenção e ADRs
.out-of-scope/                      pedidos recusados de propósito, com o motivo
scripts/check-repo.py               verificação das regras do repositório
```

## Desenvolvimento

Para testar mudanças numa sessão, sem instalar nada, carregue o plugin direto desta pasta:

```bash
claude --plugin-dir .
```

Antes de publicar, rode as verificações. As regras do repositório estão em [CLAUDE.md](./CLAUDE.md).

```bash
claude plugin validate .
```

```bash
python scripts/check-repo.py
```
