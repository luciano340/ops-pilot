# Modelo de Dados: Erro de saída estruturada inválida

Esta funcionalidade não adiciona persistência nem altera entidades operacionais.

## StructuredOutputError

Erro de aplicação em memória que representa falha ao validar a resposta de uma chamada que exige saída estruturada.

| Campo/atributo | Tipo | Regra |
|---|---|---|
| mensagem | string | Texto estável em inglês, sem conteúdo bruto da resposta nem detalhes de credenciais/provedor. |
| causa | exceção encadeada | `pydantic.ValidationError` original, preservada para diagnóstico sem compor a mensagem exibida. |

O tipo poderá ser tratado por diferentes fronteiras. No escopo atual, a fronteira CLI o converte para `CommandError`; nenhuma serialização HTTP ou interface gráfica será adicionada.
