# Contrato: Falhas de saída estruturada

## Erro compartilhável da aplicação

- A interpretação inválida de uma resposta estruturada de planejamento ou replanejamento é sinalizada por um tipo identificável de erro de aplicação.
- O erro apresenta a mensagem:

  ```text
  The model returned an invalid structured response. Please retry or choose a model that supports structured outputs.
  ```

- A mensagem não contém o JSON inválido, dados do pedido, segredos ou detalhes variáveis do provedor.
- A causa técnica original permanece disponível como exceção encadeada; interfaces não devem usar a mensagem da causa como texto para o usuário.

## Fronteira CLI

- O comando `arena` traduz o erro compartilhável em uma falha de comando com a mensagem acima.
- O comando termina com erro não zero e não imprime traceback para essa falha conhecida.
- Erros de rede, credenciais, ferramentas e outras falhas não são reclassificados como saída estruturada inválida.
- Resultados de estratégia válidos permanecem no formato atual de resposta, trace e métricas.

## Extensibilidade

Uma futura borda HTTP/UI pode capturar o erro tipado e mapear para o contrato de transporte apropriado sem depender de `CommandError`. A resposta HTTP/UI não faz parte deste contrato atual.
