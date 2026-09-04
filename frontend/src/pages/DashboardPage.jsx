import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import StatCard from '../components/ui/StatCard'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { getReplenishmentStatus } from '../lib/replenishment'
import { getDashboard } from '../services/dashboardService'

function getFriendlyError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para visualizar estes dados.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível carregar o dashboard.'
}

function formatNumber(value) {
  return new Intl.NumberFormat('pt-BR').format(value ?? 0)
}

function formatDate(value) {
  if (!value) {
    return 'Sem data'
  }

  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    month: '2-digit',
  }).format(new Date(value))
}

const auditActionLabels = {
  'category.created': 'Categoria criada',
  'category.deleted': 'Categoria removida',
  'category.updated': 'Categoria atualizada',
  'product.created': 'Produto criado',
  'product.deleted': 'Produto enviado para lixeira',
  'product.restored': 'Produto restaurado',
  'product.updated': 'Produto atualizado',
  'replenishment.assignee_added': 'Responsável adicionado à reposição',
  'replenishment.assignee_removed': 'Responsável removido da reposição',
  'replenishment.canceled': 'Necessidade de reposição cancelada',
  'replenishment.completed': 'Necessidade de reposição concluída',
  'replenishment.created': 'Necessidade de reposição criada',
  'replenishment.stocked': 'Entrada da reposição registrada',
  'replenishment.updated': 'Necessidade de reposição atualizada',
  'stock.movement_created': 'Estoque movimentado',
  'workspace.created': 'Workspace criado',
  'workspace.updated': 'Workspace atualizado',
}

function formatAuditLog(log) {
  const title = auditActionLabels[log.action] ?? log.action
  const metadata = log.metadata ?? {}
  const detail =
    metadata.name ??
    metadata.product_name ??
    metadata.product_id ??
    metadata.category_id ??
    metadata.movement_type ??
    log.entity_type

  return {
    detail: `Item relacionado: ${detail}`,
    id: log.id,
    time: formatDate(log.created_at),
    title,
  }
}

function DashboardPage({ onNavigate }) {
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id

  const {
    data,
    error,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['dashboard', workspaceId],
    queryFn: () => getDashboard(workspaceId),
    enabled: Boolean(workspaceId),
  })

  const summary = data?.summary ?? null
  const attentionProducts = data?.attention_products ?? []
  const recentActivity = useMemo(
    () => (data?.recent_activity ?? []).map(formatAuditLog),
    [data],
  )
  const errorMessage = error ? getFriendlyError(error) : ''

  const stats = useMemo(
    () => [
      {
        label: 'Total de produtos',
        tone: 'blue',
        trend: `${formatNumber(summary?.total_categories)} categorias cadastradas`,
        value: formatNumber(summary?.total_products),
      },
      {
        label: 'Estoque baixo',
        tone: 'yellow',
        trend: 'Abaixo do mínimo cadastrado',
        value: formatNumber(summary?.low_stock_products),
      },
      {
        label: 'Sem estoque',
        tone: 'green',
        trend: 'Produtos com quantidade zerada',
        value: formatNumber(summary?.out_of_stock_products),
      },
      {
        label: 'Movimentações',
        tone: 'slate',
        trend: 'Total registrado no workspace',
        value: formatNumber(summary?.total_stock_movements),
      },
    ],
    [summary],
  )

  const attentionColumns = [
    { key: 'name', label: 'Produto' },
    { key: 'category', label: 'Categoria' },
    { key: 'quantity', label: 'Quantidade' },
    {
      key: 'minimum_quantity',
      label: 'Mínimo',
      render: (product) => product.minimum_quantity,
    },
    {
      key: 'status',
      label: 'Status',
      render: (product) => {
        const status = getReplenishmentStatus(product)

        return <Badge tone={status.tone}>{status.label}</Badge>
      },
    },
    {
      key: 'action',
      label: 'Ação',
      render: () => (
        <Button onClick={() => onNavigate('stock')} size="sm" variant="secondary">
          Abrir estoque
        </Button>
      ),
    },
  ]

  const activityColumns = [
    { key: 'title', label: 'Atividade' },
    { key: 'detail', label: 'Detalhe' },
    { key: 'time', label: 'Quando' },
  ]
  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Dashboard</h1>
          <p>Acompanhe estoque, movimentações e necessidades de reposição.</p>
        </div>
        <Button onClick={() => refetch()} variant="secondary">
          Atualizar dados
        </Button>
      </div>

      {errorMessage ? (
        <p className="stock-feedback stock-feedback--error">{errorMessage}</p>
      ) : null}

      {isLoading ? (
        <div className="stock-loading">Carregando dashboard...</div>
      ) : (
        <>
          <section className="stats-grid">
            {stats.map((stat) => (
              <StatCard key={stat.label} {...stat} />
            ))}
          </section>

          <section className="content-grid content-grid--two">
            <Card title="Atenção do estoque" eyebrow="Inventory attention">
              {attentionProducts.length ? (
                <DataTable columns={attentionColumns} rows={attentionProducts} />
              ) : (
                <div className="stock-empty">
                  <h2>Estoque saudável</h2>
                  <p>Nenhum produto ativo está zerado ou abaixo do mínimo cadastrado.</p>
                </div>
              )}
            </Card>
            <Card title="Atividades recentes" eyebrow="Recent activity">
              {recentActivity.length ? (
                <DataTable columns={activityColumns} rows={recentActivity} />
              ) : (
                <div className="stock-empty">
                  <h2>Nenhuma atividade recente</h2>
                  <p>As ações do workspace aparecerão aqui conforme forem registradas.</p>
                </div>
              )}
            </Card>
          </section>

          <section className="feature-grid feature-grid--single">
            <Card
              className="feature-card"
              title="Atalho para etiquetas/QR Code"
              eyebrow="Identificação"
            >
              <div className="label-shortcut">
                <div className="label-shortcut__content">
                  <p>
                    Gere QR Codes, códigos de barras e etiquetas prontas para
                    impressão e identificação dos produtos.
                  </p>
                  <Button
                    className="label-shortcut__button"
                    onClick={() => onNavigate('labels')}
                  >
                    Gerar etiquetas
                  </Button>
                </div>

                <div
                  className="label-shortcut__preview"
                  role="img"
                  aria-label="Exemplo decorativo de etiqueta Produzzy"
                >
                  <div className="label-shortcut__brand">
                    <img
                      aria-hidden="true"
                      alt=""
                      src="/brand/produzzy-icon.png"
                    />
                    <strong>Produzzy</strong>
                  </div>
                  <span className="label-shortcut__product">Produto</span>
                  <div className="label-shortcut__codes">
                    <div className="label-shortcut__qr" aria-hidden="true"></div>
                    <div className="label-shortcut__barcode" aria-hidden="true"></div>
                  </div>
                </div>
              </div>
            </Card>
          </section>
        </>
      )}
    </div>
  )
}

export default DashboardPage
