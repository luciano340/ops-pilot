# Feature Specification: API HTTP de Chat

**Feature Branch**: `006-chat-api`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "API HTTP de chat do OpsPilot para executar estratégias de raciocínio existentes, com seleção de estratégia, reflexão opcional, respostas estruturadas, erros previsíveis e timeout."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Executar estratégia de chat (Priority: P1)

Um cliente do OpsPilot envia uma mensagem para receber uma resposta baseada nos
alertas, incidentes e ferramentas operacionais disponíveis. O cliente pode
escolher entre as estratégias `react` e `plan_and_execute`; quando não escolhe,
o sistema usa `react`.

**Why this priority**: É o fluxo central da API e entrega acesso HTTP às
capacidades de raciocínio já existentes no OpsPilot.

**Independent Test**: Enviar uma solicitação válida com uma estratégia
determinística substituta e verificar status 200 e os campos de resposta,
rastreabilidade e métricas, sem chamadas externas.

**Acceptance Scenarios**:

1. **Given** uma solicitação JSON válida sem estratégia, **When** o cliente
   envia `POST /chat`, **Then** o sistema executa `react` e responde com status
   200 contendo `answer`, `trace` e `metrics`.
2. **Given** uma solicitação válida com `strategy` igual a `plan_and_execute`,
   **When** o cliente envia a solicitação, **Then** o sistema executa essa
   estratégia e mantém o mesmo formato de resposta.
3. **Given** uma solicitação válida, **When** o cliente envia um método HTTP
   diferente de POST para a rota, **Then** o sistema não executa uma estratégia
   e informa que o método não é permitido.
4. **Given** que o cliente já utiliza a arena de estratégias, **When** a API de
   chat é disponibilizada, **Then** a arena continua funcionando com as
   estratégias existentes.

---

### User Story 2 - Solicitar reflexão da resposta (Priority: P2)

O cliente pode pedir que a resposta seja revisada por uma etapa de reflexão,
sem precisar escolher um nome de estratégia diferente. A reflexão é opcional e
desativada por padrão.

**Why this priority**: A reflexão melhora a verificação de respostas sem alterar
os nomes públicos das estratégias ou exigir mudanças no cliente para o uso
comum.

**Independent Test**: Enviar a mesma solicitação com `reflect` falso e
verdadeiro usando estratégia e avaliador determinísticos; verificar que a
reflexão só é executada quando solicitada e que a resposta mantém o contrato.

**Acceptance Scenarios**:

1. **Given** uma solicitação válida sem o campo `reflect`, **When** ela é
   processada, **Then** a estratégia base é executada sem avaliador de reflexão.
2. **Given** uma solicitação válida com `reflect` igual a `true`, **When** ela
   é processada, **Then** a resposta passa pela reflexão existente e continua
   identificada pela estratégia base selecionada (`react` ou
   `plan_and_execute`).
3. **Given** um valor de `reflect` que não seja booleano, **When** a solicitação
   é validada, **Then** o sistema retorna erro 400 e não executa a estratégia.

---

### User Story 3 - Receber erros de solicitação compreensíveis (Priority: P3)

O cliente recebe um erro previsível quando o corpo é inválido, a estratégia não
é reconhecida ou a execução ultrapassa o limite de tempo, podendo distinguir
entre erro de entrada, estratégia indisponível e timeout.

**Why this priority**: Erros estáveis permitem que clientes lidem com falhas
sem depender de detalhes internos ou expor informações operacionais.

**Independent Test**: Enviar casos inválidos, uma estratégia desconhecida e
uma execução controladamente lenta; verificar status, código de erro e ausência
de execução para entradas inválidas.

**Acceptance Scenarios**:

1. **Given** JSON malformado, não-objeto, com campos extras ou dados inválidos,
   **When** enviado para `POST /chat`, **Then** o sistema responde 400 com
   `issues` e não inclui valores de entrada sensíveis.
2. **Given** um nome de estratégia não registrado, **When** enviado em um corpo
   válido, **Then** o sistema responde 422 com
   `error.code` igual a `unknown_strategy`.
3. **Given** uma estratégia que não termina em até 180 segundos, **When** o
   prazo é excedido, **Then** o sistema responde 504 com
   `error.code` igual a `strategy_timeout`.
4. **Given** uma falha operacional inesperada durante a execução, **When** a
   requisição falha, **Then** o cliente não recebe uma resposta de sucesso
   simulada nem detalhes internos ou stack trace.
5. **Given** uma solicitação cuja execução ainda está em andamento, **When**
   outro cliente envia uma solicitação independente, **Then** o serviço
   continua processando a segunda solicitação sem aguardar a primeira terminar.

### Edge Cases

- Mensagem ausente, vazia ou composta somente por espaços deve ser rejeitada
  com status 400.
- Corpo vazio, JSON malformado ou JSON cujo valor raiz não seja um objeto deve
  resultar em erro 400 com o formato de erro definido.
- Campos desconhecidos devem ser rejeitados; `strategy` deve ser uma string
  não vazia, e um nome não suportado deve ser distinguido de um erro de formato.
- Um nome de estratégia válido em formato, mas não registrado, deve resultar
  em 422, e não 400.
- `reflect` ausente equivale a `false`; valores que não sejam booleanos são
  inválidos.
- Se a estratégia exceder 180 segundos, a API deve terminar a espera e
  responder 504; não deve retornar posteriormente uma segunda resposta para a
  mesma requisição.
- Erros de validação não devem serializar o valor recusado nem outros dados da
  mensagem do cliente.
- Falhas de configuração ou de serviços externos não devem ser convertidas em
  respostas HTTP 200 ou em erros de entrada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST disponibilizar `POST /chat` para processar uma
  solicitação de raciocínio operacional.
- **FR-002**: O corpo da solicitação MUST ser um objeto JSON com `message`
  obrigatório e não vazio; `strategy` opcional com padrão `react`; e `reflect`
  opcional com padrão `false`.
- **FR-003**: O sistema MUST rejeitar campos extras, tipos incorretos, mensagem
  vazia ou somente com espaços e JSON malformado com HTTP 400. A resposta MUST
  conter `{ "issues": [...] }` com detalhes de validação sem valores de entrada
  sensíveis.
- **FR-004**: O sistema MUST aceitar os nomes de estratégia registrados
  `react` e `plan_and_execute`. Um nome não registrado MUST produzir HTTP 422
  com `{ "error": { "code": "unknown_strategy", "message": "..." } }`.
- **FR-005**: O campo `reflect` MUST controlar a aplicação da reflexão
  existente à estratégia selecionada, sem exigir nomes de estratégia
  compostos. Na ausência do campo, a reflexão MUST permanecer desativada.
- **FR-006**: Uma execução concluída MUST retornar HTTP 200 com os campos
  `answer`, `trace` e `metrics`. `trace` MUST preservar os eventos tipados e
  seus dados de ação quando presentes; `metrics` MUST conter `llm_calls` e
  `latency_ms`.
- **FR-007**: A execução MUST ter limite de 180 segundos. Ao excedê-lo, o
  sistema MUST responder HTTP 504 com
  `{ "error": { "code": "strategy_timeout", "message": "..." } }`.
- **FR-008**: Enquanto uma solicitação aguarda a estratégia selecionada, o
  serviço MUST permanecer disponível para receber e processar outras
  solicitações independentes.
- **FR-009**: Falhas operacionais MUST ser distinguidas de erros de entrada e
  nunca produzir respostas de sucesso simuladas, stack traces ou detalhes
  internos no corpo da resposta.
- **FR-010**: O endpoint MUST disponibilizar as estratégias existentes
  `react` e `plan_and_execute`, preservar os contratos de trace e métricas
  existentes e aplicar a reflexão existente quando solicitada, sem duplicar o
  comportamento de raciocínio.
- **FR-011**: Os testes de integração MUST cobrir sucesso e formato da resposta,
  validação 400, estratégia desconhecida 422, reflexão ligada e desligada, e
  timeout 504 usando uma estratégia fake determinística, sem rede ou serviços
  externos e sem exigir credenciais.
- **FR-012**: A mudança MUST preservar o comportamento existente da arena e das
  estratégias de raciocínio.

### Key Entities *(include if feature involves data)*

- **Solicitação de chat**: mensagem do cliente, nome opcional da estratégia e
  preferência booleana de reflexão.
- **Resultado de estratégia**: resposta textual, sequência de eventos de trace
  e métricas de execução.
- **Evento de trace**: evento tipado de raciocínio, ação, observação, plano,
  crítica ou resposta; eventos de ação podem incluir ferramenta e argumentos.
- **Erro da API**: erro estruturado que distingue problemas de validação,
  estratégia desconhecida e timeout sem revelar dados sensíveis.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das solicitações válidas de teste retornam HTTP 200 com
  `answer`, `trace` e `metrics`, incluindo as chaves `llm_calls` e
  `latency_ms`.
- **SC-002**: 100% dos corpos inválidos cobertos pelos testes retornam HTTP 400
  com `issues`, e nenhum executa a estratégia.
- **SC-003**: 100% dos testes com estratégia desconhecida retornam HTTP 422
  com código `unknown_strategy`.
- **SC-004**: Uma execução que excede 180 segundos retorna HTTP 504 com código
  `strategy_timeout`, em vez de aguardar indefinidamente.
- **SC-005**: Todos os testes de integração do endpoint passam sem acesso à
  rede, credenciais ou serviços externos.
- **SC-006**: O cliente pode usar reflexão sem alterar o nome da estratégia
  solicitada e pode omiti-la para manter o comportamento padrão sem reflexão.
- **SC-007**: Uma solicitação independente pode ser atendida enquanto outra
  estratégia ainda está em execução, sem aguardar sua conclusão.

## Assumptions

- A API é uma interface HTTP de requisição/resposta; streaming,
  persistência de conversas e histórico não fazem parte desta versão.
- A autenticação/autorização da API não é introduzida por esta funcionalidade;
  o acesso segue os controles já aplicados no ambiente onde o serviço é
  executado.
- Os nomes `react` e `plan_and_execute`, a reflexão e os formatos de resultado
  correspondem aos contratos já existentes no OpsPilot; a especificação não
  introduz novas estratégias de raciocínio.
- Os detalhes de validação em `issues` e a mensagem de erros estruturados
  devem ser estáveis e seguros para clientes, sem expor conteúdo da mensagem,
  credenciais, stack trace ou detalhes do provedor.
- O endpoint será integrado ao serviço HTTP e deverá reutilizar os recursos de
  raciocínio, reflexão, trace e métricas já disponíveis no OpsPilot.
- Os testes poderão substituir a execução real por uma estratégia
  determinística, sem depender de credenciais ou serviços externos.
