import { useCallback, useEffect, useMemo, useState } from 'react'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import StatCard from '../components/ui/StatCard'
import { useWorkspace } from '../contexts/WorkspaceContext'
import {
  getReplenishmentQuantity,
  getReplenishmentStatus,
  needsReplenishment,
} from '../lib/replenishment'
import {
  getDashboardSummary,
  listRecentActivity,
} from '../services/dashboardService'
import { listLowStockProducts } from '../services/productService'

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

function formatRequiredUnits(product) {
  const quantity = getReplenishmentQuantity(product)
  const unitLabel = quantity === 1 ? 'unidade' : 'unidades'

  return `Precisa repor ${formatNumber(quantity)} ${unitLabel}`
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
    detail: `Referência: ${detail}`,
    id: log.id,
    time: formatDate(log.created_at),
    title,
  }
}

function DashboardPage({ onNavigate }) {
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id
  const [summary, setSummary] = useState(null)
  const [lowStockProducts, setLowStockProducts] = useState([])
  const [recentActivity, setRecentActivity] = useState([])
  const [activityError, setActivityError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const loadDashboard = useCallback(async () => {
    if (!workspaceId) {
      return
    }

    setIsLoading(true)
    setError('')
    setActivityError('')

    try {
      const [summaryData, lowStockItems] = await Promise.all([
        getDashboardSummary(workspaceId),
        listLowStockProducts(workspaceId),
      ])

      setSummary(summaryData)
      setLowStockProducts(lowStockItems)

      try {
        const activityItems = await listRecentActivity(workspaceId, { limit: 6 })
        setRecentActivity(activityItems.map(formatAuditLog))
      } catch (activityLoadError) {
        setRecentActivity([])
        setActivityError(getFriendlyError(activityLoadError))
      }
    } catch (loadError) {
      setError(getFriendlyError(loadError))
    } finally {
      setIsLoading(false)
    }
  }, [workspaceId])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadDashboard()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadDashboard])

  const replenishmentProducts = useMemo(
    () => lowStockProducts.filter(needsReplenishment),
    [lowStockProducts],
  )
  const attentionProducts = replenishmentProducts.slice(0, 6)
  const replenishmentPreview = replenishmentProducts.slice(0, 3)

  const stats = useMemo(
    () => [
      {
        label: 'Produtos ativos',
        tone: 'blue',
        trend: `${formatNumber(summary?.total_categories)} categorias cadastradas`,
        value: formatNumber(summary?.total_products),
      },
      {
        label: 'Baixo estoque',
        tone: 'yellow',
        trend: 'Produtos que precisam de atenção',
        value: formatNumber(replenishmentProducts.length),
      },
      {
        label: 'Quantidade em estoque',
        tone: 'green',
        trend: 'Soma dos produtos ativos',
        value: formatNumber(summary?.total_stock_quantity),
      },
      {
        label: 'Movimentações registradas',
        tone: 'slate',
        trend: 'Histórico do workspace',
        value: formatNumber(summary?.total_stock_movements),
      },
    ],
    [replenishmentProducts, summary],
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
        <Button onClick={loadDashboard} variant="secondary">
          Atualizar dados
        </Button>
      </div>

      {error ? <p className="stock-feedback stock-feedback--error">{error}</p> : null}

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
            <Card title="Produtos que precisam de atenção" eyebrow="Estoque">
              {attentionProducts.length ? (
                <DataTable columns={attentionColumns} rows={attentionProducts} />
              ) : (
                <div className="stock-empty">
                  <h2>Nenhum produto em baixo estoque</h2>
                  <p>Os produtos ativos estão acima da quantidade mínima cadastrada.</p>
                </div>
              )}
            </Card>
            <Card title="Atividades recentes" eyebrow="Histórico">
              {activityError ? (
                <p className="stock-feedback stock-feedback--error">
                  {activityError}
                </p>
              ) : recentActivity.length ? (
                <DataTable columns={activityColumns} rows={recentActivity} />
              ) : (
                <div className="stock-empty">
                  <h2>Nenhuma atividade recente</h2>
                  <p>As ações do workspace aparecerão aqui conforme forem registradas.</p>
                </div>
              )}
            </Card>
          </section>

          <section className="feature-grid">
            <Card
              action={
                <Button
                  onClick={() => onNavigate('production')}
                  size="sm"
                  variant="secondary"
                >
                  Ver reposição
                </Button>
              }
              className="feature-card"
              title="Necessidades de reposição"
              eyebrow="Estoque"
            >
              {replenishmentPreview.length ? (
                <div className="replenishment-preview-list">
                  {replenishmentPreview.map((product) => {
                    const status = getReplenishmentStatus(product)

                    return (
                      <div className="replenishment-preview-item" key={product.id}>
                        <div>
                          <strong>{product.name}</strong>
                          <span>{formatRequiredUnits(product)}</span>
                        </div>
                        <Badge tone={status.tone}>{status.label}</Badge>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="replenishment-preview-empty">
                  <strong>Tudo certo por aqui</strong>
                  <span>Nenhum produto precisa de reposição no momento.</span>
                </div>
              )}
            </Card>
            <Card
              className="feature-card"
              title="Atalho para etiquetas/QR Code"
              eyebrow="Identificação"
            >
              <div className="label-shortcut">
                <div className="label-shortcut__content">
                  <p>
                    Gere QR Codes, códigos de barras, etiquetas individuais e folhas
                    A4 para identificar produtos no estoque, reposição e expedição.
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
