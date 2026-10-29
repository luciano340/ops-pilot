# Tasks: API HTTP de Chat

**Input**: Design documents from `specs/006-chat-api/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/chat-api.md`, `quickstart.md`

**Tests**: Incluídos porque a especificação exige testes de integração
determinísticos sem rede e credenciais.

**Organization**: As tarefas estão agrupadas pelas histórias de usuário da
especificação para permitir implementação e validação incremental.

## Phase 1: Setup

**Purpose**: Preparar o trabalho sem alterar infraestrutura já configurada.

O projeto já tem Django, Pydantic, pytest, pytest-django, configuração de
descoberta de `tests/` e entrada ASGI. Não são necessárias tarefas de setup nem
novas dependências.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Criar contratos e seleção compartilhados necessários para todas
as histórias.

**⚠️ CRITICAL**: Completar esta fase antes do trabalho das histórias.

- [X] T001 [P] Criar o DTO Pydantic `ChatRequest` em `src/agents/chat_schemas.py`, com `message` obrigatório aparado e não vazio, `strategy` string opcional não vazia com padrão `react`, `reflect` booleano estrito com padrão `false` e campos extras proibidos
- [X] T002 [P] Definir `UnknownStrategyError` e `StrategyTimeoutError` em `src/agents/chat_errors.py` como erros tipados da camada de aplicação, sem dependência de HTTP
- [X] T003 Criar o registry Python de builders para `react` e `plan_and_execute` em `src/agents/registry.py`, injetável nos testes; fazer o serviço rejeitar nomes não registrados com `UnknownStrategyError` antes de criar modelo ou ferramentas (depende de T002)

**Checkpoint**: Contratos de entrada, erros de aplicação e seleção de
estratégias estão definidos; histórias podem ser implementadas.

---

## Phase 3: User Story 1 - Executar estratégia de chat (Priority: P1) 🎯 MVP

**Goal**: Permitir executar as estratégias registradas por `POST /chat` e
retornar resultado, trace e métricas no formato existente.

**Independent Test**: Com `django.test.AsyncClient` e estratégias fake,
verificar seleção padrão `react`, seleção explícita `plan_and_execute`, status
200 e serialização dos campos do contrato; confirmar 405 para método diferente
de POST sem executar estratégia.

### Tests for User Story 1

> Escrever primeiro e confirmar que falham antes de implementar o endpoint.

- [X] T004 [US1] Adicionar testes de integração assíncronos em `tests/agents/test_chat_api.py` para sucesso com estratégia padrão e explícita, formato `answer`/`trace`/`metrics` e método não permitido sem execução

### Implementation for User Story 1

- [X] T005 [US1] Implementar o serviço de chat em `src/agents/chat_service.py`, resolvendo o builder registrado, criando `create_model()` e `get_agent_tools()` apenas para a estratégia selecionada e aguardando `ReasoningStrategy.run(message)` (depende de T003)
- [X] T006 [US1] Implementar a view assíncrona em `src/agents/views.py` e registrar `POST /chat` em `src/config/urls.py`, validando `request.body` com `ChatRequest` e serializando `StrategyResult` sem alterar os nomes de `llm_calls` e `latency_ms` (depende de T001 e T005)

**Checkpoint**: A chamada HTTP das estratégias existentes funciona de ponta a
ponta sem alterar o comportamento da arena.

---

## Phase 4: User Story 2 - Solicitar reflexão da resposta (Priority: P2)

**Goal**: Aplicar reflexão opt-in à estratégia selecionada, mantendo os nomes
públicos `react` e `plan_and_execute`.

**Independent Test**: Enviar requisições com reflexão desativada e ativada para
um avaliador e estratégia fake; confirmar que somente a solicitação com
`reflect=true` invoca o avaliador e que o formato de resposta continua igual.

### Tests for User Story 2

> Escrever primeiro e confirmar que falham antes de implementar.

- [X] T007 [US2] Adicionar casos de integração em `tests/agents/test_chat_api.py` verificando `reflect` padrão/desativado, reflexão ativada, chamada ao avaliador fake e presença de evento de crítica sem nomes de estratégia compostos (depende de T006)

### Implementation for User Story 2

- [X] T008 [US2] Estender `src/agents/chat_service.py` para compor `ReflectionStrategy` somente quando `ChatRequest.reflect` for verdadeiro, usando `CritiqueOutput` e o mesmo modelo da estratégia base sem expor o nome decorado na resposta HTTP (depende de T005–T007)

**Checkpoint**: Reflexão é opt-in, testável offline e compatível com as duas
estratégias já existentes.

---

## Phase 5: User Story 3 - Receber erros de solicitação compreensíveis (Priority: P3)

**Goal**: Distinguir entradas inválidas, estratégia desconhecida, timeout e
falhas operacionais com status e corpos estáveis, sem vazar dados internos.

**Independent Test**: Usar payloads inválidos, nome não registrado e fakes que
expiram ou falham; verificar 400/422/504/500, ausência de execução quando a
entrada é inválida e nenhuma exposição de valores recusados ou exceções.

### Tests for User Story 3

> Escrever primeiro e confirmar que falham antes de implementar o tratamento.

- [X] T009 [US3] Adicionar testes em `tests/agents/test_chat_api.py` para JSON malformado/não objeto, campos extras, mensagem inválida e booleano incorreto (400 com `issues` sem valores de entrada), além de estratégia desconhecida (422 `unknown_strategy`) sem execução do builder
- [X] T010 [US3] Adicionar testes em `tests/agents/test_chat_api.py` para timeout (504 `strategy_timeout`) e erro operacional inesperado (500 genérico sem detalhes da exceção)
- [X] T011 [US3] Adicionar teste concorrente em `tests/agents/test_chat_api.py` com estratégias fake sincronizadas para confirmar que uma solicitação independente conclui enquanto outra aguarda

### Implementation for User Story 3

- [X] T012 [US3] Mapear erros de validação, `UnknownStrategyError` e timeout para 400/422/504 com os corpos de `specs/006-chat-api/contracts/chat-api.md` em `src/agents/views.py`, construindo cada `issues` somente com `loc`, `code` e `message` (depende de T006 e T009)
- [X] T013 [US3] Aplicar o limite padrão de 180 segundos ao `await` da estratégia em `src/agents/chat_service.py` e converter a expiração em `StrategyTimeoutError` cancelando a espera em andamento (depende de T002 e T010)
- [X] T014 [US3] Tratar falhas operacionais em `src/agents/views.py` com logging do erro no servidor e resposta 500 genérica, sem capturar erros de forma silenciosa nem expor stack traces, valores de entrada ou detalhes do provedor (depende de T012)

**Checkpoint**: Erros e concorrência atendem ao contrato HTTP sem chamadas
externas nos testes.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentar o uso público e validar a implementação completa.

- [X] T015 [P] Documentar a rota `POST /chat`, campos opcionais, requisitos OpenRouter e exemplos de sucesso/erro em `README.md`, referenciando `specs/006-chat-api/contracts/chat-api.md`
- [X] T016 Executar `pytest tests/agents/test_chat_api.py` e `mypy .`; corrigir regressões relacionadas à feature nos arquivos `src/agents/`, `src/config/urls.py` e `tests/agents/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Nenhuma alteração necessária; dependências e infraestrutura
  atuais já atendem a feature.
- **Foundational (Phase 2)**: Bloqueia as histórias; T001 e T002 podem ser
  executadas em paralelo, T003 depende de T002.
- **User Stories (Phase 3+)**: Dependem da fase foundational. Na execução
  incremental recomendada, US2 depende do serviço/endpoint de US1 e US3 depende
  dos caminhos HTTP introduzidos em US1.
- **Polish (Phase 6)**: Depende das histórias escolhidas e completas.

### User Story Dependencies

- **US1 (P1)**: Inicia após Phase 2; entrega MVP HTTP.
- **US2 (P2)**: Depende de T005 e T006 para compor reflexão no serviço e
  exercitá-la via endpoint.
- **US3 (P3)**: Depende de T006; integra timeout, erro desconhecido e
  tratamento operacional sobre os caminhos HTTP/serviço existentes.

### Within Each User Story

- Escrever testes antes da implementação e confirmar que falham.
- Manter os testes Django e testes de concorrência em
  `tests/agents/test_chat_api.py`; não executar em paralelo tarefas que alterem
  esse mesmo arquivo.
- Completar serviço antes de integrar a view e a rota.
- Executar testes direcionados da história no checkpoint antes de avançar.

### Parallel Opportunities

- T001 (schema) e T002 (erros) podem ser feitos em paralelo.
- Após T001–T003, T004 pode ser implementada enquanto ajustes independentes de
  documentação de contrato forem preparados; evitar alterações concorrentes ao
  mesmo arquivo de teste.
- T007 é uma tarefa de teste que deve preceder T008, não deve concorrer com
  alterações em `tests/agents/test_chat_api.py`.
- T015 (README) pode ser executada em paralelo às alterações de código das
  histórias, pois modifica um arquivo diferente; finalizar antes da revisão
  global.

## Parallel Example: User Story 1

```text
# Phase 2: arquivos independentes
T001: Criar ChatRequest em src/agents/chat_schemas.py
T002: Criar erros tipados em src/agents/chat_errors.py

# Depois de concluir T001–T003, escrever o teste antes do endpoint
T004: Testar POST /chat em tests/agents/test_chat_api.py
T005: Implementar serviço em src/agents/chat_service.py
```

As tarefas T004 e T005 são ordenadas por TDD: primeiro o teste; depois a
implementação. Não são paralelas entre si.

## Implementation Strategy

### MVP First (User Story 1)

1. Completar T001–T003 na Phase 2.
2. Escrever T004 e confirmar a falha esperada.
3. Implementar T005–T006 e validar seleção de estratégia, resposta e método.
4. **Parar e validar** o endpoint com os testes offline da US1.
5. Entregar/demonstrar o MVP sem reflexão; adicionar tratamento completo de
   erros e timeout conforme as histórias seguintes.

### Incremental Delivery

1. Foundation → schema, erros e registry prontos.
2. US1 → execução HTTP básica testável sem modelo real.
3. US2 → reflexão opt-in validada por avaliador fake.
4. US3 → erros estruturados, timeout, logging e concorrência verificados.
5. Polish → documentação do usuário, Pytest direcionado e Mypy.

## Notes

- Tarefas paralelizáveis usam `[P]` somente quando trabalham em arquivos
  diferentes e não dependem de tarefas incompletas.
- O rótulo `[USn]` identifica a história de usuário; setup, foundation e polish
  não recebem esse rótulo.
- Não criar tabelas nem migrations: a feature não persiste conversas.
- Manter testes offline; não configurar nem exigir credenciais OpenRouter.
