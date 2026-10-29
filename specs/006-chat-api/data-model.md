# Data Model: API HTTP de Chat

## Persistência

Esta feature não introduz entidades persistidas, tabelas ou migrations. O
endpoint executa uma estratégia existente e retorna um resultado transitório
para o solicitante.

## DTOs e valores da requisição

### ChatRequest

Representa o corpo JSON validado na fronteira HTTP.

| Campo | Tipo | Obrigatório | Padrão | Validação |
|---|---|---:|---|---|
| `message` | string | Sim | — | Aparar espaços externos; rejeitar se vazio após aparar. |
| `strategy` | string | Não | `react` | String não vazia após aparar; o registry determina se o nome é suportado. |
| `reflect` | booleano | Não | `false` | Tipo booleano estrito; não aceitar conversão de string ou número. |

Campos adicionais são proibidos. A mensagem normalizada é passada à estratégia.

### StrategyResult

Resultado transitório das estratégias existentes, serializado na resposta.

| Campo | Tipo | Descrição |
|---|---|---|
| `answer` | string | Resposta final produzida pela estratégia. |
| `trace` | lista de `TraceEvent` | Eventos tipados em ordem de execução. |
| `metrics` | `ExecutionMetrics` | Contagem de chamadas ao modelo e latência em milissegundos. |

### TraceEvent

Reutiliza `agents.types.TraceEvent`. `type` é um dos valores existentes:
`thought`, `action`, `observation`, `plan`, `critique` ou `answer`. Eventos
`action` carregam nome de ferramenta e argumentos; os demais não carregam
esses campos.

### ExecutionMetrics

Reutiliza `agents.types.ExecutionMetrics`.

| Campo | Tipo | Regra |
|---|---|---|
| `llm_calls` | inteiro | Maior ou igual a zero. |
| `latency_ms` | número | Maior ou igual a zero. |

## Erros de transporte

| Caso | HTTP | Corpo |
|---|---:|---|
| JSON inválido ou campos não válidos | 400 | `{ "issues": [{ "loc": [...], "code": "...", "message": "..." }] }` |
| Estratégia não registrada | 422 | `{ "error": { "code": "unknown_strategy", "message": "..." } }` |
| Prazo excedido | 504 | `{ "error": { "code": "strategy_timeout", "message": "..." } }` |
| Falha operacional inesperada | 500 | `{ "error": { "code": "internal_error", "message": "..." } }` |
| Método não permitido | 405 | Resposta Django de método não permitido; não executar estratégia. |

Mensagens de erro são genéricas e não contêm o valor rejeitado, conteúdo da
mensagem, credenciais, stack trace ou detalhes do provedor. `loc` identifica
somente o campo ou posição do JSON rejeitado.

## Ciclo de execução

1. A view lê o corpo e valida `ChatRequest`.
2. O serviço localiza o builder por `strategy`; nome ausente do registry falha
   antes de criar dependências externas.
3. O serviço cria a estratégia base. Se `reflect=true`, compõe a reflexão
   existente.
4. O serviço aguarda `run(message)` dentro do limite de 180 segundos.
5. A view serializa o resultado ou traduz o erro tipado correspondente.

Nenhum histórico ou resultado é mantido entre chamadas.
