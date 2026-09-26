## O que faz

`reverse-engineer` faz a engenharia reversa de um ou mais repositórios e entrega um modelo do sistema: para que ele serve, como está organizado, como as partes conversam, onde fica o estado, como roda, como evoluiu e onde estão os riscos. O trabalho é dividido entre subagentes especialistas. Cada um aplica uma ou mais **lentes** (domínio, dados, integrações, estrutura, infraestrutura, evolução, fluxos, risco) sobre uma base determinística que scripts produzem antes: inventário, grafo de dependências entre módulos, métricas do histórico git e sinais de integração entre repositórios.

Nenhuma afirmação chega ao modelo final sem evidência. Os agentes registram **achados** com grau de certeza e citação de arquivo e linha. Depois, um script confere cada citação e um verificador independente julga se a evidência sustenta a afirmação. O que não se sustenta é rebaixado ou descartado antes da síntese.

## Quando usar

Você aciona digitando `/raulfranck-skills:reverse-engineer`. O agente não dispara essa skill sozinho, porque ela coloca vários subagentes para trabalhar.

| Situação | Use |
|---|---|
| Chegou numa empresa ou num time e precisa entender um ou vários repositórios | `reverse-engineer` |
| Vai contribuir com um projeto open source e quer o mapa antes de mexer | `reverse-engineer`, com perguntas de foco |
| Due diligence técnica, auditoria de arquitetura, preparação de uma refatoração grande | `reverse-engineer` |
| Uma pergunta pontual sobre um arquivo, ou um bug específico | uma conversa comum com o agente: mais rápida e mais barata |

## Pré-requisitos

- O plugin `raulfranck-skills` instalado: os subagentes vêm com ele.
- Python 3.9 ou mais novo e git no PATH.
- Cada execução grava em `./.reveng/<data>-<nome>/` na pasta onde a sessão está. Se essa pasta for um repositório git, o workspace é adicionado ao `.git/info/exclude`. Os repositórios analisados não são alterados.
- Os subagentes gravam arquivos no workspace e rodam comandos git e python. Num modo de permissão restritivo você vai aprovar muitas ações; o modo auto ou "aceitar edições" deixa a execução fluir.

## Como uma execução acontece

| Fase | Quem | Resultado |
|---|---|---|
| Escopo | você | repositórios, para quem é o relatório, perguntas de foco, execução local opcional, idioma |
| Reconhecimento | scripts + um agente leve (haiku) por repositório | inventário, dependências, métricas do git, sinais de integração, listas de leitura por lente e as afirmações da documentação registradas como hipóteses |
| Plano | orquestrador, com a sua aprovação | tarefas dimensionadas pelo tamanho de cada repositório, com contagem de agentes por modelo |
| Onda A | analistas (sonnet) em paralelo | lentes independentes: domínio e dados, integrações, estrutura, infraestrutura, evolução |
| Onda B | analistas (sonnet) | fluxos críticos de ponta a ponta e riscos |
| Verificação | script + verificadores (sonnet) | cada citação conferida; achados confirmados, rebaixados ou refutados |
| Síntese | sintetizador (opus) | o rascunho do relatório |
| Revisão | script + editor (sonnet) | o texto reescrito para o leitor escolhido, sem jargão do método e com os termos técnicos explicados |
| Relatório | script | `report.html` na pasta do workspace |

Se a sessão cair no meio, a execução continua de onde parou.

## O relatório

Uma página HTML única, que abre em qualquer navegador:

- **Em camadas:** a primeira seção explica o sistema em dois minutos; as seguintes aprofundam o funcionamento, os riscos, por onde mudar, o histórico e as perguntas em aberto.
- **Componentes visuais:** fluxos passo a passo, diagramas, cards de risco com impacto e probabilidade, comparação entre o que a documentação diz e o que o código faz, e linha do tempo.
- **Termos explicados:** passe o mouse sobre um termo sublinhado para ver a definição. A página termina com a lista dos termos usados, então ela também serve para aprender o vocabulário de engenharia.
- **Código a um clique:** cada caminho de arquivo abre o arquivo na linha certa no VS Code.
- **Evidências:** cada marcador numerado leva ao trecho de código que sustenta a afirmação, no apêndice.

O relatório se adapta ao leitor escolhido no início: um dev entrando no projeto, um tech lead decidindo prioridades ou um leitor não técnico.

## Graus de certeza

| Grau | Significa |
|---|---|
| fato | a citação mostra diretamente |
| inferência | decorre de fatos por um argumento curto e explícito |
| hipótese | plausível, ainda não verificada; afirmações da documentação começam aqui |
| desconhecido | pergunta que os repositórios não respondem |

## Perguntas comuns

**Quanto custa?**

O plano mostra quantos agentes vão rodar, e com qual modelo, antes de qualquer análise começar. Como referência inicial, ainda a calibrar com execuções piloto: um repositório pequeno usa 7 execuções de agente (1 haiku, 5 sonnet, 1 opus) e um médio, cerca de 11. As contagens pesadas (dependências, histórico git, checagem de citações) ficam com os scripts e não gastam tokens.

**Posso usar em código privado da empresa?**

Os scripts rodam na sua máquina e o workspace fica na sua pasta. Os agentes enviam trechos de código ao modelo, como qualquer sessão do Claude Code. Siga a política da sua empresa para uso de IA com código.

**A sessão caiu no meio. Perdi tudo?**

Não. Rode `/raulfranck-skills:reverse-engineer --resume <workspace>`: o status aponta as tarefas sem saída, e só elas são refeitas.

**Por que o relatório chama de hipótese algo que parece óbvio?**

Sem uma citação que mostre a afirmação diretamente, ela não sobe para fato. É isso que torna o relatório confiável, e a seção de perguntas em aberto diz o que falta para resolver cada hipótese importante.

**Preciso deixar o projeto rodar?**

Não, é opcional. Quando você autoriza, um agente clona o repositório numa cópia isolada dentro do workspace e roda só os comandos locais de instalação, build e testes que o próprio repositório documenta. Deploy, publicação e comandos de infraestrutura ficam de fora.

## Está funcionando se

- O plano chega antes de qualquer agente de análise rodar, com a contagem por modelo.
- A primeira seção do relatório, sozinha, explica o que o sistema é e o que mais importa saber.
- Cada afirmação importante tem um marcador que leva ao trecho de código que a sustenta.
- O texto não traz jargão da análise nem siglas sem explicação.
- Cada pergunta de foco aparece respondida ou marcada como aberta, com o que falta para respondê-la.

## Onde se encaixa

Standalone: use ao chegar num sistema que você ainda não conhece, antes de planejar mudanças. O relatório e as evidências verificadas servem de base para o que vier depois: planejar uma refatoração, escrever a documentação do sistema ou escolher por onde começar uma contribuição.
