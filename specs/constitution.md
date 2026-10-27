<!--
Relatório de Impacto da Sincronização
Alteração de versão: scaffold (sem versão) → 1.0.0 (constituição inicial do projeto)
Princípios modificados (notas do projeto → constituição):
- Camadas explícitas e proibição de I/O no domínio → I. Arquitetura em Camadas e Pureza do Domínio
- Validação nas fronteiras e DTOs → II. Fronteiras Validadas e Contratos Explícitos
- Anotações de tipo, erros de domínio, testes e verificações estáticas → III. Segurança de Tipos e Critérios de Qualidade
- Repositórios assíncronos e requisitos de desempenho → IV. Acesso Assíncrono a Dados e Eficiência de Recursos
- Segredos e proteções para ações destrutivas → V. Segurança por Padrão
Seções adicionadas: Tecnologia e Ambiente de Execução; Desenvolvimento Orientado por Especificações
Seções removidas: Nenhuma; o arquivo canônico anterior era apenas um scaffold não preenchido.
TODO de acompanhamento: confirmar a data original de ratificação e substituir o marcador TODO.
-->

# Constituição do OpsPilot

## Princípios Fundamentais

### I. Arquitetura em Camadas e Pureza do Domínio
As dependências DEVEM fluir das fronteiras HTTP/CLI para Services e, em seguida,
para Store; nenhuma camada pode ignorar a próxima ou depender de uma camada
externa. O domínio NÃO DEVE realizar I/O. Services DEVEM conter as regras de
negócio e permanecer puras sempre que possível; Store DEVE ser responsável pela
persistência. Essa separação mantém o comportamento do domínio testável de forma
independente e permite substituir a persistência.

### II. Fronteiras Validadas e Contratos Explícitos
Toda entrada HTTP e CLI DEVE ser validada na respectiva fronteira com um schema
Pydantic antes de entrar na lógica da aplicação. Os dados que atravessam as
fronteiras entre camadas DEVEM usar DTOs. Falhas de negócio previsíveis DEVEM
ser representadas por tipos de erro do domínio e traduzidas em respostas HTTP
ou códigos de saída da CLI somente na fronteira. Isso impede que entradas não
validadas e preocupações de transporte vazem para o domínio.

### III. Segurança de Tipos e Critérios de Qualidade
Todas as assinaturas de funções e métodos DEVEM ter anotações de tipo, e o
projeto DEVE passar pelo Mypy em modo estrito. Novos comportamentos de domínio
DEVEM incluir testes de domínio. As alterações DEVEM preservar a aprovação dos
testes e das verificações de tipos para serem consideradas concluídas. Essas
verificações tornam os contratos explícitos e detectam regressões cedo.

### IV. Acesso Assíncrono a Dados e Eficiência de Recursos
Operações de repositório DEVEM ser aguardadas em fluxos assíncronos. Código
assíncrono DEVE usar as APIs assíncronas do ORM do Django e NÃO DEVE chamar
operações síncronas do ORM diretamente. O trabalho transacional que exigir
comportamento síncrono do ORM DEVE ser isolado por meio da ponte suportada de
sincronização para assincronismo. Chamadas a serviços externos permanecem
síncronas, a menos que a integração forneça explicitamente uma interface
assíncrona.

Consultas independentes DEVEM, preferencialmente, executar em paralelo com
`asyncio.gather()`, e operações de fan-out DEVEM ser limitadas com
`asyncio.Semaphore`. Querysets DEVEM evitar acessos N+1 com `select_related` ou
`prefetch_related`; consultas somente de leitura DEVEM, preferencialmente, usar
`values()` ou `values_list()` e carregar apenas as colunas necessárias com
`.only()` ou `.defer()`. Ingestões e atualizações em lote DEVEM usar operações
em massa quando a semântica permitir. Operações de listagem DEVEM ser paginadas
e retornar no máximo 100 registros por página, incluindo a contagem total no
resultado.

Em fluxos intensivos em dados, verificações de pertinência DEVEM, de
preferência, usar conjuntos ou dicionários; cargas de streaming DEVEM, de
preferência, usar generators; e dataclasses do domínio DEVEM, de preferência,
usar `slots=True`. Clientes de rede DEVEM reutilizar conexões em pool;
resultados determinísticos DEVEM ser armazenados em cache quando isso for
seguro. Serialização de alto desempenho, como `orjson`, DEVE ser usada somente
quando medições de carga justificarem a escolha. Essas otimizações DEVEM
preservar a correção e os limites de recursos.

### V. Segurança por Padrão
Segredos, senhas e arquivos `.env` NÃO DEVEM ser versionados. Valores secretos
DEVEM ser fornecidos pelo ambiente ou por um gerenciador de segredos aprovado.
Operações destrutivas DEVEM usar proteções explícitas e validação local, em vez
de confiar na intenção gerada por um modelo. Isso reduz a exposição acidental
de dados e limita o impacto de automações inseguras.

## Tecnologia e Ambiente de Execução

A base de versões suportadas é Python 3.14 e Django 6.1. A aplicação usa
Pydantic para validação nas fronteiras, `langchain-core` e `langchain-openai`
para integrações com agentes, PostgreSQL por meio de `psycopg` no ambiente do
Compose e SQLite como padrão no desenvolvimento local. Pytest e Mypy são as
ferramentas obrigatórias de teste e verificação estática de tipos. Alterações
de dependências ou do ambiente de execução DEVEM atualizar a configuração do
projeto e a documentação relevante, além de serem validadas nas versões
suportadas.

## Desenvolvimento Orientado por Especificações

O desenvolvimento de funcionalidades DEVE seguir este fluxo ordenado do Spec
Kit:

1. `/speckit.specify` — criar ou atualizar a especificação da funcionalidade.
2. `/speckit.plan` — documentar o design e as decisões técnicas.
3. `/speckit.tasks` — criar tarefas de implementação ordenadas por dependência.
4. `/speckit.implement` — implementar as tarefas aprovadas e executar os
   critérios de qualidade.

As especificações e os artefatos relacionados em `specs/` DEVEM ser
versionados junto com o código. DEVE haver validação humana entre as fases do
fluxo, e a implementação NÃO DEVE começar antes da aprovação da especificação.
Isso torna os requisitos, as decisões de design e as entregas rastreáveis.

## Governança

Esta constituição tem precedência sobre práticas conflitantes do projeto.
Alterações DEVEM atualizar este documento, incrementar sua versão semântica e
registrar o motivo em um Relatório de Impacto da Sincronização para revisão.
Incrementos MAJOR são obrigatórios para mudanças incompatíveis de governança,
incrementos MINOR para novos princípios ou expansões materiais e incrementos
PATCH para esclarecimentos e correções não semânticas.

Todo plano de implementação, conjunto de tarefas, revisão de código e alteração
DEVE ser verificado quanto à conformidade com estes princípios. Qualquer
exceção DEVE ser documentada com sua justificativa e aprovada por uma pessoa
antes da implementação. Novas alterações DEVEM incluir testes relevantes e
passar por `pytest` e `mypy .`. Os commits DEVEM usar Conventional Commits, com
uma descrição no infinitivo e sem ponto final.

**Versão**: 1.0.0 | **Ratificada**: TODO(27/10/2026): confirmar a data original de adoção | **Última alteração**: 2026-10-27
