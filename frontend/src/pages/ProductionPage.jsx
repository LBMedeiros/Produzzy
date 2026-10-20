import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Button from '../components/ui/Button'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import ReplenishmentBoardCard from '../components/replenishment/ReplenishmentBoardCard'
import ReplenishmentChatModal from '../components/replenishment/ReplenishmentChatModal'
import ReplenishmentCreationModal from '../components/replenishment/ReplenishmentCreationModal'
import { useAuth } from '../contexts/AuthContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { needsReplenishment } from '../lib/replenishment'
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

// Board columns (docs/redesign Fase 4); stocked/canceled live in "Histórico".
const BOARD_COLUMNS = [
  { label: 'Necessário repor', value: 'open' },
  { label: 'Em andamento', value: 'in_progress' },
  { label: 'Pronto para estocar', value: 'completed' },
]
const HISTORY_FILTERS = [
  { label: 'Estocadas', value: 'stocked' },
  { label: 'Canceladas', value: 'canceled' },
]
const COLUMN_PAGE_SIZE = 12

const activeRequestStatuses = new Set(['open', 'in_progress', 'completed'])
const HISTORY_PAGE_SIZE = 12
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

  return error?.message ?? 'Não foi possível carregar as reposições.'
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
  // 'open' | 'in_progress' | 'completed' picks the column shown on phones;
  // 'history' shows stocked/canceled requests.
  const [stage, setStage] = useState('open')
  const [historyFilter, setHistoryFilter] = useState('stocked')
  const [columnLimits, setColumnLimits] = useState({})
  const now = useMemo(() => new Date(), [])
  const [focusRequestId, setFocusRequestId] = useState(null)

  // No timed polling: the board refreshes when the user comes back to the
  // tab (refetchOnWindowFocus, once the 30s staleTime passes), after each
  // action here, and on "Atualizar dados".
  const productsQuery = useQuery({
    queryKey: PRODUCTS_QUERY_KEY(workspaceId),
    queryFn: () => listAllProducts(workspaceId, { status: 'active' }),
    enabled: Boolean(workspaceId),
  })
  const requestsQuery = useQuery({
    queryKey: REPLENISHMENTS_QUERY_KEY(workspaceId),
    queryFn: () => listAllReplenishments(workspaceId, { status: 'all' }),
    enabled: Boolean(workspaceId),
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
      const focusStatus = navigationIntent.status ?? 'open'
      if (focusStatus === 'stocked' || focusStatus === 'canceled') {
        setStage('history')
        setHistoryFilter(focusStatus)
      } else {
        setStage(focusStatus)
      }
      setFocusRequestId(navigationIntent.requestId ?? null)
      onNavigationIntentHandled?.()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [navigationIntent, onNavigationIntentHandled, workspaceId])

  // "+ Nova reposição" (quick action): open the creation form for the picked
  // product, or jump to its replenishment if one is already active.
  useEffect(() => {
    if (
      navigationIntent?.type !== 'replenishment-create' ||
      navigationIntent.workspaceId !== workspaceId ||
      !productsQuery.data ||
      !requestsQuery.data
    ) {
      return undefined
    }

    const timeoutId = window.setTimeout(() => {
      const activeRequest = requestsQuery.data.find(
        (requestItem) =>
          requestItem.product_id === navigationIntent.productId &&
          activeRequestStatuses.has(requestItem.status),
      )
      const product = productsQuery.data.find(
        (item) => item.id === navigationIntent.productId,
      )

      if (activeRequest) {
        setStage(activeRequest.status)
        setFocusRequestId(activeRequest.id)
        setSuccessMessage('Este produto já tem uma reposição em andamento.')
      } else if (product) {
        setCreationModal({ product })
        setFormError('')
        setSuccessMessage('')
      }

      onNavigationIntentHandled?.()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [
    navigationIntent,
    onNavigationIntentHandled,
    productsQuery.data,
    requestsQuery.data,
    workspaceId,
  ])

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

  const columns = useMemo(() => {
    const byStatus = { completed: [], in_progress: [], open: [] }

    displayRequests.forEach((requestItem) => {
      byStatus[requestItem.status]?.push({ requestItem })
    })

    // Low-stock products with no request yet lead the "Necessário repor" column.
    byStatus.open = [
      ...lowStockProductsWithoutActiveRequest.map((product) => ({ product })),
      ...byStatus.open,
    ]

    return byStatus
  }, [displayRequests, lowStockProductsWithoutActiveRequest])

  const historyCounts = useMemo(
    () => ({
      canceled: displayRequests.filter((item) => item.status === 'canceled').length,
      stocked: displayRequests.filter((item) => item.status === 'stocked').length,
    }),
    [displayRequests],
  )
  const historyItems = useMemo(
    () => displayRequests.filter((item) => item.status === historyFilter),
    [displayRequests, historyFilter],
  )
  const historyListRef = useRef(null)
  const historyPagination = usePagination(
    historyItems,
    HISTORY_PAGE_SIZE,
    `${workspaceId}-${historyFilter}`,
    historyListRef,
  )
  const { goToItem: goToHistoryItem } = historyPagination

  function getColumnLimit(status) {
    return columnLimits[status] ?? COLUMN_PAGE_SIZE
  }

  // Opening a specific request (e.g. from the dashboard): make sure its card
  // is rendered (column "Mostrar mais" or history page), then scroll to it.
  useEffect(() => {
    if (!focusRequestId) {
      return undefined
    }

    const target = displayRequests.find((item) => item.id === focusRequestId)

    if (!target) {
      return undefined
    }

    let scrollTimeoutId
    const timeoutId = window.setTimeout(() => {
      if (columns[target.status]) {
        const index = columns[target.status].findIndex(
          (item) => item.requestItem?.id === focusRequestId,
        )
        setColumnLimits((current) => ({
          ...current,
          [target.status]: Math.max(
            current[target.status] ?? COLUMN_PAGE_SIZE,
            index + 1,
          ),
        }))
      } else {
        goToHistoryItem((item) => item.id === focusRequestId)
      }

      scrollTimeoutId = window.setTimeout(() => {
        const element = document.getElementById(
          `replenishment-request-${focusRequestId}`,
        )
        const prefersReducedMotion = window.matchMedia(
          '(prefers-reduced-motion: reduce)',
        ).matches

        element?.scrollIntoView({
          block: 'center',
          behavior: prefersReducedMotion ? 'auto' : 'smooth',
        })
        element?.classList.add('is-focused')
        window.setTimeout(() => element?.classList.remove('is-focused'), 1800)
        setFocusRequestId(null)
      }, 50)
    }, 0)

    return () => {
      window.clearTimeout(timeoutId)
      window.clearTimeout(scrollTimeoutId)
    }
  }, [columns, displayRequests, focusRequestId, goToHistoryItem])

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
      setStage('in_progress')
      setSuccessMessage(
        `Reposição de ${requestTypeLabels[createdRequest.type].toLowerCase()} iniciada. Você é o responsável.`,
      )
      await invalidateReplenishment()
    } catch (createError) {
      const friendlyMessage = getFriendlyError(createError)

      if (createError?.status === 409) {
        setCreationModal(null)
        setStage('open')
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
        setStage('completed')
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

  const cardHandlers = {
    currentUserId: user?.id,
    now,
    onAssign: handleAssigneeUpdate,
    onChat: setChatRequest,
    onCreate: openCreationModal,
    onEntry: handleRegisterEntry,
    onStatusChange: handleStatusUpdate,
  }

  function renderBoardItem(item) {
    return item.product ? (
      <ReplenishmentBoardCard
        key={`product-${item.product.id}`}
        product={item.product}
        {...cardHandlers}
      />
    ) : (
      <ReplenishmentBoardCard
        isUpdating={updatingRequestId === item.requestItem.id}
        key={item.requestItem.id}
        request={item.requestItem}
        {...cardHandlers}
      />
    )
  }

  const isHistory = stage === 'history'

  return (
    <div className="page-stack">
      <PageHeader
        actions={
          <Button onClick={refetchReplenishment} variant="secondary">
            Atualizar dados
          </Button>
        }
        subtitle="Veja produtos que precisam ser comprados, produzidos ou repostos."
        title="Reposição"
      />

      {successMessage ? (
        <p className="stock-feedback stock-feedback--success">{successMessage}</p>
      ) : null}
      {error || loadErrorMessage ? (
        <p className="stock-feedback stock-feedback--error">
          {error || loadErrorMessage}
        </p>
      ) : null}

      {/* Computer: Quadro | Histórico. Phone: one chip per stage + Histórico. */}
      <div aria-label="Visualização" className="board-views board-views--desktop" role="tablist">
        <button
          aria-selected={!isHistory}
          className={`filter-pill${!isHistory ? ' is-active' : ''}`}
          onClick={() => setStage('open')}
          role="tab"
          type="button"
        >
          Quadro
        </button>
        <button
          aria-selected={isHistory}
          className={`filter-pill${isHistory ? ' is-active' : ''}`}
          onClick={() => setStage('history')}
          role="tab"
          type="button"
        >
          Histórico
        </button>
      </div>
      <div aria-label="Etapas da reposição" className="board-views board-views--phone" role="tablist">
        {BOARD_COLUMNS.map((column) => (
          <button
            aria-selected={stage === column.value}
            className={`filter-pill${stage === column.value ? ' is-active' : ''}`}
            key={column.value}
            onClick={() => setStage(column.value)}
            role="tab"
            type="button"
          >
            {column.label}
            <span className="filter-pill__count">{columns[column.value].length}</span>
          </button>
        ))}
        <button
          aria-selected={isHistory}
          className={`filter-pill${isHistory ? ' is-active' : ''}`}
          onClick={() => setStage('history')}
          role="tab"
          type="button"
        >
          Histórico
        </button>
      </div>

      {isLoading ? (
        <div className="stock-loading">Carregando reposições...</div>
      ) : isHistory ? (
        <section aria-label="Histórico de reposições" className="board-history">
          <div className="filters-row" aria-label="Filtrar histórico">
            {HISTORY_FILTERS.map((filter) => (
              <button
                aria-pressed={historyFilter === filter.value}
                className={`filter-pill${historyFilter === filter.value ? ' is-active' : ''}`}
                key={filter.value}
                onClick={() => setHistoryFilter(filter.value)}
                type="button"
              >
                {filter.label}
                <span className="filter-pill__count">{historyCounts[filter.value]}</span>
              </button>
            ))}
          </div>
          {historyItems.length ? (
            <>
              <div className="board-history__grid" ref={historyListRef}>
                {historyPagination.pageItems.map((requestItem) =>
                  renderBoardItem({ requestItem }),
                )}
              </div>
              <Pagination
                itemLabel="reposições"
                onPageChange={historyPagination.setPage}
                page={historyPagination.page}
                pageSize={historyPagination.pageSize}
                totalItems={historyPagination.totalItems}
              />
            </>
          ) : (
            <div className="stock-empty">
              <h2>
                {historyFilter === 'stocked'
                  ? 'Nenhuma reposição estocada ainda.'
                  : 'Nenhuma reposição cancelada.'}
              </h2>
              <p>As reposições concluídas aparecem aqui.</p>
            </div>
          )}
        </section>
      ) : (
        <div className="board">
          {BOARD_COLUMNS.map((column) => {
            const items = columns[column.value]
            const limit = getColumnLimit(column.value)

            return (
              <section
                aria-labelledby={`board-col-${column.value}`}
                className={`board__col${stage === column.value ? ' is-current' : ''}`}
                key={column.value}
              >
                <h2 className="board__head" id={`board-col-${column.value}`}>
                  {column.label}
                  <span className="dashboard-panel__count">{items.length}</span>
                </h2>
                {items.length ? (
                  <>
                    {items.slice(0, limit).map(renderBoardItem)}
                    {items.length > limit ? (
                      <button
                        className="board__more"
                        onClick={() =>
                          setColumnLimits((current) => ({
                            ...current,
                            [column.value]: limit + COLUMN_PAGE_SIZE,
                          }))
                        }
                        type="button"
                      >
                        Mostrar mais ({items.length - limit})
                      </button>
                    ) : null}
                  </>
                ) : (
                  <p className="board__empty">
                    {column.value === 'open'
                      ? 'Nada abaixo do mínimo sem reposição.'
                      : column.value === 'in_progress'
                        ? 'Nenhuma reposição em andamento.'
                        : 'Nada aguardando entrada no estoque.'}
                  </p>
                )}
              </section>
            )
          })}
        </div>
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
