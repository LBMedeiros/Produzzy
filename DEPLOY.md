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
| `PRODUZZY_CLOUDINARY_CLOUD_NAME` / `_API_KEY` / `_API_SECRET` | credenciais Cloudinary | **As três juntas** para o upload de foto de perfil funcionar (Configurações → Foto de perfil). Pegue em cloudinary.com → Dashboard. Faltando qualquer uma, o upload responde **503 "Upload de foto de perfil ainda não configurado."** e o botão não funciona. O disco do Render é efêmero, por isso a foto vai para o Cloudinary, não para o servidor. |

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

## 6. Login com Google (se aplicável)

O código já está pronto; falta só criar as credenciais e preencher as variáveis.
O fluxo é *authorization code* em popup (Google Identity Services): o frontend
obtém um `code` e o envia à API junto com a origem, e a API troca esse code por
token no Google.

**No Google Cloud Console (uma vez):**

- [ ] APIs & Services → **OAuth consent screen**: tipo *External*, nome do app,
      e-mail de suporte, escopos `openid`, `email`, `profile`. Enquanto ficar em
      *Testing*, só os *test users* cadastrados conseguem entrar — **Publish**
      (In production) para liberar qualquer conta.
- [ ] Credentials → **Create credentials → OAuth client ID → Web application**.
- [ ] **Authorized JavaScript origins**: a origem exata do frontend
      (ex. `https://produzzy.onrender.com`) e, para dev, `http://localhost:5173`.
- [ ] **Authorized redirect URIs**: as **mesmas origens puras** (sem caminho nem
      barra final). O backend troca o code usando a origem como `redirect_uri`,
      então ela precisa estar registrada aqui — senão dá `redirect_uri_mismatch`.
- [ ] Copie o **Client ID** e o **Client Secret**.

**No Render:**

- [ ] `produzzy-api`: `PRODUZZY_GOOGLE_CLIENT_ID` e `PRODUZZY_GOOGLE_CLIENT_SECRET`.
- [ ] `produzzy-api`: `PRODUZZY_ALLOWED_ORIGINS` contém a origem do frontend.
- [ ] `produzzy-web`: `VITE_GOOGLE_CLIENT_ID` = **o mesmo** Client ID. É lido em
      build time → **rebuild** depois de setar.

Regras: o Client ID é idêntico nos dois lados; o Secret fica só na API (nunca no
frontend nem em commit). Erros comuns:

- `redirect_uri_mismatch` → a origem pura não está em *Authorized redirect URIs*.
- Botão "Login com Google ainda não configurado" → `VITE_GOOGLE_CLIENT_ID` vazio
  ou frontend não foi rebuildado após setar.
- 400 "Origem do login com Google não permitida" → origem do frontend fora de
  `PRODUZZY_ALLOWED_ORIGINS` na API.

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
- [ ] Se configurou o Cloudinary: em Configurações → Foto de perfil, enviar uma
      imagem (JPG/PNG/WebP), confirmar que aparece, e depois "Remover foto".

## 8. Limitações conhecidas (aceitáveis para teste, revisar antes de "produção real")

- **Rate limiting é por processo/instância** (memória local). Com mais de 1
  worker/instância o limite efetivo multiplica, e zera a cada deploy. Para valer
  precisa de store compartilhado (Redis).
- **Geração de etiquetas/QR em lote** é CPU síncrona dentro do request; várias
  chamadas simultâneas podem saturar um plano pequeno.
- **Sem monitoramento de erros** (Sentry/APM). Só há logs de request no stdout.
