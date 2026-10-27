# OpsPilot

OpsPilot é um copiloto de plantão para gerenciamento de alertas e incidentes de
produção. A API está sendo estruturada como um agente com LangChain/LangGraph
sobre OpenRouter.

> **Estado do projeto:** inclui a arena inicial de estratégias, ferramentas de
> alertas/incidentes e seed de dados de demonstração. O comando `bench` ainda
> não foi implementado. O servidor Django integrado é para desenvolvimento,
> não para produção.

## Stack

- Python 3.14
- Django 6.1
- PostgreSQL com `psycopg` (SQLite por padrão no desenvolvimento local)
- Pydantic, LangChain, LangGraph e `langchain-openai`
- Pytest e Mypy em modo estrito

## Começar

### Windows (PowerShell)

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

### Linux/macOS

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

O SQLite é usado por padrão quando a aplicação é iniciada localmente. Para
iniciar o servidor de desenvolvimento:

```bash
python manage.py runserver
```

O arquivo `.env` é ignorado pelo Git. No Docker Compose, configure nele
`OPENROUTER_API_KEY` e `OPENROUTER_MODEL`. Para execução local, exporte essas
variáveis no ambiente do processo. As configurações locais do Django também
aceitam `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` e `DJANGO_ALLOWED_HOSTS`. A fábrica
do modelo falha explicitamente se as duas variáveis do OpenRouter estiverem
ausentes; os testes offline não precisam delas.

## Persistência e arena

Inicialize o esquema e os dados de demonstração:

```powershell
python manage.py migrate
python manage.py seed_db
```

O comando `seed_db` pode ser executado novamente sem duplicar seus cinco
serviços e seis alertas (três `firing`, três `resolved`) e sem apagar registros
fora da fixture.

Execute uma ou ambas as estratégias com a mesma solicitação:

```powershell
python manage.py arena "Liste os alertas firing" --strategies react,plan_and_execute --max-iterations 8
```

`--strategies` aceita `react` e `plan_and_execute`; o padrão são ambas.
`--max-iterations` aceita valores de 1 a 8 e o padrão é 8. O resultado separa
resposta, trace e métricas (`llm_calls` e `latency_ms`) de cada estratégia.
Chamadas reais à arena exigem credenciais OpenRouter e podem usar as ferramentas
de escrita de incidentes.

## Docker Compose

Com Docker e Docker Compose instalados, crie o arquivo de ambiente:

```bash
cp .env.example .env
```

Edite `.env` e configure `OPENROUTER_API_KEY` com uma chave de inferência criada
em [openrouter.ai/keys](https://openrouter.ai/keys) (não uma Management API
Key) e `OPENROUTER_MODEL` com um modelo disponível no OpenRouter. A chave é
necessária para executar a arena, mas não para iniciar o servidor nem rodar
comandos de diagnóstico Django.

Suba os containers em segundo plano:

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f app
```

O Compose inicia a aplicação na porta `8000` e o PostgreSQL 17, aguardando o
healthcheck do banco antes de iniciar o app. Acesse <http://localhost:8000>.
Pressione `Ctrl+C` para sair dos logs sem parar os containers.

O comando do serviço inicia apenas o servidor; migrations e seed não são
automáticos. Em outro terminal, inicialize o banco e os dados de exemplo:

```bash
docker compose exec app python manage.py migrate --noinput
docker compose exec app python manage.py seed_db
```

O seed pode ser executado novamente sem duplicar os cinco serviços e seis
alertas de demonstração.

### Verificar e usar a aplicação no container

Rode verificações Django e consulte o estado das migrations:

```bash
docker compose exec app python manage.py check
docker compose exec app python manage.py showmigrations
```

Para executar a arena com as duas estratégias, configure a chave e o modelo no
`.env` e rode:

```bash
docker compose exec app python manage.py arena "Liste os alertas firing" --strategies react,plan_and_execute --max-iterations 8
```

Esse comando faz chamadas reais ao OpenRouter e pode executar ações de escrita
se a solicitação pedir para abrir ou resolver incidentes. Para testar sem
chamar um modelo, use os testes locais descritos na seção de comandos; a imagem
de runtime não instala as dependências de desenvolvimento, como Pytest.

Para abrir um shell Django dentro do container:

```bash
docker compose exec app python manage.py shell
```

Ao finalizar, pare e remova os containers mantendo os dados persistidos:

```bash
docker compose down
```

Os dados do PostgreSQL ficam no volume `postgres_data`. **Não use**
`docker compose down -v` a menos que queira apagar também esse volume e todos os
dados locais.

As variáveis do banco têm valores padrão para desenvolvimento e podem ser
definidas no `.env` (`POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD`).
Defina também `DJANGO_SECRET_KEY` para substituir a chave de desenvolvimento
usada pelo Compose. Não use valores de desenvolvimento em ambientes
compartilhados ou de produção.

## Comandos

As tarefas abaixo são definidas no `pyproject.toml` via Taskipy. Com o ambiente
virtual ativado e as dependências de desenvolvimento instaladas, execute
`task <nome>` ou rode diretamente o comando indicado:

| Tarefa | Comando |
| --- | --- |
| `dev` | `python manage.py runserver` |
| `cli` | `python manage.py shell` |
| `test` | `pytest` |
| `typecheck` | `mypy .` |
| `arena` | `python manage.py arena "<solicitacao>"` |
| `bench` | `python manage.py bench` |

`bench` está cadastrado como tarefa, mas ainda depende de um comando Django que
não foi criado. A suíte de testes da arena e das operações é determinística e
não acessa rede nem requer credenciais de modelo:

```powershell
pytest tests\agents tests\operations
mypy .
```

## Organização e convenções

A aplicação Django fica em `src/config/`; `manage.py` é o ponto de entrada dos
comandos administrativos. As funcionalidades devem respeitar as camadas
HTTP/CLI → Services → Store: o domínio não faz I/O, Services concentra as
regras de negócio e Store cuida da persistência.

Novas entradas HTTP e CLI devem ser validadas na fronteira com schemas Pydantic,
e as camadas devem se comunicar por DTOs. Use anotações de tipo nas assinaturas
e adicione testes de domínio às novas regras.

## Fluxo Spec Kit

O desenvolvimento de funcionalidades segue esta sequência:

```text
speckit.specify → speckit.plan → speckit.tasks → speckit.implement
```

As especificações e demais artefatos em `specs/` devem ser versionados junto ao
código. Escreva e aprove a especificação antes de iniciar a implementação.
