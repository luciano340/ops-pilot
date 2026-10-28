# Feature Specification: Benchmark de Desempenho

**Feature Branch**: `005-benchmark-performance`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Criar um comando de benchmark do OpsPilot para comparar as estratégias ReAct e Plan-and-Execute em três cenários operacionais, medindo acerto, chamadas ao modelo e latência, com seed antes de cada execução, validação da resposta e dos efeitos persistidos, filtros de cenário e estratégia e opção para desativar o replanejador. Adicionar severidade aos alertas, incluindo o seed e as camadas que expõem essa informação; classificar os três alertas atualmente firing como critical."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Medir leitura e operações sequenciais (Priority: P1)

Uma pessoa executa o benchmark para verificar se cada estratégia responde corretamente a uma pergunta sobre alertas e realiza uma sequência solicitada de abertura e resolução de incidentes. O resultado deve considerar tanto a resposta textual quanto as mudanças persistidas e não deve confundir registros preexistentes com efeitos da execução avaliada.

**Why this priority**: Leitura de estado e operações explícitas são as capacidades operacionais mais comuns; verificar os efeitos reais detecta respostas que alegam sucesso sem executar as ações.

**Independent Test**: Executar C1 e C2 para uma estratégia cada, usando um estado de base conhecido; conferir a severidade reportada, a resposta, mudanças em alertas e o delta de incidentes antes/depois da execução.

**Acceptance Scenarios**:

1. **Given** o seed classifica como `critical` os alertas firing de API 5xx, latência de autorização do checkout e backlog do worker, **When** C1 pergunta quantos alertas críticos estão disparando, **Then** o resultado passa apenas se a resposta informar a contagem exata de três e não houver alterações operacionais causadas pela execução.
2. **Given** cada execução parte do estado de base preparado pelo seed, **When** C2 solicita incidentes SEV2 para checkout, worker e api e a resolução do primeiro, **Then** exatamente três novos incidentes correspondem aos serviços e severidades solicitados, checkout está resolvido e os demais permanecem abertos.
3. **Given** já existem incidentes antes de uma execução, **When** C1 ou C2 é validado, **Then** a avaliação usa os registros criados ou alterados pela execução e não exige apagar nem confundir os dados preexistentes.
4. **Given** uma estratégia retorna uma resposta incorreta ou efeitos persistidos incorretos, **When** C1 ou C2 termina, **Then** o caso é marcado como falha mesmo que a outra validação tenha passado.

### User Story 2 - Avaliar lógica dinâmica com alertas (Priority: P2)

Uma pessoa mede se as estratégias conseguem identificar o alerta firing mais antigo, abrir um incidente para o serviço correspondente e informar quantos alertas firing continuam sem cobertura por incidentes criados naquela execução.

**Why this priority**: O cenário verifica uso combinado de observação, ordenação temporal e escrita operacional, além de uma resposta que depende do estado inicial.

**Independent Test**: Preparar o seed, identificar antes da execução o alerta firing mais antigo, executar C3 com uma estratégia e validar o serviço do novo incidente e a contagem de alertas firing sem incidente novo para seus serviços.

**Acceptance Scenarios**:

1. **Given** há alertas firing com datas de criação conhecidas, **When** C3 solicita abrir incidente para o mais antigo, **Then** o novo incidente pertence ao serviço desse alerta.
2. **Given** C3 cria o incidente no serviço do alerta mais antigo, **When** a resposta informa os alertas restantes, **Then** a contagem corresponde aos alertas firing cujos serviços não receberam incidente criado naquela execução.
3. **Given** existem incidentes anteriores ao início do cenário, **When** o sistema verifica cobertura, **Then** somente incidentes novos da execução atual contam como cobertura para esse cenário.
4. **Given** a resposta textual diverge do estado persistido ou da contagem calculada, **When** C3 termina, **Then** o caso é marcado como falha.

### User Story 3 - Selecionar, comparar e inspecionar execuções (Priority: P2)

Uma pessoa pode executar todos os cenários ou filtrar um deles, comparar ReAct e Plan-and-Execute, opcionalmente desativar o replanejador e consultar uma tabela consolidada de acerto, chamadas ao modelo e latência.

**Why this priority**: A seleção torna o benchmark útil tanto para comparação completa quanto para investigação focada de uma estratégia ou comportamento.

**Independent Test**: Executar com seletores válidos e doubles controlados; verificar a matriz de execuções esperada, o uso da configuração do replanejador e a tabela com uma linha por execução.

**Acceptance Scenarios**:

1. **Given** nenhuma opção de cenário é informada, **When** o benchmark é executado, **Then** ele executa C1, C2 e C3 para cada uma das duas estratégias.
2. **Given** `--scenario` ou `-s` seleciona C1, C2, C3 ou `all`, **When** o benchmark é executado, **Then** somente os cenários selecionados são executados.
3. **Given** `--strategies` especifica uma ou ambas as estratégias válidas, **When** o benchmark é executado, **Then** apenas essas estratégias participam da matriz.
4. **Given** `--no-replanner` está presente, **When** Plan-and-Execute é executada, **Then** sua fase de replanejamento não ocorre; ReAct permanece inalterado.
5. **Given** as execuções selecionadas terminaram, **When** o resultado é exibido, **Then** a tabela contém cenário, estratégia, acerto, chamadas ao modelo e latência para cada combinação executada.
6. **Given** todas as validações passam, **When** o comando termina, **Then** seu código de saída é zero; se qualquer validação textual ou de estado falhar, o código de saída é um.

### Edge Cases

- O seed existente atualiza ou cria serviços e alertas, mas não apaga incidentes. A preparação do benchmark não deve remover dados preexistentes; cada execução deve distinguir o estado-base dos efeitos próprios.
- A severidade de cada alerta deve estar definida para todos os registros do seed; a atualização repetida do seed deve manter esses valores determinísticos.
- Se não houver alerta firing, C1 deve comparar contra a contagem zero; C3 deve falhar como cenário não executável e informar a causa, sem inventar alerta.
- Se dois alertas tiverem o mesmo `created_at`, o benchmark deve usar um desempate estável e aplicar a mesma regra ao alvo esperado e à validação.
- Se a ferramenta abrir incidente, mas a resposta omitir ou informar contagem incorreta, a validação textual reprova o caso.
- Se o modelo, seed ou banco falhar antes da avaliação, o benchmark deve terminar com falha explícita, não produzir linha de sucesso.
- Se nenhum nome de estratégia for informado, ambas as estratégias suportadas são selecionadas; nomes desconhecidos ou lista vazia são entradas inválidas.
- A opção `--no-replanner` não deve alterar a estratégia ReAct.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST disponibilizar o comando `python manage.py bench` para executar o benchmark operacional.
- **FR-002**: Cada alerta MUST possuir uma severidade explícita entre `critical`, `warning` e `info`, e essa classificação MUST estar disponível nas entradas e saídas das interfaces operacionais que expõem alertas.
- **FR-003**: O seed MUST atribuir severidade de forma determinística a todos os alertas de exemplo e atualizar a severidade quando atualizar um alerta existente; os alertas firing de API 5xx, checkout payment authorization latency e worker queue backlog MUST ser `critical`.
- **FR-004**: O sistema MUST definir C1 com a solicitação “Quantos alertas críticos estão disparando?” e avaliar a contagem reportada contra a contagem de alertas `critical` com status firing no estado preparado; para o seed atual, a contagem esperada MUST ser três.
- **FR-005**: O sistema MUST definir C2 com a solicitação de abrir incidentes SEV2 para checkout, worker e api, nessa ordem, e resolver o primeiro; a validação MUST confirmar exatamente três incidentes novos da execução, serviços e severidades correspondentes e checkout resolvido.
- **FR-006**: O sistema MUST definir C3 para selecionar o alerta firing mais antigo, abrir um incidente para o serviço correspondente e reportar quantos alertas firing não receberam incidente novo para seus serviços naquela execução.
- **FR-007**: Antes de cada combinação cenário-estratégia, o sistema MUST executar o seed para preparar os serviços e alertas, capturar o estado-base relevante e avaliar os efeitos como diferença em relação a esse estado.
- **FR-008**: O benchmark MUST NOT apagar incidentes ou outros dados operacionais preexistentes para isolar uma execução.
- **FR-009**: Cada caso MUST passar somente quando a resposta textual satisfizer o critério esperado e as verificações de estado persistido satisfizerem os critérios do cenário.
- **FR-010**: O sistema MUST executar os três cenários para `react` e `plan_and_execute` por padrão, produzindo até seis execuções independentes.
- **FR-011**: O sistema MUST aceitar `--scenario` e `-s` com `c1`, `c2`, `c3` ou `all`, usando `all` como padrão.
- **FR-012**: O sistema MUST aceitar `--strategies` para selecionar `react`, `plan_and_execute` ou ambos; nomes desconhecidos e seleções vazias MUST ser rejeitados antes de iniciar as execuções.
- **FR-013**: A opção `--no-replanner` MUST desativar a fase de replanejamento somente para Plan-and-Execute e MUST deixar ReAct inalterado.
- **FR-014**: Para cada combinação executada, o sistema MUST apresentar cenário, estratégia, acerto, total de chamadas ao modelo e latência em milissegundos.
- **FR-015**: O comando MUST retornar código zero somente quando todas as validações das combinações selecionadas passarem e código um quando qualquer validação de resposta ou estado falhar.
- **FR-016**: Falhas de configuração, execução do seed ou acesso ao banco MUST ser reportadas explicitamente e MUST NOT gerar resultado com aparência de sucesso.

### Key Entities *(include if feature involves data)*

- **Cenário de benchmark**: Solicitação operacional predefinida, expectativa de resposta e verificações de estado para C1, C2 ou C3.
- **Severidade do alerta**: Classificação explícita `critical`, `warning` ou `info` usada por pessoas e estratégias para distinguir a importância de um alerta.
- **Execução de benchmark**: Uma combinação de cenário e estratégia, com estado-base, resultado textual, efeitos persistidos e métricas.
- **Estado-base**: Snapshot dos registros relevantes antes de uma execução, usado para distinguir efeitos novos de dados existentes.
- **Avaliação do cenário**: Resultado pass/fail produzido pela validação conjunta da resposta textual e dos efeitos observáveis no estado persistido.
- **Métricas da execução**: Chamadas ao modelo e latência total medidas para uma estratégia em um cenário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma execução sem filtros produz exatamente seis resultados, cobrindo cada um dos três cenários com cada uma das duas estratégias.
- **SC-002**: 100% dos alertas fornecidos pelo seed apresentam uma das três severidades definidas e mantêm a mesma severidade após execuções repetidas do seed.
- **SC-003**: Em 100% das execuções de C1 aprovadas, a contagem informada coincide com a contagem de alertas critical firing no estado-base — três para o seed atual — e não há alteração operacional atribuível à execução.
- **SC-004**: Em 100% das execuções de C2 aprovadas, há exatamente três incidentes novos correspondentes aos serviços solicitados, todos SEV2, com checkout resolvido.
- **SC-005**: Em 100% das execuções de C3 aprovadas, o incidente novo corresponde ao serviço do alerta firing mais antigo e a contagem textual coincide com alertas firing sem incidente novo por serviço.
- **SC-006**: Toda execução selecionada gera uma linha com os cinco campos de resultado definidos, incluindo acerto, chamadas ao modelo e latência.
- **SC-007**: Todas as combinações aprovadas retornam código zero; ao menos uma validação textual ou de estado reprovada resulta em código um.
- **SC-008**: Execuções repetidas não apagam nem contabilizam incidentes preexistentes como efeitos da execução atual.

## Assumptions

- O benchmark roda contra o banco de desenvolvimento/benchmark configurado para a aplicação; ele não apaga nem recria o banco.
- Os alertas firing atuais (API 5xx, latência de autorização do checkout e backlog do worker) são classificados como `critical`; os alertas resolvidos atuais são classificados como `info`. `warning` permanece disponível para novos alertas e fixtures.
- A rotina de seed existente é executada antes de cada combinação cenário-estratégia; como ela atualiza ou cria serviços e alertas, o estado-base é capturado depois do seed.
- Incidentes novos são identificados por comparação com os identificadores existentes no estado-base; incidentes anteriores não contam como efeitos da combinação atual.
- Para C3, um alerta firing é considerado coberto nesta execução quando um incidente novo foi criado para o mesmo serviço. A quantidade “sobrando” é a contagem dos outros alertas firing.
- Se vários alertas firing empatarem na data de criação, a escolha é determinística pelo identificador do alerta em ordem crescente.
- O benchmark mede uma execução por combinação selecionada; não faz agregação estatística de múltiplas repetições nesta versão.
- Falhas de execução ou infraestrutura são distintas de um resultado de benchmark aprovado; nenhuma falha é convertida em sucesso.
