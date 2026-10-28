# Feature Specification: Mensagem amigável para saída estruturada inválida

**Feature Branch**: `002-friendly-structured-output-errors`

**Created**: 2026-10-28

**Status**: Approved

**Input**: User description: "Ajustar o código para que, caso ocorra esse tipo de erro na saída estruturada do modelo, uma mensagem mais amigável em inglês seja mostrada no CLI e possa ser reutilizada futuramente na UI."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Entender falhas de saída do modelo (Priority: P1)

Quando uma estratégia recebe uma resposta estruturada incompleta ou inválida do modelo, a pessoa que executa a arena recebe uma mensagem concisa em inglês, em vez de um traceback técnico.

**Why this priority**: O erro interrompe a execução da arena e atualmente expõe detalhes internos que não ajudam a pessoa a resolver o problema.

**Independent Test**: Simular uma resposta de modelo que não pode ser validada e verificar que a execução da estratégia falha com uma mensagem estável e compreensível; executar o comando e verificar que a mensagem aparece sem traceback.

**Acceptance Scenarios**:

1. **Given** uma estratégia recebe conteúdo estruturado inválido do modelo, **When** a resposta é interpretada, **Then** a falha é representada por um erro identificável e uma mensagem amigável em inglês, sem incluir o conteúdo bruto da resposta.
2. **Given** a arena recebe esse erro durante a execução, **When** o comando termina, **Then** o CLI apresenta a mensagem amigável e não imprime um traceback.
3. **Given** uma falha não relacionada à validação da saída estruturada, **When** ocorre durante a execução, **Then** ela não é mascarada como erro de saída estruturada.

### Edge Cases

- Uma resposta truncada durante o planejamento inicial e uma resposta inválida durante o replanejamento devem receber o mesmo tratamento amigável.
- Uma resposta válida continua a produzir o resultado normal, sem alterar trace, resposta ou métricas.
- A mensagem apresentada não deve depender do texto variável da exceção do provedor nem revelar conteúdo da resposta do modelo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST identificar falhas de validação de respostas estruturadas produzidas durante o planejamento e o replanejamento.
- **FR-002**: O sistema MUST expor essas falhas por meio de um erro identificável, com uma mensagem concisa e em inglês apropriada para apresentação ao usuário.
- **FR-003**: O CLI MUST apresentar a mensagem amigável para essas falhas sem imprimir traceback.
- **FR-004**: A mensagem apresentada MUST NOT incluir o conteúdo bruto da resposta inválida nem substituir falhas não relacionadas por uma mensagem de saída estruturada inválida.
- **FR-005**: A representação do erro MUST poder ser consumida por interfaces além do CLI sem depender da formatação de saída do comando.
- **FR-006**: Respostas estruturadas válidas e os demais comportamentos da arena MUST permanecer inalterados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos testes para saídas estruturadas inválidas no planejamento e replanejamento verificam o mesmo tipo de erro e mensagem amigável.
- **SC-002**: 100% dos testes de execução da arena para essa falha confirmam que a mensagem aparece sem traceback.
- **SC-003**: 100% dos testes de regressão para respostas válidas e erros não relacionados confirmam que seus comportamentos permanecem distintos e inalterados.

## Assumptions

- Uma resposta que não atende ao formato estruturado esperado, inclusive JSON truncado, é a falha abrangida por esta funcionalidade.
- A mensagem será em inglês e orientará a pessoa a tentar novamente ou usar um modelo compatível com saída estruturada, sem afirmar uma causa específica que a aplicação não consiga verificar.
- A interface futura poderá traduzir o erro identificável para sua própria resposta, mas a implementação de UI não faz parte deste escopo.
