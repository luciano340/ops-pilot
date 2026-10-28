# Quickstart: Validar mensagens amigáveis para saída estruturada inválida

## Pré-requisitos

- Ambiente virtual e dependências de desenvolvimento instaladas.
- Nenhuma credencial OpenRouter necessária; os cenários usam modelos falsos.
- No PowerShell com política que bloqueie `Activate.ps1`, use diretamente `.\.venv\Scripts\python.exe`.

## Executar os testes focados

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\agents\test_plan_and_execute.py tests\agents\test_arena_command.py
```

Esperado: testes para saídas inválidas no planejamento e replanejamento verificam o mesmo erro tipado; teste do comando verifica a mensagem legível sem traceback; respostas válidas e falhas não relacionadas mantêm seu comportamento.

## Verificações de qualidade

```powershell
.\.venv\Scripts\python.exe -m mypy .
.\.venv\Scripts\python.exe -m pytest -q
```

Esperado: Mypy e a suíte offline terminam sem erros.

## Exercício manual da CLI

Após configurar credenciais e um modelo compatível em ambiente seguro, execute:

```text
python manage.py arena "Liste os alertas firing" --strategies plan_and_execute --max-iterations 8
```

Uma resposta estruturada inválida deve terminar com mensagem curta e código diferente de zero, sem traceback. Não é necessário gerar deliberadamente respostas defeituosas via provedor: os testes offline validam esse cenário de forma determinística.
