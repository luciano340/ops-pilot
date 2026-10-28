# Implementation Plan: Planejamento ciente das ferramentas disponíveis

**Branch**: `003-tool-aware-planning` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-tool-aware-planning/spec.md`

## Summary

Atualizar o prompt de planejamento do Plan-and-Execute para fornecer catálogo das ferramentas realmente entregues à estratégia — nomes, descrições e schemas de argumentos — e exigir que ações compatíveis sejam decompostas em etapas executáveis. Instruções adicionais distinguem operações suportadas, dados obrigatórios ausentes e pedidos sem ferramenta correspondente. Executor segue limitado a uma chamada de ferramenta por etapa e só registra sucesso após observação.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Django 6.1, Pydantic 2, `langchain-core`, `langchain-openai`, `langgraph`

**Storage**: PostgreSQL no Compose e SQLite local; sem alterações de persistência.

**Testing**: Pytest, pytest-django e Mypy em modo estrito. Testes usam modelo falso sem rede ou credenciais.

**Target Platform**: Aplicação Django/CLI em Windows/Linux e contêiner Linux.

**Project Type**: Aplicação Django com estratégias de agente e ferramentas operacionais.

**Performance Goals**: Não adicionar chamadas ao modelo; manter a contagem existente de planejamento, execução e replanejamento.

**Constraints**: Catálogo derivado apenas das ferramentas entregues à estratégia. Não inventar campos obrigatórios, capacidades, resultados nem confirmação de ações. Preservar execução de no máximo uma ferramenta por etapa, limites de iteração e trace.

**Scale/Scope**: Uma estratégia Plan-and-Execute e suas ferramentas fornecidas. Sem novas ferramentas de operações, sem modificar ReAct, CLI, schemas de persistência ou UI.

## Constitution Check

| Gate | Resultado | Evidência / decisão |
|---|---|---|
| Arquitetura em camadas e domínio sem I/O | PASS | Mudança limitada à orquestração do agente; nenhum I/O de domínio novo. |
| Fronteiras validadas e contratos explícitos | PASS | O schema real de cada ferramenta é descrito ao planejador; argumentos continuam validados pela ferramenta na execução. |
| Segurança de tipos e qualidade | PASS | Acesso ao schema e serialização do catálogo terão tipos explícitos; adicionar testes de planejamento e executar pytest/Mypy. |
| Acesso async a dados e eficiência | PASS | Reutiliza a execução async existente; não adiciona fan-out, queries ou chamadas de modelo. |
| Segurança por padrão | PASS | O planejador não poderá alegar execução sem observação. Não há expansão de permissões e nenhuma ferramenta é adicionada. |
| Spec Kit e aprovação humana | PASS | Especificação aprovada antes desta fase de design. |

## Research Summary

- LangChain expõe argumentos de ferramentas por schema (`args_schema`) e descrição; as ferramentas do projeto são `StructuredTool` com schemas Pydantic e descrições registradas.
- Decisão: montar o catálogo a partir dos objetos `BaseTool` recebidos, usando nome, descrição e schema de argumentos, serializado como JSON no contexto do planejamento.
- Decisão: alterar apenas a orientação do planner e o contexto enviado; o executor continua a receber exatamente o conjunto de ferramentas já autorizado via `bind_tools`.
- Alternativa rejeitada: selecionar uma ferramenta usando heurística local de palavras-chave. Não cobre solicitações variadas e duplicaria o entendimento semântico do modelo.
- Alternativa rejeitada: executar ferramenta diretamente no planner. Isso misturaria decomposição e ação, eliminaria o passo de aprovação operacional do executor e dificultaria o trace existente.
- Para requisições com campos obrigatórios ausentes, o planner pode primeiro buscar contexto com ferramentas de leitura ou retornar pergunta objetiva; não deve inventar severidade, serviço ou outros valores.
- Consulte [research.md](./research.md) para detalhes e referência documental.

## Project Structure

### Documentation (this feature)

```text
specs/003-tool-aware-planning/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── planner-tool-context.md
└── tasks.md
```

### Source Code (repository root)

```text
src/agents/
└── plan_and_execute.py

tests/agents/
└── test_plan_and_execute.py
```

**Structure Decision**: Manter toda a lógica na estratégia Plan-and-Execute existente e seus testes offline. Não adicionar módulos, dependências ou ferramentas operacionais novas.

## Complexity Tracking

Nenhuma violação da constituição ou camada/projeto adicional precisa de justificativa.
