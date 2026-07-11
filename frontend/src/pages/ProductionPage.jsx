import { useCallback, useEffect, useMemo, useState } from 'react'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import AssigneeAvatars from '../components/replenishment/AssigneeAvatars'
import ReplenishmentCreationModal from '../components/replenishment/ReplenishmentCreationModal'
import { useAuth } from '../contexts/AuthContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import {
  getReplenishmentQuantity,
  needsReplenishment,
} from '../lib/replenishment'
import { listLowStockProducts } from '../services/productService'
import {
  assignReplenishmentToMe,
  createReplenishment,
  listReplenishments,
  unassignReplenishmentFromMe,
  updateReplenishment,
} from '../services/replenishmentService'

const requestTypeLabels = {
  purchase: 'Compra',
  production: 'Produção',
}

const requestStatus = {
  canceled: { label: 'Cancelada', tone: 'danger' },
  completed: { label: 'Pronto para estocar', tone: 'success' },
  in_progress: { label: 'Em andamento', tone: 'warning' },
  open: { label: 'Necessário repor', tone: 'replenishment-open' },
  stocked: { label: 'Estocado', tone: 'success' },
}

const requestFilters = [
  { label: 'Necessário repor', value: 'open' },
  { label: 'Em andamento', value: 'in_progress' },
  { label: 'Pronto para estocar', value: 'completed' },
  { label: 'Estocado', value: 'stocked' },
  { label: 'Canceladas', value: 'canceled' },
]

const activeRequestStatuses = new Set(['open', 'in_progress', 'completed'])

function getFriendlyError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para realizar esta ação.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível carregar as necessidades de reposição.'
}

function formatNumber(value) {
  return new Intl.NumberFormat('pt-BR').format(value ?? 0)
}

function formatDate(value) {
  if (!value) {
    return 'Sem data'
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

function ProductionPage({ onNavigate }) {
  const { user } = useAuth()
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id
  const [products, setProducts] = useState([])
  const [requests, setRequests] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [creationModal, setCreationModal] = useState(null)
  const [formError, setFormError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [updatingRequestId, setUpdatingRequestId] = useState(null)
  const [requestFilter, setRequestFilter] = useState('open')

  const loadReplenishment = useCallback(async () => {
    if (!workspaceId) {
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const [lowStockItems, requestItems] = await Promise.all([
        listLowStockProducts(workspaceId),
        listReplenishments(workspaceId, { limit: 100, status: 'all' }),
      ])
      setProducts(lowStockItems.filter(needsReplenishment))
      setRequests(requestItems)
    } catch (loadError) {
      setProducts([])
      setRequests([])
      setError(getFriendlyError(loadError))
    } finally {
      setIsLoading(false)
    }
  }, [workspaceId])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadReplenishment()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadReplenishment])

  const displayRequests = useMemo(() => {
    const seenActiveProductIds = new Set()

    return requests.filter((requestItem) => {
      if (!activeRequestStatuses.has(requestItem.status)) {
        return true
      }

      if (seenActiveProductIds.has(requestItem.product_id)) {
        return false
      }

      seenActiveProductIds.add(requestItem.product_id)
      return true
    })
  }, [requests])

  const lowStockProductsWithoutActiveRequest = useMemo(() => {
    const activeProductIds = new Set(
      displayRequests
        .filter((requestItem) => activeRequestStatuses.has(requestItem.status))
        .map((requestItem) => requestItem.product_id),
    )

    return products.filter((product) => !activeProductIds.has(product.id))
  }, [displayRequests, products])

  const requestCounts = useMemo(
    () => {
      const counts = displayRequests.reduce(
        (counts, requestItem) => ({
          ...counts,
          [requestItem.status]: (counts[requestItem.status] ?? 0) + 1,
        }),
        {},
      )

      counts.open =
        (counts.open ?? 0) + lowStockProductsWithoutActiveRequest.length

      return counts
    },
    [displayRequests, lowStockProductsWithoutActiveRequest.length],
  )

  const filteredRequests = useMemo(
    () =>
      displayRequests.filter(
        (requestItem) => requestItem.status === requestFilter,
      ),
    [displayRequests, requestFilter],
  )

  const visibleItemCount =
    filteredRequests.length +
    (requestFilter === 'open' ? lowStockProductsWithoutActiveRequest.length : 0)

  function openCreationModal(product) {
    setCreationModal({ product })
    setFormError('')
    setSuccessMessage('')
  }

  function closeCreationModal() {
    if (!isSaving) {
      setCreationModal(null)
      setFormError('')
    }
  }

  async function handleCreateRequest(requestData) {
    setIsSaving(true)
    setFormError('')

    try {
      const createdRequest = await createReplenishment(workspaceId, {
        product_id: creationModal.product.id,
        ...requestData,
      })
      setRequests((currentRequests) => [createdRequest, ...currentRequests])
      setCreationModal(null)
      setRequestFilter('open')
      setSuccessMessage(
        `Necessidade de ${requestTypeLabels[createdRequest.type].toLowerCase()} criada com sucesso.`,
      )
    } catch (createError) {
      setFormError(getFriendlyError(createError))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleStatusUpdate(requestItem, status) {
    setUpdatingRequestId(requestItem.id)
    setError('')
    setSuccessMessage('')

    try {
      await updateReplenishment(workspaceId, requestItem.id, { status })
      const requestItems = await listReplenishments(workspaceId, {
        limit: 100,
        status: 'all',
      })
      setRequests(requestItems)

      if (status === 'completed') {
        setSuccessMessage(
          'Reposição pronta para estocar. Registre a entrada pela tela de Estoque.',
        )
        setRequestFilter('completed')
      } else {
        setSuccessMessage('Status da necessidade atualizado com sucesso.')
      }
    } catch (updateError) {
      setError(getFriendlyError(updateError))
    } finally {
      setUpdatingRequestId(null)
    }
  }

  async function handleAssigneeUpdate(requestItem, shouldAssign) {
    setUpdatingRequestId(requestItem.id)
    setError('')
    setSuccessMessage('')

    try {
      const updatedRequest = shouldAssign
        ? await assignReplenishmentToMe(workspaceId, requestItem.id)
        : await unassignReplenishmentFromMe(workspaceId, requestItem.id)

      setRequests((currentRequests) =>
        currentRequests.map((currentRequest) =>
          currentRequest.id === requestItem.id ? updatedRequest : currentRequest,
        ),
      )
      setSuccessMessage(
        shouldAssign
          ? 'Você assumiu esta necessidade de reposição.'
          : 'Você saiu desta necessidade de reposição.',
      )
    } catch (updateError) {
      setError(getFriendlyError(updateError))
    } finally {
      setUpdatingRequestId(null)
    }
  }

  function handleRegisterEntry(requestItem) {
    onNavigate('stock', {
      request: requestItem,
      type: 'replenishment-entry',
      workspaceId,
    })
  }

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Reposição</h1>
          <p>Veja produtos que precisam ser comprados, produzidos ou repostos.</p>
        </div>
        <Button onClick={loadReplenishment} variant="secondary">
          Atualizar dados
        </Button>
      </div>

      {successMessage ? (
        <p className="stock-feedback stock-feedback--success">{successMessage}</p>
      ) : null}
      {error ? <p className="stock-feedback stock-feedback--error">{error}</p> : null}

      {isLoading ? (
        <div className="stock-loading">Carregando necessidades de reposição...</div>
      ) : (
        <Card
          action={
            <Badge tone={visibleItemCount ? 'warning' : 'success'}>
              {formatNumber(visibleItemCount)} neste status
            </Badge>
          }
          className="replenishment-requests"
          title="Acompanhamento das necessidades"
          eyebrow="Quadro de reposição"
        >
          <div
            aria-label="Filtrar necessidades por status"
            className="replenishment-status-tabs"
          >
            {requestFilters.map((filter) => (
              <button
                className={requestFilter === filter.value ? 'is-active' : ''}
                key={filter.value}
                onClick={() => setRequestFilter(filter.value)}
                type="button"
              >
                <span>{filter.label}</span>
                <strong>{requestCounts[filter.value] ?? 0}</strong>
              </button>
            ))}
          </div>

          {visibleItemCount ? (
            <div className="replenishment-request-grid">
              {requestFilter === 'open'
                ? lowStockProductsWithoutActiveRequest.map((product) => (
                    <article
                      className="replenishment-request-card replenishment-request-card--suggestion"
                      key={`product-${product.id}`}
                    >
                      <div className="replenishment-request-card__header replenishment-request-card__header--open">
                        <div>
                          <span>{product.category}</span>
                          <h3>{product.name}</h3>
                        </div>
                        <Badge tone="replenishment-open">
                          Necessário repor
                        </Badge>
                      </div>

                      <div className="replenishment-request-card__details replenishment-request-card__details--stock">
                        <div>
                          <span>Estoque atual</span>
                          <strong>{formatNumber(product.quantity)} un.</strong>
                        </div>
                        <div>
                          <span>Mínimo</span>
                          <strong>
                            {formatNumber(product.minimum_quantity)} un.
                          </strong>
                        </div>
                        <div>
                          <span>Necessário repor</span>
                          <strong>
                            {formatNumber(getReplenishmentQuantity(product))} un.
                          </strong>
                        </div>
                      </div>

                      <div className="replenishment-request-card__actions">
                        <Button onClick={() => openCreationModal(product)} size="sm">
                          Repor
                        </Button>
                      </div>
                    </article>
                  ))
                : null}
              {filteredRequests.map((requestItem) => {
                const status =
                  requestStatus[requestItem.status] ?? requestStatus.open
                const assignees = requestItem.assignees ?? []
                const isCurrentUserAssigned = assignees.some(
                  (assignee) => assignee.id === user?.id,
                )
                const isUpdating = updatingRequestId === requestItem.id

                return (
                  <article
                    className="replenishment-request-card"
                    key={requestItem.id}
                  >
                    {requestItem.status === 'open' ? (
                      <div className="replenishment-request-card__header replenishment-request-card__header--open">
                        <div>
                          <span>{requestItem.product_category}</span>
                          <h3>{requestItem.product_name}</h3>
                        </div>
                        <div className="replenishment-request-card__badges replenishment-request-card__badges--open">
                          <Badge tone="neutral">
                            {requestTypeLabels[requestItem.type]}
                          </Badge>
                          <Badge tone={status.tone}>{status.label}</Badge>
                        </div>
                      </div>
                    ) : (
                      <div className="replenishment-request-card__header">
                        <div>
                          <span>{requestItem.product_category}</span>
                          <h3>{requestItem.product_name}</h3>
                        </div>
                        <div className="replenishment-request-card__badges">
                          <Badge tone="neutral">
                            {requestTypeLabels[requestItem.type]}
                          </Badge>
                          <Badge tone={status.tone}>{status.label}</Badge>
                        </div>
                      </div>
                    )}

                    <div className="replenishment-request-card__details">
                      <div>
                        <span>Quantidade prevista</span>
                        <strong>
                          {formatNumber(requestItem.quantity_needed)} un.
                        </strong>
                      </div>
                      <div>
                        <span>Criado em</span>
                        <strong>{formatDate(requestItem.created_at)}</strong>
                      </div>
                    </div>

                    <div className="replenishment-request-card__assignees">
                      <div>
                        <span>Responsáveis</span>
                        <AssigneeAvatars assignees={assignees} />
                      </div>
                      {requestItem.status === 'open' ||
                      requestItem.status === 'in_progress' ? (
                        <Button
                          disabled={isUpdating}
                          onClick={() =>
                            handleAssigneeUpdate(
                              requestItem,
                              !isCurrentUserAssigned,
                            )
                          }
                          size="sm"
                          variant="secondary"
                        >
                          {isCurrentUserAssigned
                            ? 'Sair da tarefa'
                            : 'Assumir tarefa'}
                        </Button>
                      ) : null}
                    </div>

                    {requestItem.notes ? (
                      <p className="replenishment-request-card__notes">
                        {requestItem.notes}
                      </p>
                    ) : null}

                    <div className="replenishment-request-card__actions">
                      {requestItem.status === 'open' ? (
                        <>
                          <Button
                            disabled={isUpdating}
                            onClick={() =>
                              handleStatusUpdate(requestItem, 'in_progress')
                            }
                            size="sm"
                          >
                            Marcar em andamento
                          </Button>
                          <Button
                            className="replenishment-actions__cancel"
                            disabled={isUpdating}
                            onClick={() =>
                              handleStatusUpdate(requestItem, 'canceled')
                            }
                            size="sm"
                            variant="secondary"
                          >
                            Cancelar
                          </Button>
                        </>
                      ) : null}
                      {requestItem.status === 'in_progress' ? (
                        <>
                          <Button
                            disabled={isUpdating}
                            onClick={() =>
                              handleStatusUpdate(requestItem, 'completed')
                            }
                            size="sm"
                          >
                            Marcar como pronto
                          </Button>
                          <Button
                            className="replenishment-actions__cancel"
                            disabled={isUpdating}
                            onClick={() =>
                              handleStatusUpdate(requestItem, 'canceled')
                            }
                            size="sm"
                            variant="secondary"
                          >
                            Cancelar
                          </Button>
                        </>
                      ) : null}
                      {requestItem.status === 'completed' ? (
                        <div className="replenishment-ready-action">
                          <p>
                            Registre a entrada no estoque para atualizar a
                            quantidade.
                          </p>
                          <Button
                            onClick={() => handleRegisterEntry(requestItem)}
                            size="sm"
                          >
                            Registrar entrada no estoque
                          </Button>
                        </div>
                      ) : null}
                      {requestItem.status === 'stocked' ? (
                        <p className="replenishment-stocked-note">
                          Entrada registrada no estoque.
                        </p>
                      ) : null}
                      {requestItem.status === 'canceled' ? (
                        <p className="replenishment-canceled-note">
                          Necessidade cancelada. Nenhuma ação pendente.
                        </p>
                      ) : null}
                    </div>
                  </article>
                )
              })}
            </div>
          ) : (
            <div className="stock-empty">
              <h2>Nenhuma necessidade neste status.</h2>
              <p>
                Use as etapas acima para acompanhar o quadro de reposição.
              </p>
            </div>
          )}
        </Card>
      )}

      {creationModal ? (
        <ReplenishmentCreationModal
          error={formError}
          isSaving={isSaving}
          onClose={closeCreationModal}
          onSubmit={handleCreateRequest}
          product={creationModal.product}
        />
      ) : null}
    </div>
  )
}

export default ProductionPage
