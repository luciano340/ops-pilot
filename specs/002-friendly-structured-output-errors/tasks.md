---

description: "Tarefas para apresentar mensagens amigáveis para saídas estruturadas inválidas"
---

# Tasks: Mensagens amigáveis para saída estruturada inválida

**Input**: Artefatos de design em `specs/002-friendly-structured-output-errors/`

**Pré-requisitos**: `plan.md`, `spec.md`, `research.md`, `data-model.md` e `contracts/`

**Organização**: Tarefas agrupadas por história de usuário; testes offline precedem a implementação.

## Phase 1: Setup

**Purpose**: Nenhuma configuração ou dependência nova é necessária.

## Phase 2: Foundational

**Purpose**: Não há infraestrutura compartilhada bloqueadora; a implementação está contida na história US1.

## Phase 3: User Story 1 - Entender falhas de saída do modelo (Priority: P1) 🎯 MVP

**Goal**: Converter apenas respostas estruturadas inválidas em um erro tipado com mensagem em inglês e apresentá-lo no CLI sem traceback.

**Independent Test**: Simular respostas inválidas no planejamento e replanejamento, verificar o erro e a mensagem; chamar a arena via Django e verificar que `CommandError` apresenta a mesma mensagem. Confirmar que erros não relacionados continuam distintos.

### Tests for User Story 1

- [X] T001 [US1] Adicionar testes offline para validar que respostas inválidas de `Plan` e `PlanReview` são convertidas para o erro tipado e não expõem o payload em `tests/agents/test_plan_and_execute.py`
- [X] T002 [P] [US1] Adicionar teste do comando Django para validar a mensagem amigável e ausência de traceback em `tests/agents/test_arena_command.py`

### Implementation for User Story 1

- [X] T003 [US1] Definir `StructuredOutputError` e a mensagem pública estável em inglês em `src/agents/errors.py`
- [X] T004 [US1] Traduzir somente `pydantic.ValidationError` emitidas pelas respostas estruturadas do planejador e replanejador para `StructuredOutputError` em `src/agents/plan_and_execute.py`
- [X] T005 [US1] Converter `StructuredOutputError` para `CommandError` sem mascarar outras falhas em `src/agents/management/commands/arena.py`

**Checkpoint**: A história deve passar nos testes de estratégia e CLI sem credenciais, preservando o caminho válido e propagando erros não relacionados.

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Validar a implementação e manter o guia de execução alinhado.

- [X] T006 [US1] Executar os cenários e comandos de verificação documentados em `specs/002-friendly-structured-output-errors/quickstart.md`

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Nenhuma dependência; nenhuma alteração de setup é necessária.
- **Foundational (Phase 2)**: Sem tarefas; não bloqueia a história.
- **User Story 1 (Phase 3)**: Independente e pode iniciar imediatamente.
- **Polish (Phase 4)**: Depende da conclusão da implementação US1.

### User Story Dependencies

- **User Story 1 (P1)**: Independente; única história desta feature e entrega o MVP.

### Within User Story 1

- T001 e T002 são testes em arquivos separados e podem ser escritos em paralelo antes da implementação.
- T003 define o tipo compartilhado; T004 e T005 dependem desse tipo.
- T006 depende de T001 a T005.

### Parallel Opportunities

- T001 e T002 podem ser feitos em paralelo porque alteram arquivos de teste distintos.
- T004 e T005 podem ser implementados em paralelo após T003, pois alteram arquivos de produção distintos.

## Parallel Example: User Story 1

```text
Task: "Adicionar testes de estratégia em tests/agents/test_plan_and_execute.py"
Task: "Adicionar teste do comando em tests/agents/test_arena_command.py"
```

Depois de T003:

```text
Task: "Traduzir validação na estratégia em src/agents/plan_and_execute.py"
Task: "Converter o erro no comando em src/agents/management/commands/arena.py"
```

## Implementation Strategy

### MVP First

1. Criar os testes de estratégia e CLI que cobrem a falha relatada.
2. Adicionar erro tipado reutilizável e conversões restritas nos limites definidos.
3. Executar os testes focados e verificar que erros não relacionados não são mascarados.
4. Executar o quickstart e Mypy antes de considerar a história concluída.

### Incremental Delivery

- A única história fornece a mensagem consistente para estratégia e CLI; UI futura fica fora do escopo atual.

## Notes

- Cada tarefa de implementação/teste inclui caminho de arquivo explícito.
- Não adicionar captura ampla de exceções nem alterar o `.env`.
