# Modelo de Dados: Núcleo de Raciocínio e Arena de Estratégias

## Objetos de execução

### TraceEvent

Registro imutável/validado emitido durante uma execução.

| Campo | Tipo | Regras |
|---|---|---|
| `type` | Literal | Um de `thought`, `action`, `observation`, `plan`, `critique`, `answer`. |
| `content` | string | Texto legível do evento; não vazio quando representar uma observação ou resposta. |
| `tool` | string opcional | Nome da ferramenta para eventos `action`; obrigatório nesse tipo. |
| `args` | dict opcional | Argumentos validados da ferramenta para eventos `action`; obrigatório nesse tipo. |

Eventos aparecem na ordem em que a estratégia os produz. Trace não contém raciocínio privado oculto do modelo; somente conteúdo explícito disponibilizado pela integração.

### ExecutionMetrics

| Campo | Tipo | Regras |
|---|---|---|
| `llm_calls` | inteiro | Contagem não negativa de invocações de modelo feitas pela estratégia, incluindo chamadas de planner/replanner. |
| `latency_ms` | float | Duração não negativa da execução completa em milissegundos. |

### StrategyResult

| Campo | Tipo | Regras |
|---|---|---|
| `answer` | string | Resposta final da estratégia. |
| `trace` | lista de `TraceEvent` | Eventos na ordem de execução. |
| `metrics` | `ExecutionMetrics` | Métricas agregadas da execução. |

### Strategy

Contrato de execução com nome estável e operação `run(input: str) -> StrategyResult` assíncrona. A arena inicial registra `react` e `plan_and_execute`; estratégias desconhecidas são rejeitadas na fronteira antes de iniciar qualquer uma.

### PlanStep e PlanState

`PlanStep` contém uma descrição textual validada para uma única etapa. `PlanState` carrega a solicitação, passos restantes, observações de passos executados, saída final opcional e contador. O planner cria a lista inicial; o executor consome no máximo um passo por iteração; o replanner substitui a lista após cada observação. O fluxo termina com lista vazia ou contador igual ao limite efetivo, nunca acima de oito.

## Objetos persistidos

### Service

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID/PK | Identificador único persistido. |
| `name` | string | Obrigatório, único e usado como referência de negócio no comando de abertura. |
| `description` | string | Opcional; resumo do serviço. |
| `created_at`, `updated_at` | datetime | Gerenciados na persistência. |

### Alert

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID/PK | Identificador único persistido. |
| `service` | FK → Service | Obrigatório; excluir serviço não deve apagar alertas acidentalmente. |
| `name` | string | Obrigatório; estável para identificar amostras do seed. |
| `message` | string | Texto descritivo do sinal. |
| `status` | enum | `firing` ou `resolved`. |
| `created_at`, `updated_at` | datetime | Gerenciados na persistência. |

Índice em `status` para filtragem; a leitura de lista é paginada, com tamanho máximo 100 e total correspondente.

### Incident

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID/PK | Identificador retornado pela abertura e usado para resolver. |
| `title` | string | Obrigatório e não vazio. |
| `service` | FK → Service | Obrigatório; o serviço deve existir. |
| `severity` | string | Obrigatória e não vazia; vocabulário aberto nesta versão. |
| `status` | enum | `open` ou `resolved`; abertura cria `open`. |
| `created_at`, `updated_at` | datetime | Gerenciados na persistência. |
| `resolved_at` | datetime opcional | Definido na transição para `resolved`. |

Resolução requer UUID válido e incidente existente. Uma transição repetida para `resolved` não deve aparentar criar/alterar outro incidente.

## Seed de demonstração

O comando mantém cinco serviços e seis alertas identificados como registros da fixture do produto, com três alertas `firing` e três `resolved`. A chave natural dos registros semeados é estável; nova execução atualiza a fixture do seed e não remove linhas que não pertencem a ela. Em um banco vazio, o resultado inicial totaliza cinco serviços e seis alertas. Nenhum incidente é exigido no seed.

## DTOs e schemas de entrada

- `ListAlertsInput`: filtro `status` opcional (`firing`/`resolved`), `limit` padrão até 100 e `offset` não negativo interno à store.
- `OpenIncidentInput`: `title`, `service` e `severity` como strings não vazias.
- `ResolveIncidentInput`: `id` em formato UUID.
- `ArenaInput`: solicitação não vazia, uma ou mais estratégias registradas e limite de iterações inteiro entre 1 e 8.
