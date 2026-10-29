# Research: API HTTP de Chat

## Execução assíncrona Django

**Decision**: Implementar o controller como view assíncrona e aguardar o
serviço de chat. O caminho HTTP de produção deve usar a aplicação ASGI
existente (`config.asgi:application`) para atender solicitações concorrentes
sem adaptação WSGI por requisição. Aplicar o prazo no serviço com
`asyncio.timeout(180)`; deixar a view traduzir o timeout conhecido para 504.

**Rationale**: Django 6.1 suporta views `async def`. A documentação oficial
esclarece que o uso sob WSGI funciona, mas cada requisição recebe um event loop
único e não obtém os benefícios de uma stack assíncrona eficiente; ASGI é a
opção adequada para requisições longas e concorrência. A aplicação ASGI já
existe no repositório, e as estratégias e ferramentas chamam interfaces
assíncronas.

**Alternatives considered**:

- View síncrona envolvendo execução assíncrona: rejeitada porque bloqueia a
  thread de requisição e requer adaptação artificial do event loop.
- `asyncio.run()` na view: rejeitada porque cria event loop no controller,
  conflita com a execução async do Django e não oferece o comportamento
  concorrente exigido.
- Servir a view assíncrona sob WSGI: tecnicamente compatível, mas não
  proporciona uma stack assíncrona eficiente para requisições demoradas.

**Sources**:

- Django 6.1, Async support: https://docs.djangoproject.com/en/6.1/topics/async/
- Django 6.1, async views: https://github.com/django/django/blob/6.1/docs/topics/async.txt

## Validação JSON e proteção de dados no erro

**Decision**: Usar modelo Pydantic dedicado com campos estritos, extra
forbidden, remoção de espaços externos e validação de mensagem não vazia.
Validar o corpo JSON diretamente; converter erro de sintaxe e de schema em
HTTP 400. Construir `issues` selecionando apenas localização, tipo e mensagem
de cada erro, sem serializar `input`, `ctx` ou valor recusado.

**Rationale**: Pydantic v2 fornece `model_validate_json` e erros estruturados.
O schema mantém `strategy` como string não vazia em vez de enum fechado para
distinguir falha de formato (400) de nome não registrado (422). Campos
estritos evitam aceitar coerções ambíguas, em particular para booleanos.

**Alternatives considered**:

- Fazer parsing manual com `json.loads` e validação manual: rejeitada por
  duplicar schema e regras já cobertas pelo Pydantic.
- Colocar `strategy` num `Literal`/enum no request schema: rejeitada porque
  converteria estratégia inexistente em 400, contrariando o contrato 422.
- Retornar `ValidationError.errors()` integral: rejeitada porque pode conter
  `input` e contexto que exponham conteúdo enviado pelo usuário.

**Sources**:

- Pydantic 2.12, JSON parsing: https://docs.pydantic.dev/2.12/concepts/json/
- Pydantic 2.12, validation errors: https://docs.pydantic.dev/2.12/errors/errors/
- Pydantic, extra forbidden: https://docs.pydantic.dev/latest/concepts/models/#extra-data

## Cliente de testes assíncronos

**Decision**: Exercitar o contrato por meio de `django.test.AsyncClient` e
testes async pytest-django; injetar builders e avaliadores fake para cobrir
sucesso, erro e timeout sem instanciar nem chamar OpenRouter.

**Rationale**: O AsyncClient fornece a interface assíncrona e despacha pela
rota de requisição ASGI. A substituição do registry na fronteira do serviço
testa a integração HTTP e o wiring sem dependência de rede ou credenciais.

**Alternatives considered**:

- Testar apenas a função view diretamente: rejeitada porque não cobre
  roteamento, conversão HTTP e serialização do framework.
- Usar modelo fake LangChain para todos os testes de contrato: possível, mas
  adiciona complexidade não necessária para verificar a fronteira; testes
  existentes já demonstram padrão offline para estratégias.

**Sources**:

- Django 6.1, testing tools / AsyncClient:
  https://docs.djangoproject.com/en/6.1/topics/testing/tools/#django.test.AsyncClient

## Composição e isolamento das estratégias

**Decision**: Manter um registry Python de builders indexado por `react` e
`plan_and_execute`. O serviço valida o nome no registry antes de criar modelo,
ferramentas ou avaliador. Para reflexão, compõe `ReflectionStrategy` sobre a
instância base e usa `CritiqueOutput` com o mesmo modelo. Criar os objetos
dependentes por chamada, sem singleton mutável de estratégia.

**Rationale**: As classes de estratégias, fábrica, ferramentas e reflexão já
existem em `src/agents`. Um registry separa a seleção de nomes públicos da
construção e fornece um ponto simples de substituição por fakes em testes. A
criação por chamada evita compartilhar estado de execução entre requisições e
permite avaliar o timeout no contexto da chamada.

**Alternatives considered**:

- Acrescentar resolução de API ao comando da arena: rejeitada porque acopla
  controller HTTP ao CLI e à sua execução com `asyncio.run()`.
- Manter nomes compostos `reflect:react`: rejeitada porque reflection já é
  opção independente no contrato HTTP.
- Instanciar estratégia ou modelo global no import do módulo: rejeitada por
  efeitos colaterais de import, problemas de credenciais em testes e estado
  compartilhado.

## Erros de aplicação e transporte

**Decision**: Serviço diferencia `UnknownStrategyError` e
`StrategyTimeoutError`; view os traduz para os códigos estáveis de 422 e 504.
Falhas inesperadas recebem log no servidor e resposta 500 genérica em JSON,
sem exceção interna no corpo. Erros de validação não executam o serviço.

**Rationale**: A conversão de erro para status HTTP pertence à fronteira.
Falhas inesperadas precisam permanecer observáveis para operação, mas não
devem vazar detalhes ao cliente.

**Alternatives considered**:

- Traduzir toda exceção em 400 ou 422: rejeitada porque mascararia falhas de
  configuração/modelo como erro do cliente.
- Propagar o texto da exceção do provedor ao cliente: rejeitada por exposição
  de detalhes de integração.
- Responder 200 com resposta fallback: rejeitada por produzir resultado de
  sucesso enganoso.
