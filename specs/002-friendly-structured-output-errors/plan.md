# Implementation Plan: Mensagens amigáveis para saída estruturada inválida

**Branch**: `002-friendly-structured-output-errors` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-friendly-structured-output-errors/spec.md`

## Summary

Traduzir falhas de validação da saída estruturada no planejamento e replanejamento para um erro de aplicação tipado, com mensagem concisa em inglês, e apresentar esse erro como `CommandError` na fronteira CLI. O tipo de erro ficará independente da formatação do comando para permitir tratamento futuro em outras interfaces. Capturas ficam restritas a `pydantic.ValidationError` e não mascaram erros não relacionados.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Django 6.1, Pydantic 2, `langchain-core`, `langchain-openai`, `langgraph`

**Storage**: N/A; não há dados persistidos para esta funcionalidade.

**Testing**: Pytest, pytest-django e Mypy em modo estrito. Testes de estratégia e do comando usam doubles, sem credenciais nem chamadas externas.

**Target Platform**: CLI Django em Windows/Linux e contêiner Linux; o tipo de erro também poderá ser traduzido por futura interface HTTP.

**Project Type**: Aplicação Django com estratégia de agente e comando CLI.

**Performance Goals**: Sem impacto mensurável no caminho de sucesso; falhas inválidas devem ser traduzidas durante o tratamento já executado.

**Constraints**: Preservar respostas válidas e erros não relacionados. Não expor conteúdo bruto inválido, credenciais ou detalhes internos do provedor na mensagem apresentada.

**Scale/Scope**: Duas fronteiras de resposta estruturada (planejador e replanejador), uma classe de erro compartilhável, tradução na CLI e testes offline correspondentes. UI futura fora do escopo.

## Constitution Check

| Gate | Resultado | Evidência / decisão |
|---|---|---|
| Arquitetura em camadas e domínio sem I/O | PASS | O erro de aplicação será definido em `agents`, a estratégia converte a falha no limite de integração do modelo e o comando CLI traduz o erro para `CommandError`. Não há I/O novo no domínio. |
| Fronteiras validadas e contratos explícitos | PASS | A CLI permanece a borda de apresentação. O erro identificado poderá ser convertido em resposta por uma futura borda HTTP sem acoplar a estratégia ao CLI. |
| Segurança de tipos e qualidade | PASS | Assinaturas tipadas; testes offline cobrem estratégia e comando; executar pytest focado e Mypy. |
| Acesso async a dados e eficiência | PASS | Nenhuma alteração em persistência ou acesso a dados. |
| Segurança por padrão | PASS | A mensagem não inclui resposta bruta do modelo nem dados secretos. Não haverá captura ampla que esconda falhas inesperadas. |
| Spec Kit e aprovação humana | PASS | A especificação foi revisada e aprovada antes desta fase de design. |

## Research Summary

- Pydantic 2 lança `ValidationError` quando dados não satisfazem um modelo. A validação de respostas estruturadas ocorre dentro do fluxo `with_structured_output` e também é validada explicitamente pela estratégia; ambos os locais podem ser delimitados sem capturar exceções gerais.
- O traceback reportado termina em validação Pydantic de JSON incompleto durante a saída estruturada de `PlanReview`, tornando `ValidationError` o tipo de falha comprovadamente relevante para esta correção.
- A CLI Django já traduz exceções de configuração para `CommandError`; usar o mesmo padrão evita traceback no caminho normal de erro do comando.
- Mensagem padrão proposta: `The model returned an invalid structured response. Please retry or choose a model that supports structured outputs.`
- Consulte [research.md](./research.md) para decisões e alternativas.

## Project Structure

### Documentation (this feature)

```text
specs/002-friendly-structured-output-errors/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── structured-output-errors.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
└── agents/
    ├── errors.py
    ├── plan_and_execute.py
    └── management/
        └── commands/
            └── arena.py

tests/
└── agents/
    ├── test_plan_and_execute.py
    └── test_arena_command.py
```

**Structure Decision**: Preservar o app `agents` existente. Adicionar nele um erro compartilhável; traduzir falhas estruturadas na estratégia Plan-and-Execute e converter o erro tipado para a exceção apresentada pelo comando Django. Estender os testes offline existentes, sem criar novos subsistemas ou dependências.

## Complexity Tracking

Nenhuma violação da constituição ou camada/projeto adicional precisa de justificativa.
