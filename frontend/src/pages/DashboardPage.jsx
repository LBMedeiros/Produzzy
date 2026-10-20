import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import MovementsChart from '../components/dashboard/MovementsChart'
import { useQuickActions } from '../components/layout/QuickActions'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import StockLevel from '../components/ui/StockLevel'
import SummaryTile from '../components/ui/SummaryTile'
import UserAvatar from '../components/ui/UserAvatar'
import { useAuth } from '../contexts/AuthContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { daysSince, describeActivity, formatRelativeTime } from '../lib/activity'
import { getFirstName } from '../lib/formatters'
import { getDashboard } from '../services/dashboardService'

const numberFormatter = new Intl.NumberFormat('pt-BR')
const RECENT_ACTIVITY_LIMIT = 5

function getFriendlyError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para visualizar estes dados.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível carregar o início.'
}

function getGreeting(now) {
  const hour = now.getHours()

  if (hour < 12) {
    return 'Bom dia'
  }

  return hour < 18 ? 'Boa tarde' : 'Boa noite'
}

// "Segunda, 20 de outubro"
function formatToday(now) {
  const weekday = new Intl.DateTimeFormat('pt-BR', { weekday: 'long' })
    .format(now)
    .replace('-feira', '')
  const day = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'long' }).format(
    now,
  )

  return `${weekday.charAt(0).toUpperCase()}${weekday.slice(1)}, ${day}`
}

function pluralize(count, singular, plural) {
  return `${numberFormatter.format(count)} ${count === 1 ? singular : plural}`
}

function getTypeLabel(type) {
  return type === 'production' ? 'produção' : 'compra'
}

function getAssigneeName(request) {
  return request.assignees?.[0]?.name ?? request.assigned_to_name ?? null
}

function ActivitySentence({ actor, parts }) {
  return (
    <>
      <b>{actor}</b>
      {parts.map((part, index) => {
        const key = `${part.kind}-${index}`

        if (part.kind === 'strong') {
          return (
            <span key={key}>
              {' '}
              <b>{part.value}</b>
            </span>
          )
        }

        if (part.kind === 'in' || part.kind === 'out') {
          return (
            <span key={key}>
              {' '}
              <span className={part.kind === 'in' ? 'activity-in' : 'activity-out'}>
                {part.value}
              </span>
            </span>
          )
        }

        return <span key={key}> {part.value}</span>
      })}
    </>
  )
}

function DashboardPage({ onNavigate }) {
  const { user } = useAuth()
  const { activeWorkspace } = useWorkspace()
  const quickActions = useQuickActions()
  const workspaceId = activeWorkspace?.id
  const canAct = Boolean(quickActions?.canAct)
  const now = useMemo(() => new Date(), [])

  const { data, error, isLoading } = useQuery({
    queryKey: ['dashboard', workspaceId],
    queryFn: () => getDashboard(workspaceId),
    enabled: Boolean(workspaceId),
  })

  const summary = data?.summary ?? {}
  const attentionProducts = useMemo(() => data?.attention_products ?? [], [data])
  const zeroProducts = attentionProducts.filter((product) => product.quantity === 0)
  const lowProducts = attentionProducts.filter((product) => product.quantity > 0)
  const stalledRequests = data?.stalled_replenishments ?? []
  const readyRequests = data?.ready_replenishments ?? []
  const movementsByDay = data?.movements_by_day ?? []
  const activity = (data?.recent_activity ?? []).slice(0, RECENT_ACTIVITY_LIMIT)
  const canSeeActivity = Boolean(data?.recent_activity?.length)

  const attentionCount =
    (summary.out_of_stock_products ?? 0) +
    (summary.low_stock_products ?? 0) +
    stalledRequests.length +
    readyRequests.length
  const shownAttentionCount =
    attentionProducts.length + stalledRequests.length + readyRequests.length
  const attentionText = attentionCount
    ? `${pluralize(attentionCount, 'item precisa', 'itens precisam')} de atenção hoje`
    : 'Nada precisa da sua atenção hoje'

  const movementsDelta = (summary.movements_today ?? 0) - (summary.movements_yesterday ?? 0)
  const lowCount = summary.low_stock_products ?? 0
  const zeroCount = summary.out_of_stock_products ?? 0
  const zeroWithout = summary.out_of_stock_without_replenishment ?? 0

  function openProductReplenishment(product) {
    if (product.active_replenishment_id) {
      onNavigate('production', {
        requestId: product.active_replenishment_id,
        status: product.active_replenishment_status,
        type: 'replenishment-focus',
        workspaceId,
      })
      return
    }

    onNavigate('production', {
      productId: product.id,
      type: 'replenishment-create',
      workspaceId,
    })
  }

  function renderProductRow(product) {
    const hasRequest = Boolean(product.active_replenishment_id)

    return (
      <div className="attention-row" key={product.id}>
        <div className="attention-row__name">
          <strong>{product.name}</strong>
          <span>{product.category}</span>
        </div>
        <StockLevel
          minimum={product.minimum_quantity}
          quantity={product.quantity}
          showReplenish
        />
        {hasRequest ? (
          <Button onClick={() => openProductReplenishment(product)} size="sm" variant="secondary">
            Ver reposição
          </Button>
        ) : canAct ? (
          <Button onClick={() => openProductReplenishment(product)} size="sm">
            Repor
          </Button>
        ) : (
          <span />
        )}
      </div>
    )
  }

  function renderRequestRow(request, kind) {
    const assignee = getAssigneeName(request)
    const days = daysSince(request.updated_at, now)
    const note =
      kind === 'stalled'
        ? `${assignee ? `Com ${getFirstName(assignee)}` : 'Sem responsável'} há ${pluralize(days, 'dia', 'dias')}, sem atualização`
        : `${numberFormatter.format(request.quantity_needed)} un. previstas · pronta para estocar`

    return (
      <div className="attention-row" key={`${kind}-${request.id}`}>
        <div className="attention-row__name">
          <strong>{request.product_name}</strong>
          <span>
            {request.product_category ? `${request.product_category} · ` : ''}
            {getTypeLabel(request.type)}
          </span>
        </div>
        <div className="attention-row__note">
          {assignee ? <UserAvatar className="avatar--xs" name={assignee} /> : null}
          <span>{note}</span>
        </div>
        {kind === 'stalled' ? (
          <button
            className="attention-row__pill-button"
            onClick={() =>
              onNavigate('production', {
                requestId: request.id,
                status: request.status,
                type: 'replenishment-focus',
                workspaceId,
              })
            }
            type="button"
          >
            <Badge tone="warn">Parada</Badge>
          </button>
        ) : canAct ? (
          <Button
            onClick={() =>
              onNavigate('stock', { request, type: 'replenishment-entry', workspaceId })
            }
            size="sm"
            variant="secondary"
          >
            Estocar
          </Button>
        ) : (
          <Badge tone="ok">Pronta</Badge>
        )}
      </div>
    )
  }

  return (
    <div className="page-stack dashboard">
      <section className="dashboard-hello">
        <div>
          <h1>
            {getGreeting(now)}, {getFirstName(user?.name)}
          </h1>
          <p>
            {formatToday(now)}
            {data ? ` · ${attentionText}` : ''}
          </p>
        </div>
        {canAct ? (
          <Button
            className="dashboard-hello__action"
            icon="+"
            onClick={() => quickActions.openQuickAction('movement')}
          >
            Movimentar estoque
          </Button>
        ) : null}
      </section>

      {error ? (
        <p className="stock-feedback stock-feedback--error">{getFriendlyError(error)}</p>
      ) : null}

      {isLoading ? (
        <div className="stock-loading">Carregando início...</div>
      ) : data ? (
        <>
          <section aria-label="Resumo" className="summary-tiles">
            <SummaryTile
              hint={`em ${pluralize(summary.total_categories ?? 0, 'categoria', 'categorias')}`}
              label="Produtos ativos"
              value={numberFormatter.format(summary.total_products ?? 0)}
            />
            <SummaryTile
              highlight={lowCount > 0}
              hint={
                lowCount
                  ? `${numberFormatter.format(summary.low_stock_in_replenishment ?? 0)} já em reposição`
                  : 'tudo acima do mínimo'
              }
              label="Abaixo do mínimo"
              tone="warn"
              value={numberFormatter.format(lowCount)}
            />
            <SummaryTile
              highlight={zeroCount > 0}
              hint={
                !zeroCount
                  ? 'nenhum produto zerado'
                  : zeroWithout
                    ? `${numberFormatter.format(zeroWithout)} sem reposição aberta`
                    : 'todos com reposição aberta'
              }
              label="Zerados"
              tone="bad"
              value={numberFormatter.format(zeroCount)}
            />
            <SummaryTile
              hint={
                movementsDelta === 0 ? (
                  'igual a ontem'
                ) : (
                  <>
                    <b className={movementsDelta > 0 ? 'is-up' : 'is-down'}>
                      {movementsDelta > 0 ? '+' : '−'}
                      {numberFormatter.format(Math.abs(movementsDelta))}
                    </b>{' '}
                    em relação a ontem
                  </>
                )
              }
              label="Movimentações hoje"
              tone="ok"
              value={numberFormatter.format(summary.movements_today ?? 0)}
            />
          </section>

          <div className="dashboard-grid">
            <section aria-labelledby="attention-title" className="dashboard-panel">
              <div className="dashboard-panel__head">
                <h2 id="attention-title">
                  Precisa da sua atenção
                  {shownAttentionCount ? (
                    <span className="dashboard-panel__count">{attentionCount}</span>
                  ) : null}
                </h2>
                <Link to="/stock">Ver estoque</Link>
              </div>

              {shownAttentionCount ? (
                <>
                  {zeroProducts.length ? (
                    <div className="attention-group">
                      <p className="attention-group__label">
                        <i aria-hidden="true" className="status-dot status-dot--bad" />
                        Zerados
                      </p>
                      {zeroProducts.map(renderProductRow)}
                    </div>
                  ) : null}
                  {lowProducts.length ? (
                    <div className="attention-group">
                      <p className="attention-group__label">
                        <i aria-hidden="true" className="status-dot status-dot--warn" />
                        Abaixo do mínimo
                      </p>
                      {lowProducts.map(renderProductRow)}
                    </div>
                  ) : null}
                  {stalledRequests.length || readyRequests.length ? (
                    <div className="attention-group">
                      <p className="attention-group__label">
                        <i aria-hidden="true" className="status-dot" />
                        Reposições
                      </p>
                      {stalledRequests.map((request) => renderRequestRow(request, 'stalled'))}
                      {readyRequests.map((request) => renderRequestRow(request, 'ready'))}
                    </div>
                  ) : null}
                </>
              ) : (
                <div className="dashboard-panel__empty">
                  <strong>Tudo em dia</strong>
                  <p>Nenhum produto zerado ou abaixo do mínimo, e nenhuma reposição parada.</p>
                </div>
              )}
            </section>

            <div className="dashboard-col">
              <section aria-labelledby="movements-title" className="dashboard-panel">
                <div className="dashboard-panel__head">
                  <h2 id="movements-title">Movimentações · 7 dias</h2>
                </div>
                <div className="movements-legend">
                  <span>
                    <i aria-hidden="true" className="movements-legend__in" />
                    Entradas
                  </span>
                  <span>
                    <i aria-hidden="true" className="movements-legend__out" />
                    Saídas
                  </span>
                </div>
                <div className="movements-chart-wrap">
                  <MovementsChart days={movementsByDay} />
                </div>
              </section>

              {canSeeActivity ? (
                <section aria-labelledby="activity-title" className="dashboard-panel">
                  <div className="dashboard-panel__head">
                    <h2 id="activity-title">Atividade recente</h2>
                    <button
                      className="dashboard-panel__link"
                      onClick={() =>
                        onNavigate('stock', { type: 'stock-history', workspaceId })
                      }
                      type="button"
                    >
                      Ver histórico
                    </button>
                  </div>
                  <ul className="activity-feed">
                    {activity.map((log) => (
                      <li key={log.id}>
                        <UserAvatar
                          className="avatar--sm"
                          name={log.user_name}
                          src={log.user_avatar_url}
                        />
                        <p>
                          <ActivitySentence {...describeActivity(log, user?.id)} />
                          <time dateTime={log.created_at}>
                            {formatRelativeTime(log.created_at, now)}
                          </time>
                        </p>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}

export default DashboardPage
