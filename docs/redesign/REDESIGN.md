# Redesign do Produzzy — guia de implementação

Este documento é a especificação do novo visual do app (todas as telas autenticadas).
A referência visual é o protótipo **`docs/redesign/prototipo.html`**: abra no navegador e use os
botões **Computador / Celular** e **Escuro / Claro** no topo. O protótipo é estático (dados de
exemplo, sem requisições); a implementação deve usar os dados reais da API.

> **Para quem for implementar (incluindo o Claude Code):** leia este arquivo inteiro, o
> `AGENTS.md` e o `CLAUDE.md` antes de começar. Implemente **uma fase por vez** (seção 5), rode as
> verificações da seção 6 ao final de cada fase e pare para revisão humana antes da próxima.

---

## 1. Princípios

1. **Cor só para status.** Superfícies neutras e calmas; cor aparece apenas onde há algo a
   comunicar: âmbar = abaixo do mínimo, vermelho = zerado, verde = ok/concluído, azul = ação
   principal e seleção. Nada de blocos inteiros saturados (ex.: os cards coloridos atuais do
   Dashboard).
2. **Barra de nível de estoque como linguagem visual comum.** Todo produto mostra
   `quantidade de mínimo` + uma barra fina (seção 3.2), no Dashboard, no Estoque e na Reposição.
3. **Ação ao alcance.** O botão de ação de cada item fica na própria linha/card (Repor, Estocar,
   Movimentar). Ações raras (ex.: "Criar workspace") saem do destaque.
4. **Celular é app.** Menu fixo no rodapé, cabeçalho de uma linha, botão "+" flutuante, listas
   compactas. Nenhuma tela pode ter rolagem lateral.
5. **Mostrar só o que importa.** Seções vazias somem ou encolhem (ex.: "Reposições prontas para
   estocar" só aparece se houver itens). Nada de texto repetido (ex.: o selo "Necessário repor"
   em todo card da aba "Necessário repor").
6. **Tudo em português.** Nenhum rótulo em inglês na interface (hoje há "INVENTORY ATTENTION" e
   "RECENT ACTIVITY" no Dashboard).

## 2. O que NÃO muda

- **Tela de login** (`LoginPage`, `.auth-landing`, `lib/useAuthLandingMotion.js`): já está no
  visual novo. Não alterar.
- **Geração de QR Codes / etiquetas** (`backend/app/services/qrcode_service.py`): os QR Codes reais
  têm a **logo do Produzzy no centro** com correção de erro **H**. Manter exatamente assim. A tela
  de Etiquetas deve exibir as imagens reais geradas pela API, não desenhos.
- Regras de negócio, permissões, isolamento por workspace e auditoria do `AGENTS.md`.
- Stack: React 19 + Vite, **CSS puro em `src/styles/global.css`**, sem biblioteca de componentes,
  sem CSS-in-JS, sem Tailwind. Serviços em `services/*Service.js` chamando `lib/api.js`.
- Paginação existente (`components/ui/Pagination.jsx`, `lib/pagination.js`) e a busca de todas
  as páginas da API (`fetchAllPages`).

## 3. Sistema visual

### 3.1 Tokens de cor

Os valores abaixo são os do protótipo (classe `.app` e `.app[data-scheme="light"]`). Na
implementação, mapeie-os para os tokens já existentes em `:root` (claro) e
`:root[data-theme="dark"]` (escuro) de `global.css`, reaproveitando os nomes atuais quando houver
equivalente (`--bg`, `--surface`, `--text`, `--muted`, `--border`, `--blue`…). O tema continua
controlado pelo `ThemeContext`.

| Papel | Escuro | Claro |
|---|---|---|
| Fundo da página | `#07111f` | `#f3f6fb` |
| Painel / card | `#0d1829` | `#ffffff` |
| Superfície elevada (trilhos, campos) | `#12203a` | `#f5f8fc` |
| Linha / borda | `#1f2d44` | `#e2e8f0` |
| Texto | `#e5edf7` | `#0f172a` |
| Texto secundário | `#8a9bb3` | `#5b6b82` |
| Texto terciário | `#5f7190` | `#8a99ae` |
| Ação principal (botão) | `#3b82f6` | `#2563eb` |
| Texto de destaque / links | `#93c5fd` | `#1d4ed8` |
| Ok | `#4ade80` (fundo 14%) | `#16a34a` (fundo 10%) |
| Atenção (abaixo do mínimo) | `#fbbf24` (fundo 14%) | `#d97706` (fundo 12%) |
| Crítico (zerado) | `#f87171` (fundo 14%) | `#dc2626` (fundo 10%) |
| Saídas no gráfico | `#64748b` | `#94a3b8` |

### 3.2 Componentes compartilhados (criar em `src/components/ui/`)

- **`StockLevel`** — rótulo `<b>{quantidade}</b> de {mínimo}` (+ opcional `repor {mínimo − qtd}`
  à direita) e barra de 6 px, raio cheio. Largura = `min(100%, qtd / mínimo)`. Cor:
  zerado → vermelho (barra vazia com contorno vermelho sutil); abaixo do mínimo → âmbar;
  igual/acima → verde. Números com `font-variant-numeric: tabular-nums`. Reaproveitar a regra de
  status que já existe em `lib/formatters.js` / `lib/replenishment.js` em vez de duplicar.
- **Pílula de status** — usar/estender `Badge`: tons `warn`, `bad`, `ok`, `muted`; texto curto
  ("Abaixo do mínimo", "Zerado", "Em estoque", "Parada", "Em andamento", "Pendente").
- **Cartão-resumo (tile)** — fundo neutro, rótulo com bolinha colorida, número grande, linha de
  contexto ("3 já em reposição", "+5 em relação a ontem"). Substitui o visual atual do
  `StatCard`.
- **Chips de filtro com contagem** — ex.: `Todos 131 · Abaixo do mínimo 12 · Zerados 4`.
- **`PageHeader`** — título, subtítulo e área de ações à direita (some no celular quando a ação
  vai para o botão "+").
- **Botão de escanear** — azul cheio com gradiente leve, ícone num quadrado branco de 48 px,
  título + uma linha curta, seta "›" à direita (ver Etiquetas no protótipo).

### 3.3 Tipografia e espaçamento

- Mesma família atual (Inter / system-ui). Títulos de página 26 px (22 px no celular), títulos de
  painel 16 px, corpo 14 px, rótulos de seção 11,5 px em caixa alta com `letter-spacing: .06em`.
- Raio: painéis 14 px, cards 12 px, botões e campos 10 px, pílulas 999 px.
- Espaçamento com `gap` em grid/flex; padding de página 24 px (16/14 px no celular).

### 3.4 Movimento

- Transição curta ao trocar de tela (fade + 8 px, ~350 ms) — já existe `.page-transition`.
- Hover discreto em botões e no botão de escanear.
- Respeitar `prefers-reduced-motion` em tudo.

## 4. Responsividade

- **Breakpoint principal: 640 px.** Abaixo dele vale o layout de celular (seção 4.2).
- Testar sempre em **360, 390, 768, 1280 e 1440 px**, nos dois temas.
- **Nenhuma rolagem lateral** em nenhuma tela. Itens de grid/flex que contêm texto precisam de
  `min-width: 0`; listas de chips longas rolam dentro do próprio container
  (`overflow-x: auto`), nunca a página.
- Respeitar áreas seguras do iPhone (`env(safe-area-inset-*)`) no menu de baixo.

### 4.1 Computador (≥ 640 px)

- **Barra lateral** em trilho de ícones (como hoje, colapsada) com estado ativo em azul suave.
- **Topo**: seletor de workspace (com **"Criar workspace" dentro do menu do seletor**, não mais
  como botão azul no topo), busca, "Compartilhar", avatares da equipe, avatar do usuário.

### 4.2 Celular (< 640 px)

- **Cabeçalho de uma linha**: seletor de workspace (ocupa o espaço), botão de busca, avatar.
- **Menu fixo no rodapé** (`BottomTabBar`): Início, Estoque, Reposição, Etiquetas, Conta, com
  ícone + rótulo. Deve ficar **sempre colado no rodapé**, mesmo com pouco conteúdo na tela, e o
  conteúdo da página precisa de `padding-bottom` para não ficar escondido atrás dele.
- **Botão "+" flutuante** acima do menu: abre "Movimentar estoque" (Início, Estoque) e
  "Nova reposição" (Reposição). Oculto em Etiquetas e Conta.
- A barra lateral e o topo de computador ficam ocultos.

## 5. Plano em fases

Cada fase = um PR pequeno, revisável e com o app funcionando. Ao terminar uma fase, rode a
seção 6 e pare.

### Fase 0 — Fundação
- Ajustar os tokens de cor (3.1) nos dois temas em `global.css`.
- Criar `StockLevel`, estender `Badge` com os tons novos, criar `PageHeader`.
- **Pronto quando:** componentes existem e são usados em pelo menos um lugar sem mudar layout de
  página; lint e build passam.

### Fase 1 — Estrutura (menu de baixo e cabeçalho)
- `AppLayout`, `Sidebar`, `Header`: layout de computador (4.1) e de celular (4.2), com
  `BottomTabBar` e botão "+".
- Mover "Criar workspace" para dentro do seletor de workspace.
- **Pronto quando:** em 360 px o conteúdo começa logo abaixo de um cabeçalho de uma linha, o menu
  de baixo fica no rodapé em todas as telas (inclusive com pouco conteúdo) e não há rolagem
  lateral; no computador nada quebra.

### Fase 2 — Início (Dashboard)
- Saudação ("Bom dia, {nome}") + data + "N itens precisam de atenção hoje" + botão
  "+ Movimentar estoque".
- 4 tiles neutros: Produtos ativos, Abaixo do mínimo, Zerados, Movimentações hoje.
- **"Precisa da sua atenção"** agrupado: Zerados, Abaixo do mínimo, Reposições (paradas e prontas
  para estocar), com `StockLevel` e ação direta.
- **Gráfico "Movimentações · 7 dias"** (entradas × saídas por dia), SVG simples desenhado em
  escala, cores dos tokens.
- **Atividade recente legível**: "Ana deu entrada de +20 cx. em Luva nitrílica P · há 10 min"
  (nunca "Item relacionado: 1").
- **Backend necessário** (seguir o padrão router → crud → schema e as regras do `AGENTS.md`, com
  testes): incluir no retorno do dashboard (a) o nome do usuário de cada atividade e dados
  suficientes para a frase legível (nome do produto, quantidade, tipo), (b) movimentações por dia
  dos últimos 7 dias (entradas e saídas), (c) reposições "paradas" (em andamento sem atualização
  há 3+ dias) e "prontas para estocar". Tudo restrito ao workspace.
- **Pronto quando:** igual ao protótipo com dados reais, nos dois temas e no celular.

### Fase 3 — Estoque
- Faixa verde "N reposições prontas para estocar" **só quando houver**, com botão "Estocar".
- Barra de ferramentas: busca, categoria, chips com contagem (Todos, Abaixo do mínimo, Zerados,
  Histórico, Lixeira).
- Tabela: Produto (nome + categoria · unidade), Nível (`StockLevel`), Status, Último movimento
  (já vem em `last_movement` na API: "João · saída de 6 · há 1 h"), ações (Movimentar + ⋯).
- Celular: linhas compactas (nome, pílula, `StockLevel` com "repor N").
- Manter paginação, filtros e todas as ações atuais (editar, lixeira, histórico, categorias).

### Fase 4 — Reposição
- Computador: **quadro com 3 colunas** — Necessário repor, Em andamento, Pronto para estocar —
  com contagem no cabeçalho de cada coluna. Estocadas e canceladas vão para "Histórico".
- Card: nome, categoria · tipo (compra/produção), `StockLevel` com "repor N", responsável
  (avatar + nome), tempo ("aberta há 2 dias", "há 4 dias parada" em âmbar), ação.
- Sem selo repetindo o nome da coluna.
- Celular: chips/abas com as 3 etapas, cards compactos.
- Manter atribuição de responsáveis, chat de passagem de trabalho e a retenção atual.

### Fase 5 — Etiquetas
- Botão **"Escanear etiqueta"** (3.2) no topo, abrindo o scanner atual (`QrScannerModal`).
- Lista de produtos com seleção + busca; opções QR Code / Código de barras / cópias.
- **Prévia da folha** usando as imagens reais da API (com a logo no centro dos QR Codes).
- Ações: Imprimir e Baixar PDF.

### Fase 6 — Conta (Configurações)
- Duas colunas no computador (uma no celular): Perfil e tema; Segurança; Workspace (membros e
  convites pendentes separados por linha); Privacidade (baixar dados, excluir conta em destaque
  vermelho discreto).
- E-mail de recuperação com pílula **Pendente/Confirmado** e botão **"Reenviar confirmação"**
  (pode exigir um endpoint de reenvio no backend, com rate limit, seguindo o padrão de
  `/auth/resend-verification`). No formulário, o campo de senha deve se chamar
  **"Senha do Produzzy"**, com a dica "Para confirmar que é você".
- Quando o envio de e-mail falhar, a tela deve dizer isso (hoje ela sempre diz que enviou).

### Fase 7 — Acabamento
- Varredura de textos em inglês, estados vazios, foco visível em todos os controles, contraste
  nos dois temas, `prefers-reduced-motion`, telas de "Esqueci a senha" e confirmação de e-mail no
  mesmo estilo do login.

## 6. Verificação ao final de cada fase

```bash
cd frontend && npm run lint && npm run build
cd backend && python -m pytest          # quando a fase mexer no backend
```

E no navegador (`npm run dev`, com o backend rodando):
- 360, 390, 768, 1280 e 1440 px, temas escuro e claro;
- sem rolagem lateral; menu de baixo colado no rodapé no celular;
- fluxos principais funcionando: login, movimentar estoque, criar/repor/estocar reposição,
  gerar etiqueta, trocar de workspace.

O CI do GitHub (`.github/workflows/ci.yml`) roda lint, build e os testes do backend em todo PR.
