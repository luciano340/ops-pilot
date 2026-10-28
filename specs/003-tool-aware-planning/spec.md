# Feature Specification: Planejamento ciente das ferramentas disponíveis

**Feature Branch**: `003-tool-aware-planning`

**Created**: 2026-10-28

**Status**: Approved

**Input**: User description: "Corrigir o Plan-and-Execute para reconhecer e usar as ferramentas operacionais disponíveis, em vez de responder que não tem acesso quando uma ferramenta apropriada como open_incident existe."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Planejar ações com ferramentas disponíveis (Priority: P1)

Quando uma pessoa solicita uma operação que uma ferramenta disponível pode executar, o assistente inclui essa operação no plano e a encaminha ao executor, em vez de responder que não tem acesso ou terminar com um plano vazio.

**Why this priority**: Um pedido operacional pode ser ignorado sem erro visível quando o planejador não sabe quais ferramentas o executor pode usar.

**Independent Test**: Usar modelo falso que retorna uma etapa de abertura de incidente e uma chamada de ferramenta; verificar que o plano inclui a etapa, que `open_incident` é chamada e que a resposta final reflete o resultado confirmado pela ferramenta.

**Acceptance Scenarios**:

1. **Given** uma ferramenta apropriada está disponível e a solicitação pede explicitamente uma ação que ela suporta, **When** o planejamento é feito, **Then** o plano contém uma etapa que encaminha a solicitação ao executor, em vez de um plano vazio e uma alegação de falta de acesso.
2. **Given** o plano contém uma etapa operacional, **When** o executor age, **Then** ele só pode chamar ferramentas disponíveis e o trace registra a ação e a observação.
3. **Given** uma solicitação pede uma operação sem ferramenta disponível, **When** o plano é criado, **Then** o sistema não afirma que executou essa operação e informa que a capacidade não está disponível.
4. **Given** uma solicitação combina ações suportadas e não suportadas, **When** o plano é executado, **Then** as ações suportadas são planejadas/executadas e as não suportadas permanecem explicitamente não executadas.

### Edge Cases

- Solicitações informativas que não exigem ferramentas ainda podem produzir resposta direta com plano vazio.
- Uma ferramenta disponível pode não ser suficiente por faltar um argumento obrigatório; a estratégia não deve inventar fatos operacionais e deve solicitar esclarecimento ou sinalizar o dado ausente.
- A descrição das ferramentas e seus argumentos deve ser apresentada ao planejador sem expor conteúdo secreto.
- O executor pode produzir texto sem chamada de ferramenta; isso não deve ser registrado como ação executada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O planejador MUST receber informações sobre as ferramentas disponíveis e as operações que cada uma pode executar.
- **FR-002**: Para uma solicitação de ação compatível com uma ferramenta disponível, o planejador MUST produzir uma ou mais etapas operacionais, em vez de concluir diretamente com plano vazio.
- **FR-003**: O planejador MUST distinguir operações disponíveis de operações que não são suportadas pelas ferramentas fornecidas.
- **FR-004**: A estratégia MUST executar etapas usando apenas ferramentas disponíveis e MUST registrar ações e observações no trace.
- **FR-005**: A resposta MUST NOT alegar sucesso para uma ação sem confirmação da ferramenta.
- **FR-006**: Solicitações que não exigem ação e não correspondem a operação disponível MUST continuar podendo terminar sem etapas.
- **FR-007**: A estratégia MUST preservar o comportamento de limite de iterações, tratamento de saída estruturada inválida e contagem de chamadas do modelo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos testes offline para pedidos que correspondem a ferramentas disponíveis verificam que o planejamento inclui etapas e que a ação é encaminhada à ferramenta esperada.
- **SC-002**: 100% dos testes para operações não suportadas confirmam que não há chamada a ferramenta nem alegação de execução.
- **SC-003**: 100% dos testes de regressão para solicitações informativas e limites de iteração confirmam que o comportamento existente é preservado.

## Assumptions

- As ferramentas fornecidas ao construtor da estratégia são a fonte autoritativa das capacidades disponíveis.
- A execução de uma ferramenta continua sendo responsabilidade do executor; o planejador apenas identifica etapas necessárias.
- A ferramenta atual `open_incident` exige título, serviço e severidade; valores ausentes não devem ser inventados sem uma regra de produto.
- A ferramenta existente `resolve_incident` resolve incidentes, mas não existe ferramenta dedicada a encerrar alertas; esta feature não adiciona novas ferramentas operacionais.
- Não há interface gráfica implementada; a melhoria atua no comportamento da estratégia e no trace.
