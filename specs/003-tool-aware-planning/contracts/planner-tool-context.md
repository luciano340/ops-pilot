# Contrato: Contexto de ferramentas do planner

## Entrada de planejamento

Além da solicitação do usuário, o planner recebe um catálogo das ferramentas disponíveis na execução atual. Cada item contém:

- nome usado pelo executor;
- descrição de capacidade;
- schema de argumentos e campos obrigatórios.

O catálogo reflete somente ferramentas vinculadas ao executor daquela estratégia e não inclui credenciais.

## Comportamento esperado

- Se uma solicitação pedir explicitamente uma ação que uma ferramenta disponível executa, criar uma etapa direcionada àquela capacidade.
- Se a ferramenta exigir dados ausentes, não inventá-los: buscar os fatos por ferramenta de leitura quando viável ou pedir esclarecimento.
- Se não houver ferramenta para uma operação solicitada, não alegar acesso ou execução dessa operação.
- Pedidos informativos sem necessidade de ação podem retornar plano sem etapas.
- O executor pode realizar até uma chamada operacional de ferramenta por etapa; ações confirmadas e observações continuam registradas no trace.

## Compatibilidade

O formato de `Plan`, `PlanReview`, eventos de trace, métricas e interface CLI permanece inalterado. Não se adicionam ferramentas ou permissões.
