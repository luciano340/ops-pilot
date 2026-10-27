---

description: "Tarefas para implementar o núcleo de raciocínio e a arena de estratégias"
---

# Tasks: Núcleo de Raciocínio e Arena de Estratégias

**Input**: Documentos de design em `/specs/001-reasoning-arena/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/` e `quickstart.md`

**Tests**: Testes são obrigatórios nesta feature: a especificação exige testes de ferramentas/store/formatadores e execução determinística offline.

**Organization**: As tarefas estão agrupadas pelas quatro histórias de usuário para permitir implementação e validação incremental.

## Phase 1: Setup

**Purpose**: Preparar dependências e estrutura Django necessária para os componentes da feature.

- [X] T001 Atualizar `pyproject.toml` com as dependências `langchain` e `langgraph` e configurar descoberta dos pacotes Django `agents` e `operations` em `src/`
- [X] T002 Criar os pacotes Django `src/agents/` e `src/operations/`, seus `apps.py` e registrar ambas as aplicações em `src/config/settings.py`

---

## Phase 2: Foundational

**Purpose**: Estabelecer modelos persistidos, contratos comuns e erros tipados exigidos por mais de uma história.

**⚠️ CRITICAL**: Completar esta fase antes de implementar qualquer história de usuário.

- [X] T003 Criar modelos e migration inicial em `src/operations/models.py` e `src/operations/migrations/`: Service tem `id` UUID, `name` obrigatório/único, `description` opcional e timestamps; Alert tem `id` UUID, FK obrigatória para Service que não apaga alertas em cascata, `name` obrigatório, `message`, status limitado a `firing` ou `resolved` e timestamps; Incident tem `id` UUID, título/service/severity obrigatórios e não vazios, status `open` ou `resolved`, timestamps e `resolved_at` opcional
- [X] T004 Implementar `TraceEvent`, `ExecutionMetrics` e `StrategyResult` tipados em `src/agents/types.py`: limitar tipos de evento a `thought`, `action`, `observation`, `plan`, `critique` e `answer`; exigir ferramenta e argumentos em eventos `action`; exigir contagens/latência não negativas
- [X] T005 Implementar a interface abstrata `ReasoningStrategy` em `src/agents/base.py` com `name: str` e `async run(input: str) -> StrategyResult`
- [X] T006 Definir DTOs e exceções de domínio tipadas em `src/operations/domain.py` e schemas de fronteira em `src/operations/schemas.py`, incluindo filtro de alerta opcional (`firing`/`resolved`), argumentos não vazios para abertura de incidente e identificador UUID para resolução

**Checkpoint**: Aplicações registradas, contratos de estratégia definidos, esquema persistente migrável e erros/DTOs compartilhados disponíveis.

---

## Phase 3: User Story 1 - Comparar estratégias de raciocínio (Priority: P1) 🎯 MVP

**Goal**: Executar estratégias com entrada idêntica e apresentar resposta, trace e métricas separadamente.

**Independent Test**: Injetar duas estratégias determinísticas, executar a arena com a mesma entrada e confirmar resultados distinguíveis, trace ordenado e métricas; validar rejeição de opções inválidas sem chamada a qualquer estratégia.

### Tests for User Story 1

- [X] T007 [P] [US1] Testar tipos válidos/inválidos de trace, invariantes de `action`, métricas e resultado em `tests/agents/test_types.py`
- [X] T008 [P] [US1] Testar formatação cronológica de eventos, argumentos de ação, resposta e métricas em `tests/agents/test_trace_formatting.py`
- [X] T009 [P] [US1] Testar arena com estratégias fake, entrada idêntica, seleção inválida e contagem/latência determinísticas em `tests/agents/test_arena.py`

### Implementation for User Story 1

- [X] T010 [US1] Implementar a fábrica OpenRouter em `src/agents/factory.py` lendo `OPENROUTER_API_KEY` e `OPENROUTER_MODEL`, configurando `https://openrouter.ai/api/v1` e temperatura padrão zero; falhar explicitamente se a configuração obrigatória estiver ausente
- [X] T011 [US1] Implementar a estratégia ReAct em `src/agents/react.py` com o agente pré-construído atual (`langchain.agents.create_agent`), modelo e ferramentas injetáveis, trace normalizado de mensagens/ações/observações e contagem de cada invocação ao modelo
- [X] T012 [US1] Implementar execução e formatação comparativa em `src/arena.py`: validar estratégias antes de executar, enviar exatamente a mesma entrada, medir duração por estratégia e exibir resposta, eventos ordenados e métricas sem omissões
- [X] T013 [US1] Implementar o comando Django em `src/agents/management/commands/arena.py`: aceitar solicitação posicional não vazia, `--strategies` com nomes separados por vírgula e `--max-iterations` inteiro entre 1 e 8 com padrão 8; traduzir falhas para saída CLI explícita e não zero
- [X] T014 [US1] Integrar a construção do modelo, estratégias disponíveis e saída da arena em `src/agents/management/commands/arena.py`, mantendo fábrica e estratégias substituíveis nos testes offline

**Checkpoint**: Comparação executável com estratégias injetadas sem rede e comando validado na fronteira.

---

## Phase 4: User Story 2 - Investigar alertas e gerenciar incidentes (Priority: P1)

**Goal**: Consultar alertas e criar/resolver incidentes por tools que validam argumentos e persistem alterações.

**Independent Test**: Com banco de teste, listar alertas sem filtro e por estado, criar incidente para serviço existente e resolvê-lo; confirmar falhas explícitas sem mutação para entradas/IDs inválidos ou inexistentes.

### Tests for User Story 2

- [X] T015 [P] [US2] Testar consultas paginadas, filtragem e total, abertura e resolução de incidentes e registros inexistentes em `tests/operations/test_store.py`
- [X] T016 [P] [US2] Testar regras de domínio de status, validação dos três schemas de ferramenta e erros sem resultado de sucesso em `tests/operations/test_services.py` e `tests/agents/test_tools.py`

### Implementation for User Story 2

- [X] T017 [US2] Implementar operações assíncronas de persistência para serviços, alertas e incidentes em `src/operations/store.py`; leituras de alertas retornam `(List[Entity], total)`, aceitam paginação e limitam cada página a no máximo 100 registros
- [X] T018 [US2] Implementar serviços de consulta e mutação em `src/operations/services.py`: validar transições, exigir serviço existente para criar incidente e rejeitar incidente inexistente ou já resolvido sem indicar sucesso
- [X] T019 [US2] Implementar adapters tipados `list_alerts`, `open_incident` e `resolve_incident` em `src/agents/tools.py`, validando entrada com schemas Pydantic e encaminhando erros tipados sem fallback de sucesso
- [X] T020 [US2] Conectar os adapters de `src/agents/tools.py` à estratégia ReAct em `src/agents/react.py` sem contornar Services/Store

**Checkpoint**: As três ferramentas operacionais funcionam com banco local e as ações/observações ficam disponíveis para o trace ReAct.

---

## Phase 5: User Story 3 - Executar raciocínio com planejamento limitado (Priority: P2)

**Goal**: Planejar, executar exatamente uma etapa por ciclo e replanejar até conclusão ou oito iterações.

**Independent Test**: Injetar planner, executor e replanner determinísticos; verificar estrutura do plano, ordem de passos, replanejamento após cada observação e encerramento com plano vazio ou limite, sem mais de oito execuções.

### Tests for User Story 3

- [X] T021 [P] [US3] Testar plano estruturado, execução de um passo por vez, revisão após observação, conclusão e plano ainda pendente no limite em `tests/agents/test_plan_and_execute.py`

### Implementation for User Story 3

- [X] T022 [US3] Implementar schemas Pydantic de `PlanStep` e plano estruturado, mais estado tipado da execução, em `src/agents/plan_and_execute.py`
- [X] T023 [US3] Construir grafo `StateGraph` planner/executor/replanner em `src/agents/plan_and_execute.py`; executar no máximo uma etapa antes de replanejar, registrar plano/ação/observação e encerrar por plano vazio ou `max_iterations` limitado a oito
- [X] T024 [US3] Integrar `PlanAndExecuteStrategy` ao contrato comum, ferramentas e métricas em `src/agents/plan_and_execute.py`; garantir resposta explícita quando o limite for atingido com etapas pendentes

**Checkpoint**: Estratégia Plan-and-Execute determinística em teste e incapaz de exceder oito iterações.

---

## Phase 6: User Story 4 - Preparar dados e validar sem dependências externas (Priority: P2)

**Goal**: Disponibilizar dados iniciais repetíveis e garantir que os testes essenciais funcionem sem modelo/rede.

**Independent Test**: Executar o seed duas vezes em banco local inicialmente vazio; verificar cinco serviços e seis alertas, distribuição três/três sem duplicatas; executar testes de store, tools e formatador com dependências externas substituídas.

### Tests for User Story 4

- [X] T025 [P] [US4] Testar execução repetida do seed, quantidade/distribuição da fixture e preservação de registros externos em `tests/operations/test_seed_db.py`
- [X] T026 [P] [US4] Testar execução de componentes do agente com modelo fake e sem credenciais, garantindo que os testes não criem cliente nem solicitem rede em `tests/agents/test_offline.py`

### Implementation for User Story 4

- [X] T027 [US4] Implementar comando `seed_db` em `src/operations/management/commands/seed_db.py` com cinco serviços e seis alertas nomeados de forma estável, três `firing` e três `resolved`; repetir a operação sem duplicar nem apagar registros fora da fixture
- [X] T028 [US4] Criar fixtures reutilizáveis de modelo fake e ambiente sem credenciais em `tests/conftest.py`; os testes não constroem cliente OpenRouter nem fazem chamadas de rede

**Checkpoint**: Seed idempotente e testes determinísticos executáveis sem rede ou configuração de modelo.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentar uso e validar o fluxo completo respeitando qualidade e limites de recursos.

- [X] T029 [P] Atualizar `README.md` com configuração externa OpenRouter, migrations, comandos `seed_db`/`arena` e instruções de testes offline
- [X] T030 Conferir se todas as assinaturas adicionadas em `src/agents/` e `src/operations/` têm type hints e eliminar incompatibilidades reportadas por `mypy .`
- [X] T031 Executar `pytest` e `mypy .`, corrigir falhas relacionadas à feature e registrar a validação do guia em `specs/001-reasoning-arena/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências; preparar dependências e aplicações Django.
- **Foundational (Phase 2)**: depende de Setup e bloqueia todas as histórias.
- **US1 (Phase 3)**: depende de Foundation; a comparação pode ser validada com estratégias/tools fake e não depende da implementação da store.
- **US2 (Phase 4)**: depende de Foundation; fornece as ferramentas reais e integra o ReAct ao armazenamento.
- **US3 (Phase 5)**: depende de Foundation e de US2 para executar ferramentas reais; seu grafo pode ser testado com ferramentas fake.
- **US4 (Phase 6)**: depende de US2 para semear modelos persistidos; testes offline não dependem de US1/US3.
- **Polish (Phase 7)**: depende das histórias que serão entregues.

### User Story Dependencies

- **US1 (P1)**: independente após Foundation para arena/CLI e ReAct com ferramentas injetadas; integração real com tools é concluída em US2 (T020).
- **US2 (P1)**: independente após Foundation; fornece persistência e ferramentas para a operação real.
- **US3 (P2)**: pode iniciar após Foundation para testes fakes, mas a integração end-to-end com ferramentas requer US2.
- **US4 (P2)**: requer os modelos e store de US2; pode ser implementada após US2 sem depender da arena.

### Within Each User Story

- Testes dos contratos/módulos de uma história podem ser escritos antes da implementação e devem falhar antes do comportamento existir.
- Tasks só recebem `[P]` quando alteram arquivos diferentes e não dependem de tarefas incompletas.
- Persistência antecede services; services antecedem adapters; adapters antecedem integração das estratégias.
- Aplicar migrations antes de testar ferramentas ou o comando de seed.

### Dependency Graph

```text
T001 → T002 → T003–T006 (Foundation)
                    ├── US1: T007–T014
                    ├── US2: T015–T020
                    └── US3: T021–T024 (integração real depende de US2)
US2 → US4: T025–T028
US1 + US2 + US3 + US4 → T029–T031
```

### Parallel Opportunities

- Após T002, T003, T004 e T006 podem ser desenvolvidas em paralelo; T005 depende de T004.
- Na US1, T007, T008 e T009 são testes de arquivos distintos; a implementação da fábrica (T010) pode ocorrer em paralelo à formatação da arena (T012) depois dos contratos, evitando conflitos em `src/arena.py`/`src/agents/factory.py`.
- Na US2, T015 e T016 podem ser implementadas em paralelo; a sequência de produção é T017 → T018 → T019 → T020, com T020 também dependendo de T011.
- Na US3, T021 pode ser escrito antes da implementação; T022 precede T023, que precede T024.
- Na US4, T025 e T026 podem ser escritos em paralelo; T027 depende de T017 e T003.
- T029 pode ocorrer em paralelo à validação final quando os comandos estiverem estabilizados.

## Parallel Example: User Story 1

```text
# Após T004 e T005, preparar testes independentes em arquivos distintos:
T007 tests/agents/test_types.py
T008 tests/agents/test_trace_formatting.py
T009 tests/agents/test_arena.py

# Depois dos contratos, implementar componentes em arquivos distintos:
T010 src/agents/factory.py
T012 src/arena.py
```

## Parallel Example: User Story 2

```text
# Testes isolados por área:
T015 tests/operations/test_store.py
T016 tests/operations/test_services.py e tests/agents/test_tools.py

# Implementar store e schemas/adapters em arquivos distintos:
T017 src/operations/store.py
T019 src/agents/tools.py
```

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Setup e Foundation.
2. Implementar a comparação CLI com estratégias injetadas e resposta/trace/métricas.
3. Executar os testes da US1 sem rede e validar rejeição de opções inválidas.
4. Integrar tools reais em US2 para a demonstração operacional de ponta a ponta.

### Incremental Delivery

1. Setup + Foundation: contratos tipados e modelos migráveis.
2. US1: comparação e estratégia ReAct testável com fakes.
3. US2: persistência, alertas e gestão de incidentes, integrados ao ReAct.
4. US3: alternativa Plan-and-Execute com limite inviolável.
5. US4: seed e verificação offline repetível.
6. Polish: documentação, suite total e Mypy.

### Parallel Team Strategy

1. Concluir Setup e Foundation em conjunto.
2. Em seguida, US1 e US2 podem avançar em paralelo, respeitando a integração final T020.
3. US3 pode desenvolver e validar o grafo com ferramentas fake em paralelo; integração final usa as tools de US2.
4. US4 começa após a store/modelos estarem prontos.

## Notes

- `[P]` indica tarefas em arquivos distintos que não dependem de tarefas incompletas.
- `[US1]`–`[US4]` mapeiam diretamente as histórias da especificação.
- A seed usa fixture identificável e idempotente; não deve limpar dados não pertencentes à fixture.
- As chamadas de modelo reais só são usadas na execução explícita da arena; a suíte obrigatória permanece offline.
- Nenhuma tarefa cria/expõe chain-of-thought privado; o trace contém eventos e conteúdo disponibilizados explicitamente pela integração.
