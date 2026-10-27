# Research: Núcleo de Raciocínio e Arena de Estratégias

## Decisões

### Integração de modelos OpenRouter

- **Decision**: Centralizar a criação em `agents.factory`, usando o `ChatOpenAI` de `langchain-openai` com `base_url="https://openrouter.ai/api/v1"`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` e `temperature=0` por padrão. Falhar explicitamente se as variáveis obrigatórias estiverem ausentes; não substituir credenciais ou modelo por valores fictícios.
- **Rationale**: O projeto já declara `langchain-openai`; OpenRouter aceita o protocolo OpenAI Chat Completions e documenta o endpoint `/api/v1`. A fábrica mantém configuração e substituição por fake num só ponto.
- **Alternatives considered**: Cliente OpenAI direto, que contornaria as abstrações LangChain e o requisito de provedor de modelo compartilhado; integração dedicada `langchain-openrouter`, que exigiria uma nova dependência e não é necessária para o endpoint compatível com OpenAI solicitado.
- **Sources**: [OpenRouter Python quickstart](https://openrouter.ai/docs/quickstart); Context7 `/websites/langchain_oss_python_langchain`, consulta sobre base URL compatível com OpenAI.

### Agente ReAct pré-construído

- **Decision**: Implementar a estratégia com `langchain.agents.create_agent`, as ferramentas operacionais e o runtime de grafo do LangGraph. Nomear a estratégia `react`. Capturar mensagens/eventos retornados pelo runtime, normalizá-los para os tipos de trace do domínio e contar chamadas ao modelo por execução.
- **Rationale**: A documentação atual do LangGraph marca `langgraph.prebuilt.create_react_agent` como depreciado e recomenda `langchain.agents.create_agent`, equivalente para o agente tool-calling sobre runtime LangGraph. Isso preserva o comportamento ReAct pré-construído sem depender de uma API obsoleta. A extração do trace deve converter mensagens de chamadas de ferramenta em pares action/observation e não expor chain-of-thought oculto: eventos thought só podem ser formados de conteúdo explicitamente retornado e disponível.
- **Alternatives considered**: Importar diretamente `langgraph.prebuilt.create_react_agent`, que corresponde literalmente ao nome da spec mas já está depreciado; construir um grafo ReAct manualmente, que duplicaria o agente pré-construído sem necessidade funcional.
- **Sources**: Context7 `/langchain-ai/langgraph`, documentação/API de `create_react_agent` e migração para `create_agent`; documentação de agentes LangChain.

### Plan-and-Execute e limite

- **Decision**: Criar grafo `StateGraph` com estado tipado contendo solicitação, etapas, observações, resultado final e contagem de iterações. Planner e replanner usam saída estruturada Pydantic. Um nó executor seleciona e executa no máximo a próxima etapa/ferramenta; após a observação, o replanejador retorna as etapas restantes ou conclusão. Roteamento condicional encerra se o plano estiver vazio ou o limite tiver sido alcançado. O limite padrão é oito e qualquer valor aceito pela CLI fica entre um e oito.
- **Rationale**: A estrutura de estado e arestas explícitas representa o requisito de ciclo planner/executor/replanner e permite testar o número exato de execuções. O cap é aplicado também no roteamento, independente das decisões do modelo.
- **Alternatives considered**: Ciclo controlado exclusivamente por prompt/LLM, que não assegura limite rígido; executar várias etapas numa única chamada, que viola o requisito de revisão entre etapas.
- **Sources**: Context7 `/langchain-ai/langgraph`, docs de `StateGraph`, arestas condicionais e saída Pydantic estruturada.

### Ferramentas e fronteira async/sync

- **Decision**: Definir schemas Pydantic para argumentos das três ferramentas e adapters tipados em `agents/tools.py`. Os adapters são assíncronos e chamam services, que por sua vez chamam a store async. Views de leitura têm paginação limitada a 100 e retornam itens e total. Os erros de domínio são convertidos em erros de ferramenta explícitos; não se devolve texto de sucesso para falhas.
- **Rationale**: Django 6.1 fornece variantes async com prefixo `a` para métodos que avaliam QuerySets; o código async deve aguardá-las. Isolar o acesso através da store mantém o domínio independente de I/O e os adapters apropriados para orquestração.
- **Alternatives considered**: Fazer consultas ORM diretamente dentro dos schemas/funções de tool, que mistura camadas; envolver ORM sync em tools async, que pode bloquear ou gerar erro de async-safety.
- **Sources**: Django 6.1, [async queries](https://docs.djangoproject.com/en/6.1/topics/db/queries/#asynchronous-queries); Context7 `/django/django/6.1`.

### Persistência e seed

- **Decision**: Criar uma aplicação Django `operations` com modelos Service, Alert e Incident; gerar migration inicial. O comando `seed_db` usa identificadores naturais estáveis para manter a fixture de demonstração de cinco serviços e seis alertas idempotente, sem remover dados não relacionados.
- **Rationale**: A inicialização repetível torna o cenário comparável e preserva registros fora do conjunto de demonstração. PostgreSQL é o destino no Compose e SQLite continua sendo a configuração local/de teste já existente.
- **Alternatives considered**: Inserção sem chave idempotente, que duplica linhas em cada execução; limpar as tabelas antes de semear, que pode apagar dados alheios à amostra.

### Chamadas ao modelo, latência e testes offline

- **Decision**: Medir latência monotônica por estratégia e anexar um contador por execução que incrementa uma vez no início de cada invocação ao modelo, incluindo tentativas, planner e replanner. Projetar construção das estratégias para receber/injetar o modelo e as ferramentas. Testes usam modelos fake/tool doubles, banco de teste local e tempo substituível; não carregam a fábrica real nem acessam a rede.
- **Rationale**: Métricas medem a execução completa e têm semântica previsível em fluxos que fazem várias chamadas. Injeção permite testar todas as transições sem segredo ou tráfego externo.
- **Alternatives considered**: Medir apenas a chamada final ou contar chamadas de ferramenta, que não corresponde a `llm_calls`; testar modelos reais, que torna os testes não determinísticos e depende de credenciais/rede.
- **Sources**: Context7 `/websites/langchain_oss_python_langgraph`, traces/event streaming e mensagens de ferramenta; princípios do projeto.

### CLI Django

- **Decision**: Implementar o comando Django como adaptador síncrono que valida argumentos na borda e executa o orquestrador async por `asyncio.run`. A solicitação é um argumento posicional; `--strategies` recebe nomes separados por vírgula e `--max-iterations` aceita inteiro de 1 a 8.
- **Rationale**: O comando pode ser usado diretamente por `manage.py`; a fronteira sync isola a inicialização do event loop e serviços async podem aguardar ORM async. Uma única solicitação posicional deixa clara a entrada compartilhada.
- **Alternatives considered**: Fazer a CLI acessar o ORM; aceitar limite maior que oito, o que contradiz o cap rígido; usar apenas variável de ambiente para a solicitação, que dificulta execuções reproduzíveis e scripts locais.
- **Sources**: Django 6.1 [custom management commands](https://docs.djangoproject.com/en/6.1/howto/custom-management-commands/); Context7 `/django/django/6.1`.

## Questões Resolvidas

- Não há clarificações pendentes da especificação.
- A opção `--max-iterations` será limitada a `[1, 8]`; o valor padrão é `8`.
- A primeira versão compara as estratégias sequencialmente, na ordem informada, para manter visível e determinística a interação com o armazenamento compartilhado.
- O modelo de negócio de severidades não é mais restrito do que um valor não vazio, pois a especificação não define um vocabulário de severidade.
