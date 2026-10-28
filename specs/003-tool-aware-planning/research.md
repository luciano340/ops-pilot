# Research: Planejamento ciente das ferramentas disponíveis

## Contexto de ferramentas disponível ao planejador

- **Decision**: Fornecer ao prompt de planejamento um catálogo derivado das ferramentas entregues à estratégia, com nome, descrição e schema de argumentos em formato serializável.
- **Rationale**: O executor já está vinculado a essas ferramentas, mas o planner atual recebe apenas a solicitação e por isso pode classificar uma operação suportada como impossível ou concluir com lista vazia. O catálogo dá ao planner o contexto de capacidade que falta sem ampliar permissões.
- **Alternatives considered**:
  - Heurísticas de palavras-chave no código para selecionar ferramenta: rejeitadas por serem frágeis, específicas a idiomas e difíceis de manter.
  - Fazer planner diretamente executar ferramentas: rejeitado porque mistura etapas de planejamento e execução.
  - Passar apenas nomes de ferramentas: insuficiente para inferir campos obrigatórios e limitações.

## Tratamento de pedidos suportados e não suportados

- **Decision**: Instruir o planejador a criar etapas para ações que as ferramentas possam executar; quando uma ação pedida não existir, não afirmar que pode executá-la nem que foi executada. Para dados obrigatórios ausentes, não inventar valores; coletar fatos possíveis com ferramentas de leitura ou pedir esclarecimento.
- **Rationale**: O resultado observado para abertura de incidente é um plano vazio. Ao mesmo tempo, a ferramenta `open_incident` requer título, serviço e severidade; a solicitação pode não fornecer todos esses dados. O sistema deve preferir consulta segura ou esclarecimento a uma mutação com dados fabricados.
- **Alternatives considered**:
  - Forçar qualquer pedido operacional a gerar etapa independentemente dos dados: rejeitado, pois pode induzir argumentos inventados.
  - Tratar uma resposta do modelo sem ferramenta como sucesso: rejeitado; ação só é confirmada por observação da ferramenta.

## Fonte e formato dos schemas

- **Decision**: Usar metadados já presentes nos objetos de ferramenta LangChain; serializar catálogo com JSON UTF-8/Unicode para manter descrições e schemas legíveis.
- **Rationale**: LangChain documenta schemas Pydantic de argumentos e descrições como contrato de ferramentas; as ferramentas do projeto usam `StructuredTool` e schemas Pydantic.
- **Alternatives considered**:
  - Manter lista manual separada no planner: rejeitado porque pode ficar divergente do executor.

## Referência

- LangChain Tools, definição de schemas de argumentos com Pydantic e descrições: [docs.langchain.com/oss/python/langchain/tools](https://docs.langchain.com/oss/python/langchain/tools).
