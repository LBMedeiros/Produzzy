import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import Pagination from '../components/ui/Pagination'
import AssigneeAvatars from '../components/replenishment/AssigneeAvatars'
import ReplenishmentChatModal from '../components/replenishment/ReplenishmentChatModal'
import ReplenishmentCreationModal from '../components/replenishment/ReplenishmentCreationModal'
import { useAuth } from '../contexts/AuthContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import {
  getReplenishmentQuantity,
  needsReplenishment,
} from '../lib/replenishment'
import { usePagination } from '../lib/pagination'
import { listAllProducts } from '../services/productService'
import {
  assignReplenishmentToMe,
  createReplenishment,
  listAllReplenishments,
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
const REPLENISHMENT_REFRESH_INTERVAL_MS = 30000
const REPLENISHMENT_PAGE_SIZE = 12
const PRODUCTS_QUERY_KEY = (workspaceId) => ['products', workspaceId, 'active']
const REPLENISHMENTS_QUERY_KEY = (workspaceId) => [
  'replenishments',
  workspaceId,
  'all',
]

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

function ProductionPage({
  navigationIntent,
  onNavigate,
  onNavigationIntentHandled,
}) {
  const { user } = useAuth()
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id
  const queryClient = useQueryClient()
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [creationModal, setCreationModal] = useState(null)
  const [chatRequest, setChatRequest] = useState(null)
  const [formError, setFormError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [updatingRequestId, setUpdatingRequestId] = useState(null)
  const [requestFilter, setRequestFilter] = useState('open')
  const [focusRequestId, setFocusRequestId] = useState(null)

  // refetchInterval + refetchOnWindowFocus (default on) replace the manual
  // 10s poll + visibilitychange/focus listeners this page used to hand-roll;
  // React Query also dedupes overlapping fetches on its own.
  const productsQuery = useQuery({
    queryKey: PRODUCTS_QUERY_KEY(workspaceId),
    queryFn: () => listAllProducts(workspaceId, { status: 'active' }),
    enabled: Boolean(workspaceId),
    refetchInterval: REPLENISHMENT_REFRESH_INTERVAL_MS,
  })
  const requestsQuery = useQuery({
    queryKey: REPLENISHMENTS_QUERY_KEY(workspaceId),
    queryFn: () => listAllReplenishments(workspaceId, { status: 'all' }),
    enabled: Boolean(workspaceId),
    refetchInterval: REPLENISHMENT_REFRESH_INTERVAL_MS,
  })

  const products = useMemo(
    () => (productsQuery.data ?? []).filter(needsReplenishment),
    [productsQuery.data],
  )
  const requests = useMemo(() => requestsQuery.data ?? [], [requestsQuery.data])
  const isLoading = productsQuery.isLoading || requestsQuery.isLoading
  const loadError = productsQuery.error ?? requestsQuery.error
  const loadErrorMessage = loadError ? getFriendlyError(loadError) : ''

  function refetchReplenishment() {
    productsQuery.refetch()
    requestsQuery.refetch()
  }

  function invalidateReplenishment() {
    return Promise.all([
      queryClient.invalidateQueries({ queryKey: ['products', workspaceId] }),
      queryClient.invalidateQueries({
        queryKey: ['replenishments', workspaceId],
      }),
    ])
  }

  useEffect(() => {
    if (
      navigationIntent?.type !== 'replenishment-focus' ||
      navigationIntent.workspaceId !== workspaceId
    ) {
      return undefined
    }

    const timeoutId = window.setTimeout(() => {
      setRequestFilter(navigationIntent.status ?? 'open')
      setFocusRequestId(navigationIntent.requestId ?? null)
      onNavigationIntentHandled?.()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [navigationIntent, onNavigationIntentHandled, workspaceId])

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

  // Suggestions (low-stock products with no request yet) come first, then the
  // requests, in one list so the board can be paginated as a whole.
  const boardItems = useMemo(
    () => [
      ...(requestFilter === 'open'
        ? lowStockProductsWithoutActiveRequest.map((product) => ({ product }))
        : []),
      ...filteredRequests.map((requestItem) => ({ requestItem })),
    ],
    [filteredRequests, lowStockProductsWithoutActiveRequest, requestFilter],
  )
  const boardListRef = useRef(null)
  const boardPagination = usePagination(
    boardItems,
    REPLENISHMENT_PAGE_SIZE,
    `${workspaceId}-${requestFilter}`,
    boardListRef,
  )
  const { goToItem: goToBoardItem } = boardPagination
  const pageSuggestions = boardPagination.pageItems
    .filter((item) => item.product)
    .map((item) => item.product)
  const pageRequests = boardPagination.pageItems
    .filter((item) => item.requestItem)
    .map((item) => item.requestItem)
  const visibleItemCount = boardItems.length

  // Opening a specific request (e.g. from the dashboard) jumps to the page
  // that holds it, then scrolls it into view.
  useEffect(() => {
    if (
      !focusRequestId ||
      !boardItems.some((item) => item.requestItem?.id === focusRequestId)
    ) {
      return undefined
    }

    let scrollTimeoutId
    const timeoutId = window.setTimeout(() => {
      goToBoardItem((item) => item.requestItem?.id === focusRequestId)

      scrollTimeoutId = window.setTimeout(() => {
        const target = document.getElementById(
          `replenishment-request-${focusRequestId}`,
        )
        const prefersReducedMotion = window.matchMedia(
          '(prefers-reduced-motion: reduce)',
        ).matches

        target?.scrollIntoView({
          block: 'center',
          behavior: prefersReducedMotion ? 'auto' : 'smooth',
        })
        setFocusRequestId(null)
      }, 0)
    }, 0)

    return () => {
      window.clearTimeout(timeoutId)
      window.clearTimeout(scrollTimeoutId)
    }
  }, [boardItems, focusRequestId, goToBoardItem])

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
    setError('')
    setSuccessMessage('')

    try {
      const createdRequest = await createReplenishment(workspaceId, {
        product_id: creationModal.product.id,
        // "Quem confirma inicia": start the need and make the creator the
        // responsible in one step (no manual "Iniciar/Assumir" afterwards).
        assigned_to_user_id: user?.id,
        ...requestData,
      })
      queryClient.setQueryData(
        REPLENISHMENTS_QUERY_KEY(workspaceId),
        (current) => [createdRequest, ...(current ?? [])],
      )
      queryClient.setQueryData(PRODUCTS_QUERY_KEY(workspaceId), (current) =>
        (current ?? []).filter(
          (product) => product.id !== createdRequest.product_id,
        ),
      )
      setCreationModal(null)
      setRequestFilter('in_progress')
      setSuccessMessage(
        `Reposição de ${requestTypeLabels[createdRequest.type].toLowerCase()} iniciada. Você é o responsável.`,
      )
      await invalidateReplenishment()
    } catch (createError) {
      const friendlyMessage = getFriendlyError(createError)

      if (createError?.status === 409) {
        setCreationModal(null)
        setRequestFilter('open')
        await invalidateReplenishment()
        setError(friendlyMessage)
      } else {
        setFormError(friendlyMessage)
      }
    } finally {
      setIsSaving(false)
    }
  }

  async function handleStatusUpdate(requestItem, status) {
    setUpdatingRequestId(requestItem.id)
    setError('')
    setSuccessMessage('')

    try {
      const updatedRequest = await updateReplenishment(
        workspaceId,
        requestItem.id,
        { status },
      )
      queryClient.setQueryData(
        REPLENISHMENTS_QUERY_KEY(workspaceId),
        (current) =>
          (current ?? []).map((currentRequest) =>
            currentRequest.id === requestItem.id
              ? updatedRequest
              : currentRequest,
          ),
      )
      await invalidateReplenishment()

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

      queryClient.setQueryData(
        REPLENISHMENTS_QUERY_KEY(workspaceId),
        (current) =>
          (current ?? []).map((currentRequest) =>
            currentRequest.id === requestItem.id
              ? updatedRequest
              : currentRequest,
          ),
      )
      await invalidateReplenishment()
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
        <Button onClick={refetchReplenishment} variant="secondary">
          Atualizar dados
        </Button>
      </div>

      {successMessage ? (
        <p className="stock-feedback stock-feedback--success">{successMessage}</p>
      ) : null}
      {error || loadErrorMessage ? (
        <p className="stock-feedback stock-feedback--error">
          {error || loadErrorMessage}
        </p>
      ) : null}

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
                onClick={() => {
                  setFocusRequestId(null)
                  setRequestFilter(filter.value)
                }}
                type="button"
              >
                <span>{filter.label}</span>
                <strong>{requestCounts[filter.value] ?? 0}</strong>
              </button>
            ))}
          </div>

          <div
            className="replenishment-status-content"
            key={requestFilter}
            ref={boardListRef}
          >
            {visibleItemCount ? (
              <>
              <div className="replenishment-request-grid">
                {requestFilter === 'open'
                  ? pageSuggestions.map((product) => (
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
                {pageRequests.map((requestItem) => {
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
                      id={`replenishment-request-${requestItem.id}`}
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
                      <div className="replenishment-request-card__assignees-actions">
                        {(requestItem.status === 'open' ||
                          requestItem.status === 'in_progress') &&
                        !isCurrentUserAssigned ? (
                          <Button
                            disabled={isUpdating}
                            onClick={() =>
                              handleAssigneeUpdate(requestItem, true)
                            }
                            size="sm"
                            variant="secondary"
                          >
                            Assumir tarefa
                          </Button>
                        ) : null}
                        <button
                          aria-label="Abrir chat da reposição"
                          className="replenishment-chat-trigger"
                          onClick={() => setChatRequest(requestItem)}
                          title="Chat da reposição"
                          type="button"
                        >
                          <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 9 9 0 0 1-4-.9L3 21l1.9-5.5a8.38 8.38 0 0 1-.9-4 8.5 8.5 0 0 1 17 0Z" />
                          </svg>
                        </button>
                      </div>
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
              <Pagination
                itemLabel="necessidades"
                onPageChange={boardPagination.setPage}
                page={boardPagination.page}
                pageSize={boardPagination.pageSize}
                totalItems={boardPagination.totalItems}
              />
              </>
            ) : (
              <div className="stock-empty">
                <h2>Nenhuma necessidade neste status.</h2>
                <p>
                  Use as etapas acima para acompanhar o quadro de reposição.
                </p>
              </div>
            )}
          </div>
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

      {chatRequest ? (
        <ReplenishmentChatModal
          canPost={(chatRequest.assignees ?? []).some(
            (assignee) => assignee.id === user?.id,
          )}
          currentUserId={user?.id}
          onClose={() => setChatRequest(null)}
          productLabel={chatRequest.product_name ?? 'Reposição'}
          requestId={chatRequest.id}
          workspaceId={workspaceId}
        />
      ) : null}
    </div>
  )
}

export default ProductionPage
