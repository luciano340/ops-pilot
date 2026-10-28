# Research: Mensagens amigáveis para saída estruturada inválida

## Falha de validação estruturada

- **Decision**: Interceptar `pydantic.ValidationError` no limite das chamadas estruturadas de planejamento e replanejamento e relançá-la como um erro de aplicação identificável, com uma mensagem estável em inglês.
- **Rationale**: O traceback observado é uma `ValidationError` levantada pela validação de JSON da resposta para `PlanReview`. A validação explícita subsequente dos objetos `Plan` e `PlanReview` também usa Pydantic. Delimitar a captura a essas operações evita tratar erros de transporte, ferramenta ou execução como se fossem resposta estruturada inválida.
- **Alternatives considered**:
  - Capturar `Exception` em torno da estratégia inteira: rejeitada porque esconderia falhas não relacionadas e produziria diagnóstico enganoso.
  - Usar somente `CommandError`: rejeitada porque vincularia a falha de aplicação ao CLI e dificultaria seu tratamento por futura UI.
  - Exibir `str(ValidationError)`: rejeitada porque pode conter detalhes técnicos ou conteúdo variável, além de não ser uma mensagem estável.

## Apresentação pelo CLI

- **Decision**: Converter o erro tipado para `django.core.management.CommandError` na fronteira do comando `arena`.
- **Rationale**: O padrão Django encerra o comando com erro legível, sem apresentar traceback para falhas conhecidas do comando. O erro original permanece encadeado para diagnóstico interno.
- **Alternatives considered**:
  - Imprimir mensagem e retornar como sucesso: rejeitada porque uma execução falha não pode parecer bem-sucedida.
  - Converter erros de modelo diretamente no `handle` sem tipo intermediário: rejeitada porque o fluxo da estratégia seria inacessível a uma futura borda HTTP.

## Referências

- Pydantic 2 documenta que erros de validação resultam em `ValidationError`: [Errors](https://docs.pydantic.dev/latest/errors/errors/).
- O projeto já usa `BaseModel.model_validate` nas fronteiras estruturadas e `CommandError` no comando Django para falhas de configuração.
- O suporte de saída estruturada depende do método/provedor do modelo; a mensagem deve orientar sem declarar que um modelo específico é a causa comprovada.
