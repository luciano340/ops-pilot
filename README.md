# OpsPilot

OpsPilot é um copiloto de plantão para gerenciamento de alertas e incidentes de
produção. A API está sendo estruturada como um agente com LangChain/LangGraph
sobre OpenRouter.

> **Estado do projeto:** este repositório contém o esqueleto inicial da
> aplicação Django. A lógica de negócio e os comandos `arena` e `bench` ainda
> não foram implementados. O servidor Django integrado é para desenvolvimento,
> não para produção.

## Stack

- Python 3.14
- Django 6.1
- PostgreSQL com `psycopg` (SQLite por padrão no desenvolvimento local)
- Pydantic, `langchain-core` e `langchain-openai`
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

O arquivo `.env` é ignorado pelo Git. Configure nele, quando necessário,
`OPENROUTER_API_KEY` e `OPENROUTER_MODEL`. As configurações locais do Django
também aceitam `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` e `DJANGO_ALLOWED_HOSTS`.

## Docker Compose

Com Docker e Docker Compose instalados, crie o arquivo de ambiente e inicie os
serviços:

```bash
docker compose up --build
```

O Compose sobe a aplicação na porta `8000` e um PostgreSQL 17 com volume
persistente. A aplicação aguarda o banco passar no healthcheck antes de
iniciar. Acesse <http://localhost:8000>.

As variáveis do banco têm valores padrão para desenvolvimento e podem ser
definidas no `.env`:

```dotenv
POSTGRES_DB=ops_pilot
POSTGRES_USER=ops_pilot
POSTGRES_PASSWORD=ops_pilot
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
```

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
| `arena` | `python manage.py arena` |
| `bench` | `python manage.py bench` |

`arena` e `bench` estão cadastrados como tarefas, mas ainda dependem de
comandos Django que não foram criados.

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
