# Quickstart de Validação

Este roteiro valida o comportamento planejado após a implementação. Testes não devem depender de chamadas reais a OpenRouter.

## Pré-requisitos

- Python 3.14 e dependências do projeto instaladas (`python -m pip install -e ".[dev]"`).
- Ambiente virtual ativo conforme o [README](../../README.md).
- Para execução real da arena: `OPENROUTER_API_KEY` e `OPENROUTER_MODEL` configurados no ambiente. Não são necessários para os testes offline.
- Banco local SQLite padrão ou PostgreSQL via Docker Compose.

## Preparar dados

```powershell
python manage.py migrate
python manage.py seed_db
python manage.py seed_db
```

Esperado: ambas as execuções terminam sem duplicar a amostra; num banco inicialmente vazio há cinco serviços de seed e seis alertas de seed, três `firing` e três `resolved`. Registros preexistentes e não pertencentes à fixture não são apagados.

## Verificar contratos e estratégias offline

```powershell
pytest tests/operations tests/agents
mypy .
```

Esperado: testes de persistência, filtros, schemas, transições, trace, formatação, contagem de chamadas, mesma entrada compartilhada e limite do grafo passam sem credenciais ou tráfego externo.

## Executar uma comparação real

```powershell
python manage.py arena "Liste os alertas firing e resuma os serviços afetados" --strategies react,plan_and_execute --max-iterations 8
```

Esperado: as duas estratégias recebem a mesma solicitação; cada resultado identifica sua resposta, trace cronológico e métricas. A execução pode chamar OpenRouter e alterar registros se a solicitação ordenar ações de escrita.

## Validar rejeições e limite rígido

```powershell
python manage.py arena "Verifique alertas" --strategies unknown
python manage.py arena "Verifique alertas" --max-iterations 9
```

Esperado: ambos os comandos falham na validação antes de iniciar estratégias. Em testes offline, fornecer planos com mais de oito etapas e verificar que no máximo oito iterações são executadas e o resultado indica tarefas não concluídas quando aplicável.

## Validação executada

- `python manage.py seed_db` executado duas vezes: cada execução informou cinco serviços e seis alertas; consultas confirmaram três alertas `firing` e três `resolved`.
- `pytest -q`: 33 testes passaram, sem credenciais OpenRouter.
- `mypy .`: sem problemas em 44 arquivos fonte.
- `python manage.py check` e `python manage.py makemigrations --check --dry-run`: sem problemas e sem migrations pendentes.
- A execução real da arena não foi feita porque depende de credenciais e tráfego externo; use o comando acima somente em ambiente configurado.
