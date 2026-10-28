# Contexto do Projeto: OpsPilot

OpsPilot é um copiloto de plantão para gerenciamento de alertas e incidentes de produção. A API atua como um agente estruturado em LangChain/LangGraph sobre OpenRouter.

## Stack e Ambiente
- Python 3.14, Django 6.1, LangChain, LangGraph, Pydantic, Pytest, Mypy.
- Sempre ative o ambiente virtual antes de trabalhar: `source .venv/Scripts/activate`.

## Comandos Utilitários
- dev: `python manage.py runserver`
- cli: `python manage.py shell`
- test: `pytest`
- typecheck: `mypy .`
- arena: `python manage.py arena`
- bench: `python manage.py bench`

## Arquitetura e Convenções
- Arquitetura MVC: Model -> Service -> Controller, nada salta camadas.
- O Domínio NUNCA faz I/O. A camada de Services contém as regras de negócio puras e a Store cuida da persistência.
- Utilize sempre **Type Hints** (anotações de tipo) em todas as assinaturas para garantir validação estática estrita.
- Valide todas as entradas HTTP e CLI com schemas Pydantic na fronteira e utilize DTOs entre as camadas.
- Erros de domínio devem ser classes isoladas, traduzidas para respostas apropriadas apenas nas bordas.
- Lógica nova exige testes de domínio. Mantenha `test` e `typecheck` sempre verdes.
- NUNCA versione segredos, senhas ou arquivos `.env`.

## Concorrência e Banco de Dados
- Utilize `await` em todos os repositórios (`*_repo.*()`). NÃO utilize `await` em serviços externos (mantenha-os síncronos).
- Use ORM async nativo; nunca chame ORM síncrono dentro de contextos async. Como `transaction.atomic()` não existe no async, utilize `sync_to_async(transaction.atomic())`.
- Execute consultas independentes em paralelo com `asyncio.gather()`; proteja operações de fan-out com `asyncio.Semaphore`.
- Evite N+1 rigorosamente com `select_related`/`prefetch_related`. Para leitura pura, priorize `values()`/`values_list()`.
- Projete leituras finas usando `.only(*campos)` ou `.defer(*campos)` para não carregar dados desnecessários na RAM.
- Operações de alteração/ingestão em lote devem usar `bulk_create` e `bulk_update` para converter O(N) queries em O(1).
- Métodos de listagem (`list_*`) devem retornar `Tuple[List[Entity], int]`. Paginação é obrigatória (máximo 100 registros por vez).

## Desempenho e Eficiência de Recursos (Big O & Memória)
- **Complexidade de Busca (Big O):** Use `set` ou `dict` para validações de pertincência (`x in colecao`) garantindo busca em O(1) em vez de O(N).
- **Streaming de Dados:** Utilize Generators (`yield`) para processar volumes contínuos de logs/telemetria mantendo o uso de RAM constante em O(1).
- **Consumo de Memória:** Adicione `slots=True` nas dataclasses/entidades de domínio para eliminar o overhead do `__dict__` por objeto.
- **Rede & Caching:** Reutilize conexões via cliente HTTP assíncrono único (HTTP Connection Pool). Aplique cache (`lru_cache` ou Redis) para funções e configurações determinísticas.
- **Serialização Rápida:** Priorize o uso de parsers de alta performance como `orjson` para cenários de I/O intenso.

## Padrão de Commits
- Utilize Conventional Commits (feat:, fix:, chore:, docs:, etc).
- A mensagem deve estar no infinitivo e sem ponto final no término (ex: `feat: criar endpoint de ingestão de alertas`).


## Fluxo de desenvolvimento

Seguir o **Spec Kit** do GitHub Copilot em quatro etapas obrigatórias e em ordem:

```
speckit.specify → speckit.plan → speckit.tasks → speckit.implement
```

1. **`speckit.specify`** — escreve ou atualiza a spec da feature (markdown versionado em `specs/`).
2. **`speckit.plan`** — gera o plano de design e decisões técnicas a partir da spec.
3. **`speckit.tasks`** — decompõe o plano em tarefas ordenadas por dependência.
4. **`speckit.implement`** — executa as tarefas: código, testes verdes, typecheck verde, commit.

Specs são artefatos de primeira classe — criadas, revisadas e versionadas junto com o código. Nenhuma implementação começa sem spec aprovada.

## MCP

Sempre utilize o MCP do context7 para obter a documentação atualizada da linguagem de programação, dependências, frameworks e bibliotecas.