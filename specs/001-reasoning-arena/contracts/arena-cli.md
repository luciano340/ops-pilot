# Contrato CLI: Arena de Estratégias

## Invocação

```text
python manage.py arena <solicitacao> [--strategies react,plan_and_execute] [--max-iterations 8]
```

- `<solicitacao>`: argumento posicional obrigatório e não vazio. A mesma string é enviada sem alteração a cada estratégia selecionada.
- `--strategies`: lista separada por vírgulas. Valores permitidos: `react`, `plan_and_execute`. Padrão: ambas, na ordem acima. Lista vazia, duplicatas ou nomes desconhecidos são erros de validação antes de executar qualquer estratégia.
- `--max-iterations`: inteiro de 1 a 8, padrão `8`; a estratégia Plan-and-Execute nunca excede oito, inclusive com valor explícito.

## Resultado

Para cada estratégia, na ordem solicitada:

1. Identificação da estratégia e resposta final.
2. Trace cronológico com tipos de evento e, para `action`, nome da ferramenta e argumentos.
3. Métricas `llm_calls` e `latency_ms`.

Os resultados são apresentados em colunas identificadas por estratégia quando o terminal comportar a comparação; caso contrário, em blocos paralelos com a mesma informação sem omitir eventos ou métricas.

## Falhas e saída

- Argumentos inválidos, estratégia não registrada ou credenciais de modelo ausentes geram mensagem explícita na fronteira e código de saída não zero.
- Falha de ferramenta/modelo durante uma estratégia não é apresentada como sucesso. A falha deve identificar a estratégia e não impedir que uma falha seja distinguida de uma resposta válida.
- A CLI não imprime credenciais nem valores secretos.

## Pré-requisitos operacionais

- Aplicar migrations antes de usar ferramentas com persistência.
- Definir `OPENROUTER_API_KEY` e `OPENROUTER_MODEL` para executar contra o provedor; testes unitários não os exigem.
- Configurar PostgreSQL via ambiente/Compose ou manter SQLite local.
