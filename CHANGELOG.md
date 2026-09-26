# Changelog

Mudanças visíveis para quem usa o plugin, da mais recente para a mais antiga. Cada commit na branch principal é uma versão.

## 2026-09-26

- As evidências do apêndice saem no idioma do relatório: os agentes escrevem afirmações, justificativas e perguntas em aberto nesse idioma, e `reveng.py check` avisa quando alguma escapa para outro idioma.
- Os cards de risco mostram "severidade" e "probabilidade", com a concordância certa.
- `reverse-engineer` entrega o resultado como uma página HTML (`report.html`) em camadas, com componentes visuais (fluxos, diagramas, cards de risco, comparações, linha do tempo), links que abrem o código no VS Code, termos técnicos com tooltip e um apêndice de evidências.
- O início da análise pergunta para quem é o relatório: dev entrando no projeto, tech lead ou leitor não técnico.
- Um novo worker, `reveng-editor`, revisa a linguagem do relatório; o comando `reveng.py lint` aponta jargão do método, termos sem explicação, frases longas e referências quebradas.
- Custo menor: o plano segue os grupos de lentes por tamanho de repositório, um único verificador em repositórios pequenos, verificação por modelo só dos achados de alto impacto e analistas proibidos de executar código.
- O chat termina só com o caminho do relatório e do workspace.

## 2026-09-25

- Adiciona `reverse-engineer` (beta): engenharia reversa de um ou mais repositórios em ondas de subagentes especialistas (recon, analistas por lente, verificador independente, síntese), apoiada em scripts determinísticos (inventário, grafo de dependências entre módulos, métricas do git, sinais de integração, checagem mecânica de evidências).
