# AGENTS.md

Instrucoes permanentes para agentes Codex neste repositorio.

## Escopo do projeto

Produzzy é um SaaS de gestão de estoque, etiquetas e reposição, com arquitetura multi-workspace, em desenvolvimento para uso em produção. Cada workspace representa uma empresa, equipe ou contexto de estoque, e todos os dados de negócio devem permanecer isolados por workspace_id.

## Stack atual

Backend:
- Python.
- FastAPI para API HTTP.
- SQLAlchemy para ORM e sessoes de banco.
- Alembic para migrations.
- Pydantic para schemas de entrada e resposta.
- PostgreSQL como banco principal e fluxo oficial de desenvolvimento/producao.
- `python-jose` para JWT, `passlib`/bcrypt para senhas, `python-dotenv` para variaveis locais.
- `qrcode`, Pillow e `python-barcode` para QR Codes, codigos de barras e etiquetas.

Frontend:
- React com Vite.
- JavaScript/JSX, sem TypeScript atualmente.
- CSS puro em `frontend/src/styles/global.css`.
- ESLint configurado em `frontend/eslint.config.js`.
- Sem biblioteca de componentes externa; preservar os componentes locais em `frontend/src/components`.

## Estrutura do repositorio

Backend:
- `backend/app/main.py`: cria a aplicacao FastAPI, CORS e registra routers.
- `backend/app/config.py`: carrega variaveis de ambiente. Nao expor nem alterar secrets.
- `backend/app/database.py`: engine, `SessionLocal`, `Base` e compatibilidade legada SQLite. PostgreSQL segue sendo o banco principal.
- `backend/app/models.py`: modelos SQLAlchemy.
- `backend/app/schemas.py`: schemas e enums Pydantic.
- `backend/app/crud.py`: regras de negocio, permissoes, isolamento por workspace, movimentos, soft delete e audit logs.
- `backend/app/dependencies.py`: dependencias de banco e autenticacao.
- `backend/app/routers/`: endpoints por dominio, normalmente sob `/workspaces/{workspace_id}/...`.
- `backend/app/services/`: seguranca e geracao de QR Code/etiquetas.
- `backend/alembic/versions/`: migrations Alembic.
- `backend/tests/`: testes pytest de integracao usando banco PostgreSQL de teste via `DATABASE_URL_TEST`.

Frontend:
- `frontend/src/App.jsx`: composicao de providers, autenticacao, selecao de workspace e navegacao principal.
- `frontend/src/contexts/`: contexto de autenticacao e workspace ativo.
- `frontend/src/services/`: chamadas HTTP por dominio.
- `frontend/src/lib/api.js`: cliente HTTP, token e tratamento de erros.
- `frontend/src/pages/`: telas principais.
- `frontend/src/components/layout/`: layout, sidebar, header, menus, membros e modais de workspace.
- `frontend/src/components/ui/`: componentes visuais reutilizaveis.
- `frontend/src/components/replenishment/`: componentes do fluxo de reposicao.
- `frontend/src/styles/global.css`: estilos globais e padroes visuais.

## Regras de dominio obrigatorias

- Toda leitura ou escrita de dados de negocio deve validar membro do workspace e filtrar por `workspace_id`.
- Nunca permitir vazamento, consulta cruzada ou mutacao cruzada entre workspaces.
- Roles permanentes: `owner`, `admin`, `employee` e `viewer`.
- Preservar a matriz de permissoes em `backend/app/crud.py`:
  - leitura: `owner`, `admin`, `employee`, `viewer`;
  - produtos/categorias: `owner`, `admin`;
  - estoque: `owner`, `admin`, `employee`;
  - reposicoes: criacao/atualizacao/atribuicao por `owner`, `admin`, `employee`, com gerenciamento de responsaveis por `owner` e `admin`;
  - audit logs: `owner`, `admin`.
- Proteger owners: nao remover ou rebaixar o ultimo owner do workspace.

Estoque:
- Estoque nunca pode ficar negativo.
- Toda alteracao de estoque deve gerar um registro em `stock_movements`.
- Movimento deve preservar `quantity_before`, `quantity_after`, usuario, produto, workspace e audit log.
- Estoque so muda atraves de movimentacao real em endpoint/fluxo de stock movement.
- Criar uma reposicao nao altera estoque automaticamente.
- Marcar uma reposicao como `completed` nao altera estoque automaticamente.
- Uma reposicao so deve virar `stocked` quando houver entrada real de estoque vinculada.
- Saidas maiores que o estoque atual devem ser recusadas.
- Nao movimentar estoque de produto inativo.

Reposicao:
- Fluxo principal: `open` -> `in_progress` -> `completed` -> `stocked`.
- `canceled` e um estado terminal/alternativo permitido.
- Estados validos: `open`, `in_progress`, `completed`, `stocked`, `canceled`.
- Reposicoes ativas por produto no mesmo workspace devem continuar bloqueando duplicidade enquanto estiverem em `open`, `in_progress` ou `completed`.
- Responsaveis por reposicao devem ser membros do mesmo workspace.
- Nao alterar responsaveis de reposicoes `completed`, `stocked` ou `canceled`.

Produtos e categorias:
- Produtos usam soft delete (`is_active`, `deleted_at`, `deleted_by_user_id`) e devem manter historico de movimentos.
- Categorias usam soft delete e podem soft-deletar produtos vinculados, preservando `deleted_by_category_id`.
- Restauracoes devem respeitar unicidade de nomes ativos por workspace.
- Produtos/categorias deletados nao devem aparecer em listagens ativas, dashboard, baixo estoque, etiquetas ou QR Code, salvo quando o fluxo explicitamente pedir `include_deleted`/status apropriado.

Audit logs:
- Preservar audit logs existentes e criar logs para mutacoes relevantes.
- Nao remover, mascarar retroativamente ou reescrever historico de auditoria sem solicitacao explicita.
- Metadados de auditoria devem ser pequenos e nao devem incluir senhas, hashes, JWTs, tokens de convite, secrets ou dados sensiveis desnecessarios.

## Seguranca e configuracao

- Nunca expor secrets, tokens, senhas, hashes ou conteudo real de `.env`.
- Nao alterar `.env` sem solicitacao explicita.
- `.env.example` pode ser atualizado apenas quando uma variavel publica/documentada for realmente adicionada ou alterada.
- PostgreSQL e o banco principal. SQLite aparece apenas como compatibilidade legada/desenvolvimento e nao deve guiar novas decisoes.
- Nao apontar testes para banco de desenvolvimento ou producao. `DATABASE_URL_TEST` deve ser separado de `DATABASE_URL`.

## Regras de mudanca

- Nao fazer commit automaticamente.
- Nao fazer push automaticamente.
- Nao adicionar dependencias sem necessidade real.
- Nao realizar grandes refatoracoes sem solicitacao.
- Nao criar migrations sem necessidade real de schema.
- Quando schema mudar de verdade, usar Alembic e revisar cuidadosamente a migration.
- Preservar padroes de arquitetura existentes antes de introduzir novas abstracoes.
- Manter mudancas pequenas, focadas e coerentes com os modulos atuais.
- Nao alterar arquivos fora do escopo solicitado.
- Preservar padroes visuais existentes no frontend: componentes locais, CSS puro, layout atual e linguagem visual ja definida.

## Validacoes obrigatorias

- Se alterar frontend, executar em `frontend/`:
  - `npm run lint`
  - `npm run build`
- Se alterar backend, executar em `backend/`:
  - `pytest` ou `venv/bin/python -m pytest`, conforme ambiente disponivel;
  - validacoes relevantes para a area alterada.
- Sempre executar `git diff --check` antes de finalizar.
- Revisar o diff antes de responder.
- Se uma validacao nao puder ser executada, informar o motivo claramente.

## Resposta final esperada

Ao terminar qualquer tarefa, informar:
- o que foi feito;
- arquivos modificados;
- testes e validacoes executados;
- erros ou warnings encontrados;
- riscos restantes;
- verificacoes manuais recomendadas.
