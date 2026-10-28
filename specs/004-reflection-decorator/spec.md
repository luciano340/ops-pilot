# Feature Specification: Reflection Decorator

**Feature Branch**: `004-reflection-decorator`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Adicionar uma camada de reflexão às estratégias de raciocínio do OpsPilot para avaliar respostas com base na solicitação e nas observações registradas, corrigir respostas reprovadas dentro de um limite configurável, registrar as críticas e consolidar métricas, com seleção na arena e testes sem chamadas externas."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Revisar e corrigir uma resposta operacional (Priority: P1)

Quando uma pessoa pede ao OpsPilot uma análise ou orientação, o assistente verifica se a resposta proposta atende à solicitação e corresponde às observações disponíveis. Se a revisão encontrar problemas, o assistente usa o feedback para tentar novamente, entregando uma resposta corrigida ou a última resposta disponível quando o limite de correções for atingido.

**Why this priority**: Respostas não verificadas podem omitir a solicitação ou contradizer evidências observadas durante o raciocínio. Uma revisão limitada melhora a confiabilidade sem permitir tentativas ilimitadas.

**Independent Test**: Fornecer respostas e resultados de revisão controlados; verificar a aprovação imediata, uma reprovação seguida de aprovação e reprovações até o limite, sem depender de serviços externos.

**Acceptance Scenarios**:

1. **Given** a resposta inicial atende à solicitação e está alinhada às observações, **When** ela é revisada, **Then** o assistente a retorna sem executar uma correção adicional.
2. **Given** a resposta inicial é reprovada e há correções disponíveis, **When** o assistente recebe o feedback, **Then** ele executa outra tentativa com esse feedback e revisa a nova resposta.
3. **Given** cada tentativa é reprovada, **When** o limite de correções é alcançado, **Then** o assistente encerra o ciclo e retorna a resposta da última tentativa, sem iniciar outra.
4. **Given** uma revisão aprova uma resposta após uma ou mais correções, **When** o ciclo termina, **Then** nenhuma tentativa adicional é executada.

### User Story 2 - Escolher uma estratégia com reflexão e inspecionar sua execução (Priority: P2)

Quando uma pessoa executa a arena, ela pode escolher a reflexão para qualquer um dos modos de raciocínio suportados. O resultado inclui as revisões feitas e métricas que representam o trabalho total da execução.

**Why this priority**: A reflexão deve ser opt-in e acessível nos modos existentes, enquanto os registros permitem entender como uma resposta final foi obtida.

**Independent Test**: Executar cada modo suportado com resultados controlados e confirmar a seleção pela arena, os eventos de crítica na ordem correta e a soma das métricas de todas as tentativas e avaliações.

**Acceptance Scenarios**:

1. **Given** uma pessoa seleciona reflexão com ReAct na arena, **When** a execução começa, **Then** a reflexão envolve esse modo e mantém o contrato de resposta existente.
2. **Given** uma pessoa seleciona reflexão com Plan-and-Execute na arena, **When** a execução começa, **Then** a reflexão envolve esse modo e mantém o contrato de resposta existente.
3. **Given** uma ou mais revisões ocorrem, **When** a execução é apresentada, **Then** cada revisão aparece como evento de crítica com seu resultado e feedback.
4. **Given** existem métricas de várias tentativas e avaliações, **When** a execução termina, **Then** a latência e as chamadas ao modelo reportadas correspondem à soma de todas as etapas.

### Edge Cases

- Se o trace não contiver observações, a revisão ainda considera a solicitação e a resposta, sem inventar evidências.
- Se a resposta permanecer reprovada ao atingir o limite, a execução termina com a última resposta e mantém o feedback de reprovação no trace.
- Se o avaliador não produzir uma avaliação estruturada válida, a falha deve ser explícita e não deve ser tratada como aprovação.
- O limite de correções é zero: a resposta inicial ainda é avaliada, mas nenhuma correção adicional é executada.
- O uso de reflexão não deve alterar o comportamento dos modos existentes quando a reflexão não for selecionada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir envolver cada estratégia de raciocínio suportada com uma etapa de reflexão, preservando o contrato de execução e resultado já utilizado pelas estratégias.
- **FR-002**: O sistema MUST avaliar a resposta inicial e cada resposta corrigida quanto à precisão em relação à solicitação e à consistência com as observações registradas no trace.
- **FR-003**: A avaliação MUST usar o mesmo modelo de linguagem configurado para a estratégia executada e produzir uma decisão explícita de aprovação ou reprovação e feedback textual; uma avaliação inválida MUST ser reportada como falha, nunca como aprovação implícita.
- **FR-004**: Quando uma avaliação reprovar a resposta e ainda houver correções permitidas, o sistema MUST fornecer o feedback à próxima execução da estratégia e avaliar a resposta resultante.
- **FR-005**: O sistema MUST encerrar a reflexão imediatamente após uma aprovação ou quando alcançar o limite de correções; o limite padrão MUST ser duas correções.
- **FR-006**: Ao alcançar o limite sem aprovação, o sistema MUST retornar a resposta da última tentativa e preservar no trace o resultado da última avaliação.
- **FR-007**: O sistema MUST acrescentar um evento de crítica identificado como `critique` para cada avaliação, incluindo a decisão e o feedback, em ordem cronológica com os demais eventos da execução.
- **FR-008**: O sistema MUST reportar a latência e o total de chamadas ao modelo acumulados entre todas as tentativas da estratégia e avaliações.
- **FR-009**: A arena MUST permitir selecionar a reflexão com ReAct usando `reflect:react` e com Plan-and-Execute usando `reflect:plan_and_execute`.
- **FR-010**: A execução sem reflexão MUST preservar o comportamento existente das estratégias e da arena.
- **FR-011**: Os fluxos de aprovação, correção, limite, rastreabilidade e métricas MUST poder ser verificados deterministicamente sem chamadas de rede externas.

### Key Entities

- **Resposta da estratégia**: A resposta proposta, acompanhada do trace e das métricas da execução.
- **Avaliação crítica**: Decisão de aprovação ou reprovação e feedback sobre a resposta em relação ao pedido e às observações.
- **Tentativa de correção**: Uma nova execução da estratégia orientada pelo feedback de uma avaliação reprovada.
- **Evento de crítica**: Registro ordenado de uma avaliação no trace final.
- **Métricas acumuladas**: Latência total e chamadas ao modelo de todas as etapas do ciclo de reflexão.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em todos os cenários de aprovação inicial, uma avaliação aprovada resulta em zero tentativas de correção.
- **SC-002**: Em todos os cenários de reprovação seguida de aprovação, exatamente uma tentativa de correção ocorre antes do encerramento.
- **SC-003**: Em todos os cenários de reprovação contínua, o ciclo executa no máximo duas correções por padrão e retorna a resposta da última tentativa.
- **SC-004**: Em 100% dos cenários testados, cada avaliação corresponde a um evento de crítica e as métricas finais igualam a soma das etapas executadas.
- **SC-005**: Os cenários de aceitação podem ser executados sem conectividade externa e produzem resultados reproduzíveis.
- **SC-006**: Os modos sem reflexão continuam selecionáveis e preservam seus resultados e traces existentes nos testes de regressão.

## Assumptions

- O limite configurável conta correções após a resposta inicial; a resposta inicial também é avaliada.
- Uma resposta reprovada após a última correção continua sendo retornada como a última resposta disponível, acompanhada de sua crítica, em vez de ser apresentada como aprovada.
- As estratégias existentes fornecem traces e métricas conforme seu contrato atual; a reflexão agrega esses dados sem descartar eventos anteriores.
- A arena continuará oferecendo os modos sem reflexão; a reflexão é uma opção explícita.
- Os testes usarão resultados controlados para estratégia e avaliador, sem chamadas a modelos ou serviços externos.
