# Deploy no Render — checklist

Guia para colocar o Produzzy no ar de forma estável. Vale tanto para o
Blueprint (`render.yaml`) quanto para serviços já existentes — neste caso,
aplique só os ajustes de configuração descritos aqui.

---

## 1. Banco de dados

- [ ] Um Postgres gerenciado (Render Postgres) dedicado à API.
- [ ] `DATABASE_URL` da API aponta para ele (no Blueprint isso é automático via
      `fromDatabase`).
- [ ] **Nunca** apontar `DATABASE_URL` para o banco de testes. O banco de testes
      (`DATABASE_URL_TEST`) só existe em ambiente local/CI.

## 2. Variáveis de ambiente da API (`produzzy-api`)

| Variável | Valor | Observação |
|---|---|---|
| `PRODUZZY_ENV` | `production` | **Crítico.** Sem isso a API sobe com `SECRET_KEY` padrão pública (qualquer um forja JWT). Com `production`, a API se recusa a subir se `SECRET_KEY`/`ALLOWED_ORIGINS` estiverem fracos — isso é proposital. |
| `PRODUZZY_SECRET_KEY` | string aleatória ≥ 32 chars | Use o "Generate" do Render. Trocar essa chave invalida todas as sessões. |
| `PRODUZZY_ALLOWED_ORIGINS` | ex. `https://produzzy-web.onrender.com` | Origem **exata** do frontend, sem barra final. Aceita lista separada por vírgula. Produção rejeita `*` e o valor padrão. |
| `PRODUZZY_JWT_ALGORITHM` | `HS256` | |
| `PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | |
| `DB_POOL_RECYCLE_SECONDS` | `1800` | Opcional. Recicla conexões antes do Postgres do Render derrubar as ociosas (evita 500 intermitente após inatividade). Default já é 1800. |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | `5` / `10` | Opcional. Ajuste conforme o limite de conexões do plano do banco. |
| `PRODUZZY_GOOGLE_CLIENT_ID` / `_SECRET` | credenciais OAuth | Só se usar login com Google. |
| `PRODUZZY_CLOUDINARY_*` | credenciais Cloudinary | Só se usar upload de avatar. |

> `RENDER_GIT_COMMIT` é injetado pelo Render automaticamente e vira o
> `api_version` em `/health` — não precisa configurar.

## 3. Migrations

- [ ] O deploy roda `alembic upgrade head` **antes** de trocar a versão no ar.
  - Blueprint: `preDeployCommand: alembic upgrade head` (já no `render.yaml`).
  - Serviço manual: adicione um **Pre-Deploy Command** = `alembic upgrade head`
    (Settings → Build & Deploy), com Root Directory = `backend`.
- [ ] Neste deploy entra a migration **`0012_products_qty_nonneg`** (constraint
      `CHECK (quantity >= 0)` em `products`). Se o `upgrade` falhar aqui, há
      linha com estoque negativo no banco — corrija o dado antes de repetir.

## 4. Health check

- [ ] Health Check Path = **`/health`** (rápido, não toca o banco).
- [ ] **Não** usar `/ready` como health check — ele bate no Postgres e faz o
      serviço oscilar quando o banco pisca. `/ready` serve para diagnóstico
      manual.

## 5. Frontend (`produzzy-web`, static site)

- [ ] Build: `npm ci && npm run build` · Publish: `dist` · Root: `frontend`.
- [ ] Rewrite **`/* → /index.html`** (tipo *Rewrite*, não *Redirect*). Sem isso,
      abrir/atualizar `/join/<token>` ou `/invites/<token>/accept` dá 404.
- [ ] `VITE_API_URL` = URL pública da API (ex. `https://produzzy-api.onrender.com`),
      sem barra final. É lida em build time — **rebuild** ao mudar.
- [ ] `VITE_GOOGLE_CLIENT_ID` se usar login com Google.
- [ ] O valor de `VITE_API_URL` tem que estar dentro de
      `PRODUZZY_ALLOWED_ORIGINS` invertido: a origem do frontend precisa estar
      liberada na API (passo 2).

## 6. Google OAuth (se aplicável)

- [ ] No Google Cloud Console, "Authorized JavaScript origins" e "redirect URIs"
      incluem a origem do frontend (a mesma de `PRODUZZY_ALLOWED_ORIGINS`).
- [ ] `PRODUZZY_GOOGLE_CLIENT_ID` na API == `VITE_GOOGLE_CLIENT_ID` no frontend.

## 7. Smoke test pós-deploy

```bash
API=https://produzzy-api.onrender.com

curl -s $API/health        # {"status":"ok", "api_version":"<commit>"}
curl -s $API/ready         # {"status":"ready"}
curl -s -X POST $API/auth/login -H 'content-type: application/json' \
  -d '{"email":"x@x.com","password":"errada"}'   # 401 em PT, não 500
```

- [ ] `api_version` no `/health` é o commit atual (confirma que subiu a versão nova).
- [ ] Login real funciona pelo site.
- [ ] Criar produto, dar entrada/saída de estoque, criar reposição.
- [ ] Excluir um workspace de teste que tenha produto + reposição (era o bug
      corrigido neste deploy).

## 8. Limitações conhecidas (aceitáveis para teste, revisar antes de "produção real")

- **Rate limiting é por processo/instância** (memória local). Com mais de 1
  worker/instância o limite efetivo multiplica, e zera a cada deploy. Para valer
  precisa de store compartilhado (Redis).
- **Geração de etiquetas/QR em lote** é CPU síncrona dentro do request; várias
  chamadas simultâneas podem saturar um plano pequeno.
- **Sem monitoramento de erros** (Sentry/APM). Só há logs de request no stdout.
