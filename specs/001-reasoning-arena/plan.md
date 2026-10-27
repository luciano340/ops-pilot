# Implementation Plan: Núcleo de Raciocínio e Arena de Estratégias

**Branch**: `001-reasoning-arena` | **Date**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-reasoning-arena/spec.md`

## Summary

Implementar um núcleo tipado para estratégias de raciocínio que compartilham ferramentas operacionais, persistência de serviços, alertas e incidentes, e resultados comparáveis com trace e métricas. A solução acrescenta uma aplicação Django de operações e uma aplicação de agentes, integra modelos OpenRouter pela integração OpenAI já prevista no projeto, fornece fluxos ReAct e Plan-and-Execute limitados, e valida o comportamento por testes offline com modelo e relógio substituíveis.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Django 6.1, Pydantic 2, `langchain-core`, `langchain-openai`; adicionar `langchain` e `langgraph` para agentes e grafos.
**Storage**: PostgreSQL no Compose; SQLite local e nos testes Django.
**Testing**: Pytest, pytest-django e Mypy em modo estrito. Testes do agente usam doubles/fakes e não precisam de rede ou credenciais.
**Target Platform**: Aplicação Django executada localmente em Windows/Linux e em contêiner Linux; comandos administrativos são a interface desta feature.
**Project Type**: Projeto Django monolítico com serviços internos e CLI administrativa, sem frontend incluído nesta feature.
**Performance Goals**: Medir e reportar latência por estratégia e contagem de chamadas ao modelo; não há meta de tempo de resposta real definida. Consultas de alertas seguem o limite de paginação do projeto, no máximo 100 registros.
**Constraints**: Requisições de modelo devem usar OpenRouter com temperatura padrão zero e credenciais externas ao código. As ferramentas de persistência e execuções dos agentes são assíncronas; acessos ORM em código assíncrono usam APIs async do Django. A estratégia de planejamento não excede oito iterações, mesmo se a CLI receber limite menor. A suíte offline não chama provedores externos.
**Scale/Scope**: Uma solicitação comum por execução comparativa; estratégias iniciais `react` e `plan_and_execute`; seed com cinco serviços e seis alertas; até oito iterações de planejamento.

## Constitution Check

| Gate | Resultado | Evidência / decisão |
|---|---|---|
| Camadas e domínio sem I/O | PASS | Fronteira de comando/agent tool → service → store; regras de estado e validação no domínio/service, ORM somente na store. |
| Fronteiras validadas e contratos explícitos | PASS | Argumentos do comando e schemas de ferramentas são validados com Pydantic; transferências entre camadas usam DTOs. Erros de domínio são convertidos em mensagens/códigos de saída na borda. |
| Segurança de tipos e qualidade | PASS | Tipos em todas as assinaturas; testes de domínio/store/tools e formatadores; `pytest` e `mypy .` previstos para validação de implementação. |
| Acesso async a dados e eficiência | PASS | Tools/services que consultam store usam métodos async de Django e os aguardam; consulta de alertas paginada e limitada a 100; sem execução de ORM sync dentro dos fluxos async. |
| Segurança por padrão | PASS | Segredos vêm do ambiente; validar existência/alvo antes de mutações; resolução de incidente é uma transição não destrutiva e não repete alterações sem necessidade. |
| Especificação aprovada antes da implementação | PASS | Esta fase gera plano e artefatos de design; não inicia implementação. |

**Post-design gate**: PASS. Os contratos separam transporte CLI, lógica de serviço e persistência; os caminhos de execução com modelo são substituíveis nos testes; nenhuma exceção à constituição foi identificada.

## Project Structure

### Documentation (this feature)

```text
specs/001-reasoning-arena/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── arena-cli.md
│   └── agent-tools.md
└── tasks.md              # Gerado pela próxima fase /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── agents/
│   ├── apps.py
│   ├── types.py
│   ├── base.py
│   ├── factory.py
│   ├── tools.py
│   ├── react.py
│   ├── plan_and_execute.py
│   └── management/commands/
│       └── arena.py
├── operations/
│   ├── apps.py
│   ├── models.py
│   ├── domain.py
│   ├── schemas.py
│   ├── store.py
│   ├── services.py
│   ├── migrations/
│   └── management/commands/
│       └── seed_db.py
├── arena.py
└── config/
    └── settings.py

tests/
├── agents/
│   ├── test_types.py
│   ├── test_trace_formatting.py
│   ├── test_react.py
│   ├── test_plan_and_execute.py
│   └── test_arena.py
└── operations/
    ├── test_store.py
    ├── test_services.py
    ├── test_tools.py
    └── test_seed_db.py
```

**Structure Decision**: Manter o projeto Django existente. `operations` é a aplicação de domínio/persistência e registra modelos e o comando de seed; `agents` contém contratos de raciocínio, integração do modelo, adapters de ferramentas e comando Django da arena; `src/arena.py` coordena as execuções e formata a comparação. O comando Django valida argumentos na fronteira e delega à arena. O esqueleto atual não contém apps de negócio, portanto ambos serão registrados em `INSTALLED_APPS`; a descoberta de pacotes em `pyproject.toml` deve incluir os novos apps e subpacotes. Uma migration inicial cria as tabelas operacionais.

## Complexity Tracking

Nenhuma violação da constituição ou camada/projeto adicional precisa de justificativa.
