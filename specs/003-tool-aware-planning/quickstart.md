# Quickstart: Validar planejamento ciente das ferramentas

## Pré-requisitos

- Ambiente virtual e dependências do projeto instaladas.
- Testes offline não precisam de credenciais OpenRouter.
- No PowerShell com política que bloqueie `Activate.ps1`, use `.\.venv\Scripts\python.exe`.

## Testes de estratégia

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\agents\test_plan_and_execute.py
```

Esperado:

- O prompt/contexto do planejador contém ferramentas e schemas fornecidos.
- Um pedido compatível produz uma etapa e o executor chama a ferramenta esperada.
- Pedido sem ferramenta não é reportado como executado.
- Campos obrigatórios não são fabricados.
- Pedidos informativos, limite de iteração, trace e métricas mantêm comportamento esperado.

## Verificações gerais

```powershell
.\.venv\Scripts\python.exe -m mypy .
.\.venv\Scripts\python.exe -m pytest -q
```

## Exercício manual seguro

Com credenciais e banco de demonstração configurados, solicite uma consulta sem mutações:

```text
python manage.py arena "Liste os alertas firing e resuma os serviços afetados" --strategies plan_and_execute --max-iterations 8
```

O trace deve mostrar etapa de planejamento e chamada `list_alerts`, seguida de observação. Para testar `open_incident`, use ambiente descartável e forneça os campos obrigatórios; a execução cria registro persistente.
