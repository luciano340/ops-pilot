# Implementation Plan: API HTTP de Chat

**Branch**: `006-chat-api` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-chat-api/spec.md`

## Summary

Expor as estratégias `react` e `plan_and_execute` por `POST /chat`, validando o
JSON com Pydantic e retornando o resultado já definido pelos contratos de
estratégia. Uma camada de serviço selecionará e construirá a estratégia pelo
registry existente a criar, aplicará o decorator de reflexão quando solicitado
e imporá o limite de 180 segundos. A view Django será responsável por traduzir
erros de validação, seleção, timeout e execução para respostas HTTP seguras.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Django 6.1, Pydantic 2, LangChain/LangGraph e
`langchain-openai`; todos já presentes no `pyproject.toml`.

**Storage**: Sem novas tabelas ou persistência. A execução reutiliza os
serviços e o armazenamento operacional existentes somente através das
ferramentas do agente.

**Testing**: Pytest, pytest-django e `django.test.AsyncClient`; testes offline
com uma estratégia determinística substituindo o registry e sem credenciais do
OpenRouter. Mypy estrito é critério de qualidade do projeto.

**Target Platform**: Serviço Django Python executado localmente ou em
container. O projeto já expõe `config.asgi:application`; o servidor Django
integrado documentado é de desenvolvimento.

**Project Type**: Aplicação web/API Django, com a aplicação `agents` existente
e camadas internas de estratégia.

**Performance Goals**: Encerrar a espera da estratégia em até 180 segundos e
permitir que solicitações independentes avancem enquanto uma execução aguarda
I/O assíncrono.

**Constraints**: Preservar os contratos públicos e a arena existentes; não
bloquear o event loop; validar entradas na borda; não expor valores de entrada,
credenciais, stack traces ou detalhes internos em respostas de erro; manter os
testes sem rede.

**Scale/Scope**: Um endpoint de chat sem streaming, sessão, histórico,
persistência de conversa, autenticação nova ou novas estratégias de raciocínio.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Estado | Aplicação ao plano |
|---|---|---|
| I. Arquitetura em camadas e pureza do domínio | PASS | View HTTP traduz transporte; serviço coordena a execução; estratégias e ferramentas existentes preservam regras e persistência. Nenhuma lógica de negócio ou I/O é movida para domínio. |
| II. Fronteiras validadas e contratos explícitos | PASS | Schema Pydantic dedicado valida o corpo antes do serviço; resultado e erros atravessam camadas como modelos/erros tipados. |
| III. Segurança de tipos e critérios de qualidade | PASS | Assinaturas novas terão type hints; testes offline e Mypy cobrem a alteração. |
| IV. Acesso assíncrono a dados e eficiência | PASS | View e serviço aguardam estratégia assíncrona; ferramentas já usam serviços e APIs assíncronas do ORM. Timeout cancela a espera sem bloquear o event loop. |
| V. Segurança por padrão | PASS | Erros de validação omitem o input; respostas não expõem stack trace nem segredo; testes não usam credenciais. |
| Desenvolvimento orientado por especificações | PASS | Spec aprovada precede plano; tarefas e implementação permanecem para fases posteriores. |

**Gate result**: PASS. A implementação não requer migração nem alteração de
dependências. Para obter concorrência eficiente de requisições com views
assíncronas, ambientes de implantação devem servir a aplicação ASGI; o
servidor embutido atual continua sendo apenas para desenvolvimento, conforme
documentação do projeto.

## Project Structure

### Documentation (this feature)

```text
specs/006-chat-api/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── chat-api.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # Criado por /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── config/
│   ├── asgi.py
│   └── urls.py                         # Integrar a rota /chat
└── agents/
    ├── schemas.py                      # Manter schemas dos comandos existentes
    ├── chat_schemas.py                 # DTO Pydantic da requisição HTTP
    ├── registry.py                     # Registro dos builders das estratégias
    ├── chat_service.py                 # Seleção, reflexão e timeout
    └── views.py                        # Validação HTTP e serialização de erros

tests/
└── agents/
    └── test_chat_api.py                # Testes Django assíncronos do contrato
```

Os módulos propostos integram a aplicação `agents` que já está instalada; não
se cria uma aplicação Django nem uma camada de armazenamento nova. Os nomes são
direcionais para a fase de tarefas e devem ser ajustados somente se a inspeção
durante implementação identificar convenção mais apropriada.

**Structure Decision**: Manter o endpoint na aplicação `agents`, que contém os
contratos `ReasoningStrategy`, `StrategyResult`, as estratégias, a reflexão, a
fábrica de modelo e as ferramentas. `config.urls` conecta o controller. O
schema HTTP fica separado dos schemas de CLI existentes. O serviço de chat
coordena dependências e aplicação da estratégia sem assumir responsabilidades
de transporte.

## Constitution Check (Post-Design)

| Princípio | Estado | Verificação do design |
|---|---|---|
| I. Camadas e domínio sem I/O | PASS | `views.py` fica na borda, `chat_service.py` coordena e os componentes existentes continuam donos da execução e persistência. |
| II. Validação e DTOs | PASS | `ChatRequest` Pydantic é validado antes do serviço; `StrategyResult` e erros nomeados formam contratos entre componentes. |
| III. Tipos e qualidade | PASS | Limites dos módulos e testes estão definidos; toda nova assinatura deve ser tipada, testada e verificada com Mypy. |
| IV. Assincronia e eficiência | PASS | Execução usa `await`; limite será aplicado ao await, e execução concorrente será validada no caminho ASGI. |
| V. Segurança | PASS | Só campos de erro permitidos serão serializados; exceções inesperadas serão registradas no servidor e retornadas como erro genérico. |

**Post-design gate result**: PASS. Sem violações que exijam Complexity
Tracking.

## Complexity Tracking

Não há violações da constituição ou estruturas adicionais que exijam
justificativa.
