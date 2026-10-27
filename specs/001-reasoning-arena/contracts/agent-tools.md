# Contrato de Ferramentas e Estratégias

## Entrada/saída das ferramentas

As ferramentas recebem objetos validados por schemas Pydantic e retornam dados ou observações explícitas. Erros de validação, regra de negócio, registro inexistente ou store devem propagar um erro tipado até o agente e não podem produzir resposta de sucesso.

### `list_alerts`

**Entrada**:

```json
{"status": "firing"}
```

`status` é opcional; valores aceitos quando presente: `firing` ou `resolved`.

**Saída**: lista paginada de alertas com identificador, serviço, nome, mensagem, estado e total. A página tem no máximo 100 registros. Sem filtro, inclui ambos os estados.

### `open_incident`

**Entrada**:

```json
{"title": "Erro elevado", "service": "checkout", "severity": "high"}
```

Os três campos são strings obrigatórias não vazias. `service` deve identificar um serviço existente e `severity` não está limitada a um conjunto enumerado nesta versão.

**Saída**: identificador do incidente, título, serviço, severidade e estado inicial `open`.

### `resolve_incident`

**Entrada**:

```json
{"id": "00000000-0000-0000-0000-000000000000"}
```

`id` deve ser UUID de um incidente existente.

**Saída**: identificador, estado `resolved` e data de resolução. ID malformado, incidente inexistente ou já resolvido é apresentado como erro, não como sucesso.

## Contrato de estratégia

Cada implementação expõe um nome estável e `async run(input: str) -> StrategyResult`. Um resultado inclui texto, eventos ordenados dos seis tipos permitidos e `llm_calls`/`latency_ms`. As estratégias recebem as ferramentas e modelo via construção/injeção para execução isolada em teste.

## ReAct

O agente decide quando chamar as ferramentas, inclui chamadas como eventos `action` e os respectivos retornos como `observation`, e conclui com um evento/resposta `answer`. Chamadas do modelo são contadas para todo o ciclo.

## Plan-and-Execute

O planner e o replanner retornam plano estruturado e validado. O executor executa no máximo uma etapa antes do replanejamento. A condição de parada é lista vazia ou `max_iterations` atingido, limitado a oito. A saída final inclui o que foi concluído e deixa claro quando restaram etapas pelo limite.
