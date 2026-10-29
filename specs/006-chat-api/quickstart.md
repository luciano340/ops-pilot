# Quickstart: API HTTP de Chat

Este guia valida o contrato previsto para `POST /chat`. A execução real da
estratégia chama o modelo configurado no OpenRouter; os testes de integração
substituem estratégias e avaliadores por fakes e não precisam de rede ou
credenciais.

## Pré-requisitos

- Python 3.14 e dependências do projeto instaladas com `.[dev]`.
- Para executar manualmente uma estratégia real: `OPENROUTER_API_KEY` e
  `OPENROUTER_MODEL` disponíveis no ambiente do processo.
- Banco inicializado se a estratégia precisar consultar os dados operacionais:

```powershell
python manage.py migrate
python manage.py seed_db
```

## Executar o servidor de desenvolvimento

```powershell
python manage.py runserver
```

O servidor integrado é para desenvolvimento. Para validar comportamento
concorrente de produção, executar a aplicação pela entrada ASGI
`config.asgi:application`, como requerido pela documentação do Django.

## Solicitação manual

```powershell
curl.exe -i -X POST http://127.0.0.1:8000/chat `
  -H "Content-Type: application/json" `
  --data-binary "{`"message`":`"Liste alertas disparando`",`"strategy`":`"react`"}"
```

Esperado: HTTP 200; corpo JSON com `answer`, `trace` e `metrics`, incluindo
`llm_calls` e `latency_ms`. Para reflexão, defina `"reflect": true`; a resposta
continua associada à estratégia escolhida.

## Executar testes offline

```powershell
.\.venv\Scripts\Activate.ps1
pytest tests\agents\test_chat_api.py
mypy .
```

Esperado: os testes do endpoint passam sem `OPENROUTER_API_KEY`,
`OPENROUTER_MODEL`, rede ou chamadas a LLM. O conjunto deve cobrir:

- sucesso e serialização dos campos definidos em
  [contracts/chat-api.md](contracts/chat-api.md);
- JSON inválido, mensagem vazia, tipos inválidos e campos extras (400);
- estratégia não registrada (422);
- reflexão ativada e desativada;
- timeout, com o limite de 180 segundos substituído por valor curto no teste;
- falha operacional retornada sem conteúdo interno.

## Referências do design

- Contrato completo: [contracts/chat-api.md](contracts/chat-api.md)
- DTOs e ciclo de execução: [data-model.md](data-model.md)
- Decisões e fontes: [research.md](research.md)
