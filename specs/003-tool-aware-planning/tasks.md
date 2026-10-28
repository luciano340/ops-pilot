---

description: "Tarefas para tornar Plan-and-Execute ciente das ferramentas disponíveis"
---

# Tasks: Planejamento ciente das ferramentas disponíveis

**Input**: Artefatos de design em `specs/003-tool-aware-planning/`

**Pré-requisitos**: `plan.md`, `spec.md`, `research.md`, `data-model.md` e `contracts/`

**Organização**: Tarefas agrupadas por história de usuário; validar o contrato do planner com testes offline antes de atualizar o prompt.

## Phase 1: Setup

**Purpose**: Nenhuma configuração, dependência ou migração necessária.

## Phase 2: Foundational

**Purpose**: Não há infraestrutura bloqueadora; o catálogo será derivado de ferramentas já fornecidas.

## Phase 3: User Story 1 - Planejar ações com ferramentas disponíveis (Priority: P1) 🎯 MVP

**Goal**: Fazer o planner conhecer as ferramentas e seus argumentos, planejar ações compatíveis e manter o executor responsável por execução e confirmação.

**Independent Test**: Com ferramentas e modelo falsos, verificar que o contexto enviado ao planner contém nomes, descrições e schemas; que uma solicitação suportada gera plano com etapas; que o executor chama a ferramenta esperada e o trace registra ação e observação; e que solicitações sem ferramenta ou sem dados obrigatórios não resultam em sucesso inventado.

### Tests for User Story 1

- [X] T001 [US1] Testar em `tests/agents/test_plan_and_execute.py` que o planner recebe nomes, descrições e schemas das ferramentas injetadas, incluindo schemas e descrições corretos e ausência de ferramentas não fornecidas
- [X] T002 [P] [US1] Testar em `tests/agents/test_plan_and_execute.py` que um plano de solicitação compatível executa a ferramenta esperada e registra plano, ação e observação no trace
- [X] T003 [P] [US1] Testar em `tests/agents/test_plan_and_execute.py` que pedidos informativos e capacidades não disponíveis não produzem alegações de execução, preservando a saída direta sem etapas

### Implementation for User Story 1

- [X] T004 [US1] Montar e serializar o catálogo de ferramentas reais (`name`, `description` e `args_schema`) no contexto do planner em `src/agents/plan_and_execute.py`
- [X] T005 [US1] Atualizar a instrução do planner para transformar ações compatíveis em etapas, distinguir capacidades indisponíveis e não inventar dados obrigatórios em `src/agents/plan_and_execute.py`
- [X] T006 [US1] Executar os testes focados e corrigir eventuais regressões de planejamento, execução, trace, contagem de chamadas e limite de iterações em `tests/agents/test_plan_and_execute.py`

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Executar validações gerais e conferir o quickstart.

- [X] T007 Validar cenários documentados em `specs/003-tool-aware-planning/quickstart.md` e executar Mypy e a suíte pytest completa

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Nenhuma dependência; nenhuma alteração de setup é necessária.
- **Foundational (Phase 2)**: Sem tarefas; não bloqueia a história.
- **User Story 1 (Phase 3)**: Independente e entrega o MVP.
- **Polish (Phase 4)**: Depende da conclusão das alterações da US1.

### User Story Dependencies

- **User Story 1 (P1)**: Única história desta feature; não depende de outra história.

### Within User Story 1

- T001, T002 e T003 são testes no mesmo arquivo e devem ser agrupados sequencialmente antes da implementação.
- T004 e T005 alteram o mesmo arquivo de produção e devem ser feitos sequencialmente.
- T006 depende de T001 a T005; T007 depende de T006.

### Parallel Opportunities

- Não há tarefas de implementação paralelizáveis sem conflito de arquivo.
- A revisão dos cenários dos testes T002 e T003 pode ocorrer em paralelo conceitualmente, mas ambas as edições em `tests/agents/test_plan_and_execute.py` devem ser consolidadas em uma única alteração sequencial.

## Parallel Example: User Story 1

```text
Task: "Verificar o contrato do catálogo de ferramentas no planner em tests/agents/test_plan_and_execute.py"
Task: "Verificar execução de ferramenta e trace para plano não vazio em tests/agents/test_plan_and_execute.py"
```

## Implementation Strategy

### MVP First

1. Criar testes determinísticos com modelo falso para a presença do catálogo e execução de etapa.
2. Atualizar o contexto/instrução do planner sem alterar ferramentas vinculadas ao executor.
3. Executar regressões da estratégia e validar pedidos sem capacidade ou dados suficientes.
4. Executar pytest completo e Mypy.

### Incremental Delivery

- A única história fornece a melhoria completa e pode ser validada sem credenciais de modelo.

## Notes

- Cada tarefa executável inclui caminho de arquivo explícito.
- Não criar heurísticas de palavras-chave, novas ferramentas ou mutações fora do conjunto autorizado.
