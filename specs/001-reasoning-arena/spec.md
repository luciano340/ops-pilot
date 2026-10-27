# Feature Specification: Núcleo de Raciocínio e Arena de Estratégias

**Feature Branch**: `001-reasoning-arena`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "Criar a arquitetura base do agente de raciocínio e uma arena para comparar estratégias, com ferramentas de alertas e incidentes, persistência de serviços e alertas, traces e métricas, estratégias ReAct e Plan-and-Execute, seed inicial e testes offline."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Comparar estratégias de raciocínio (Priority: P1)

Uma pessoa de plantão envia uma solicitação operacional e executa uma ou mais estratégias com exatamente a mesma entrada. Ela compara as respostas, os passos registrados e as métricas para escolher ou avaliar a abordagem mais útil.

**Why this priority**: A comparação reproduzível entre estratégias é o valor central da arena.

**Independent Test**: Executar duas estratégias com uma entrada comum e confirmar que os resultados são exibidos lado a lado, cada um com resposta, trace, chamadas ao modelo e latência.

**Acceptance Scenarios**:

1. **Given** duas estratégias disponíveis e uma solicitação válida, **When** a pessoa executa a arena com ambas, **Then** cada estratégia recebe a mesma solicitação e a saída identifica separadamente sua resposta, trace e métricas.
2. **Given** uma estratégia selecionada, **When** a execução termina, **Then** a arena apresenta a resposta, a sequência ordenada de eventos permitidos (thought, action, observation, plan, critique e answer) e as métricas de chamadas ao modelo e latência; cada evento action identifica a ferramenta e seus argumentos.
3. **Given** uma estratégia desconhecida ou nenhuma estratégia selecionada, **When** a pessoa tenta executar a arena, **Then** a fronteira de entrada informa o erro sem iniciar uma execução parcial.
4. **Given** credenciais e identificação do modelo configuradas fora do código, **When** uma execução começa sem ajuste de temperatura, **Then** o provedor OpenRouter é usado com temperatura zero.
5. **Given** uma solicitação válida, **When** a pessoa informa as estratégias em `--strategies` e um limite opcional em `--max-iterations`, **Then** a arena executa somente as estratégias selecionadas e respeita o limite configurado.

### User Story 2 - Investigar alertas e gerenciar incidentes (Priority: P1)

Uma pessoa de plantão consulta alertas e solicita a abertura ou resolução de incidentes. O agente usa as ferramentas disponíveis para consultar e atualizar os registros operacionais, mantendo as ações visíveis no trace.

**Why this priority**: A comparação só é representativa quando as estratégias podem interagir com dados operacionais por meio de ações consistentes.

**Independent Test**: Com um conjunto de serviços e alertas conhecido, consultar alertas filtrados, abrir um incidente válido e resolver um incidente existente; verificar os registros e eventos correspondentes.

**Acceptance Scenarios**:

1. **Given** alertas em diferentes estados, **When** a pessoa consulta sem filtro, **Then** recebe os alertas disponíveis; **When** consulta por estado, **Then** recebe somente os alertas correspondentes.
2. **Given** um serviço existente e dados válidos de incidente, **When** a pessoa solicita a abertura, **Then** um incidente é criado para o serviço com título e severidade fornecidos.
3. **Given** um identificador de incidente existente, **When** a pessoa solicita sua resolução, **Then** o incidente passa ao estado resolvido.
4. **Given** um serviço, alerta ou incidente inexistente, ou dados inválidos, **When** uma ferramenta é chamada, **Then** a operação informa a falha e não simula sucesso nem altera registros indevidamente.

### User Story 3 - Executar raciocínio com planejamento limitado (Priority: P2)

Uma pessoa de plantão escolhe uma estratégia que cria um plano, executa uma etapa por vez e revê as etapas restantes até concluir o trabalho ou atingir o limite de execução.

**Why this priority**: O planejamento expõe uma alternativa controlada e comparável ao fluxo ReAct, sem permitir execução ilimitada.

**Independent Test**: Usar respostas determinísticas para o planejador e replanejador, confirmar a execução sequencial das etapas, a revisão do plano após cada etapa e o encerramento com plano vazio ou limite de oito iterações.

**Acceptance Scenarios**:

1. **Given** uma solicitação que pode ser dividida em etapas, **When** a estratégia de planejamento começa, **Then** ela produz uma lista estruturada e validada de etapas.
2. **Given** um plano com etapas restantes, **When** uma etapa é executada, **Then** a estratégia registra o resultado, revê as etapas restantes e executa no máximo uma etapa antes da revisão.
3. **Given** um plano concluído ou oito iterações realizadas, **When** a estratégia avalia a continuação, **Then** encerra a execução e devolve uma resposta final sem ultrapassar o limite.

### User Story 4 - Preparar dados e validar sem dependências externas (Priority: P2)

Uma pessoa desenvolvedora prepara um conjunto inicial previsível de serviços e alertas e executa testes locais sem acessar a rede nem um modelo externo.

**Why this priority**: Dados reproduzíveis e testes offline permitem validar ferramentas e traces sem custo ou dependência de disponibilidade externa.

**Independent Test**: Preparar o banco de dados por meio da operação de seed e executar os testes de ferramentas, persistência e formatação com dependências externas substituídas por respostas determinísticas.

**Acceptance Scenarios**:

1. **Given** um banco preparado para demonstração, **When** a pessoa executa `python manage.py seed_db`, **Then** encontra cinco serviços e seis alertas, sendo três em estado firing e três em estado resolved.
2. **Given** que o seed é executado novamente, **When** a pessoa consulta os dados, **Then** o conjunto inicial continua com as mesmas quantidades, sem duplicação.
3. **Given** o conjunto de testes do agente, **When** ele é executado sem credenciais de modelo e sem rede, **Then** os testes de store, ferramentas e formatadores de trace terminam com resultados determinísticos.

### Edge Cases

- Uma consulta de alertas não encontra registros para o estado solicitado.
- O filtro de estado ou os argumentos da abertura/resolução estão ausentes, inválidos ou fora dos valores aceitos.
- A abertura referencia um serviço inexistente ou a resolução referencia um incidente inexistente ou já resolvido.
- O modelo retorna conteúdo que não corresponde ao formato estruturado esperado pelo planejador ou replanejador.
- Uma ferramenta falha durante uma execução; a falha deve ser registrada como falha, sem evento de sucesso fabricado.
- Uma estratégia atinge o limite de iterações ainda com etapas pendentes.
- Uma solicitação termina sem resposta textual utilizável ou sem eventos de trace.
- A execução do seed é repetida em um banco que já contém parte ou todo o conjunto inicial.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A arena MUST aceitar uma solicitação e uma ou mais estratégias nomeadas, entregar a mesma solicitação a todas as estratégias selecionadas e rejeitar nomes desconhecidos antes de iniciar as execuções.
- **FR-002**: Cada execução MUST produzir uma resposta textual, uma sequência ordenada de eventos de trace e métricas com o total de chamadas ao modelo e a latência em milissegundos.
- **FR-003**: O trace MUST aceitar apenas os tipos thought, action, observation, plan, critique e answer. Cada evento action MUST identificar a ferramenta e seus argumentos.
- **FR-004**: A arena MUST exibir resultados distinguíveis por estratégia, lado a lado ou em colunas equivalentes, incluindo trace e métricas de cada execução.
- **FR-005**: A arena, iniciada com `python manage.py arena`, MUST aceitar `--strategies` para selecionar estratégias e `--max-iterations` para configurar o limite de iterações.
- **FR-006**: A estratégia ReAct MUST usar as ferramentas operacionais disponíveis e preservar o trace completo, incluindo ações e observações, além da contagem de chamadas ao modelo.
- **FR-007**: A estratégia Plan-and-Execute MUST produzir um plano estruturado, executar uma etapa por vez e revisar o plano restante após cada execução.
- **FR-008**: A estratégia Plan-and-Execute MUST terminar quando não houver etapas restantes ou quando alcançar o limite rígido de oito passos/iterações, sem excedê-lo.
- **FR-009**: As ferramentas MUST permitir consultar alertas opcionalmente filtrados por estado, abrir um incidente com título, serviço e severidade, e resolver um incidente pelo identificador.
- **FR-010**: Os registros de serviços, alertas e incidentes MUST ser persistidos; ferramentas MUST validar os argumentos e comunicar registros inexistentes ou falhas de persistência sem indicar sucesso.
- **FR-011**: O comando `python manage.py seed_db` MUST criar um conjunto reproduzível com cinco serviços e seis alertas, três com estado firing e três com estado resolved, sem duplicar esse conjunto quando executado novamente.
- **FR-012**: A integração com o modelo MUST obter credenciais e identificação do modelo de configuração externa, usar OpenRouter como provedor e aplicar temperatura zero por padrão.
- **FR-013**: Os testes de store, ferramentas e formatação de trace MUST poder ser executados sem chamadas de rede ou de modelo e MUST usar resultados determinísticos.
- **FR-014**: Entradas da linha de comando MUST ser validadas na fronteira e erros MUST ser apresentados de forma explícita, sem iniciar execuções com argumentos inválidos.

### Key Entities

- **Estratégia de raciocínio**: Uma abordagem nomeada para responder a uma solicitação operacional, produzindo resposta, eventos e métricas.
- **Evento de trace**: Um registro ordenado de um pensamento, ação, observação, plano, crítica ou resposta; ações identificam a ferramenta e seus argumentos.
- **Métrica de execução**: A contagem de chamadas ao modelo e a latência observada durante uma execução.
- **Serviço**: Um componente operacional ao qual alertas e incidentes podem estar associados.
- **Alerta**: Um sinal operacional associado a um serviço e a um estado, incluindo firing e resolved.
- **Incidente**: Um registro operacional com identificador, título, serviço, severidade e estado, que pode ser aberto e resolvido.
- **Plano**: Uma lista ordenada de etapas para atender a uma solicitação, com etapas pendentes revisadas após cada execução.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% das execuções válidas, a pessoa consegue identificar a resposta, a sequência de eventos e as métricas da estratégia executada.
- **SC-002**: Em 100% das comparações com duas ou mais estratégias válidas, todas recebem a mesma entrada e seus resultados são apresentados separadamente.
- **SC-003**: Nenhuma execução de planejamento realiza mais de oito passos/iterações; todas as execuções encerram ao esgotar as etapas ou atingir o limite.
- **SC-004**: O conjunto inicial contém exatamente cinco serviços e seis alertas, com a distribuição de três firing e três resolved, inclusive após execuções repetidas do seed.
- **SC-005**: 100% dos testes de store, ferramentas e formatação podem ser executados sem rede ou credenciais de modelo e produzem resultados reproduzíveis.
- **SC-006**: Solicitações com argumentos inválidos ou registros inexistentes são comunicadas como falhas e não geram alterações ou resultados apresentados como sucesso.

## Assumptions

- A arena é destinada a pessoas desenvolvedoras e de plantão em um ambiente de desenvolvimento ou demonstração; autenticação de operadores não faz parte deste escopo.
- O conjunto criado pelo seed é dado de demonstração e o seed deve ser repetível, preservando essas quantidades sem apagar dados não relacionados.
- Os testes offline substituem o modelo e as dependências externas por implementações determinísticas; não certificam qualidade semântica de respostas reais do modelo.
- O provedor de modelo requerido é OpenRouter; credenciais e identificador do modelo serão fornecidos fora do código-fonte, e o padrão de temperatura é zero.
- A persistência deve suportar PostgreSQL no ambiente de execução, sem impedir o uso do banco local já configurado para desenvolvimento e testes.
- A estratégia ReAct e a estratégia Plan-and-Execute são as estratégias incluídas nesta primeira versão; não há requisito para comparação visual em navegador.
