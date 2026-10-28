# Modelo de Dados: Contexto de ferramentas para planejamento

Esta funcionalidade não adiciona persistência nem modifica entidades operacionais.

## AvailableToolContext

Representação transitória de uma ferramenta já fornecida à estratégia e disponibilizada ao modelo planejador.

| Campo | Origem | Regra |
|---|---|---|
| `name` | Nome da ferramenta registrada | Identifica exatamente a operação que o executor pode chamar. |
| `description` | Descrição registrada | Explica a capacidade e seu propósito operacional. |
| `args_schema` | Schema da ferramenta | Descreve os argumentos aceitos, campos requeridos e restrições declaradas. |

## Relações e validação

- O catálogo é composto exclusivamente pelas ferramentas recebidas no construtor da estratégia.
- Cada ferramenta anunciada ao planner está também vinculada ao executor existente.
- O executor continua validando os argumentos ao invocar a ferramenta.
- O catálogo não contém credenciais nem resultados de execução.
- Um resultado só confirma ação quando o executor invoca a ferramenta e registra sua observação.
