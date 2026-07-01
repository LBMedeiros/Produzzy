import { useCallback, useEffect, useMemo, useState } from 'react'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import StatCard from '../components/ui/StatCard'
import AssigneeAvatars from '../components/replenishment/AssigneeAvatars'
import { useAuth } from '../contexts/AuthContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import {
  getReplenishmentPriority,
  getReplenishmentQuantity,
  getReplenishmentStatus,
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
  open: { label: 'Necessário repor', tone: 'neutral' },
}

const requestFilters = [
  { label: 'Necessário repor', value: 'open' },
  { label: 'Em andamento', value: 'in_progress' },
  { label: 'Pronto para estocar', value: 'completed' },
  { label: 'Canceladas', value: 'canceled' },
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
  const [quantityNeeded, setQuantityNeeded] = useState('')
  const [notes, setNotes] = useState('')
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

  const stats = useMemo(() => {
    const outOfStock = products.filter((product) => product.quantity === 0).length
    const requiredUnits = products.reduce(
      (total, product) => total + getReplenishmentQuantity(product),
      0,
    )

    return [
      {
        label: 'Produtos em baixo estoque',
        tone: 'yellow',
        trend: 'Itens abaixo do mínimo cadastrado',
        value: formatNumber(products.length),
      },
      {
        label: 'Produtos sem estoque',
        tone: 'slate',
        trend: 'Itens com prioridade alta',
        value: formatNumber(outOfStock),
      },
      {
        label: 'Unidades necessárias',
        tone: 'blue',
        trend: 'Para atingir os estoques mínimos',
        value: formatNumber(requiredUnits),
      },
    ]
  }, [products])

  const requestCounts = useMemo(
    () =>
      requests.reduce(
        (counts, requestItem) => ({
          ...counts,
          [requestItem.status]: (counts[requestItem.status] ?? 0) + 1,
        }),
        {},
      ),
    [requests],
  )

  const filteredRequests = useMemo(
    () =>
      requests.filter((requestItem) => requestItem.status === requestFilter),
    [requestFilter, requests],
  )

  function openCreationModal(product, type) {
    setCreationModal({ product, type })
    setQuantityNeeded(String(Math.max(getReplenishmentQuantity(product), 1)))
    setNotes('')
    setFormError('')
    setSuccessMessage('')
  }

  function closeCreationModal() {
    if (!isSaving) {
      setCreationModal(null)
      setFormError('')
    }
  }

  async function handleCreateRequest(event) {
    event.preventDefault()

    const parsedQuantity = Number(quantityNeeded)

    if (!Number.isInteger(parsedQuantity) || parsedQuantity <= 0) {
      setFormError('Informe uma quantidade necessária maior que zero.')
      return
    }

    setIsSaving(true)
    setFormError('')

    try {
      const createdRequest = await createReplenishment(workspaceId, {
        notes: notes.trim() || null,
        product_id: creationModal.product.id,
        quantity_needed: parsedQuantity,
        type: creationModal.type,
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

  const productColumns = [
    {
      key: 'name',
      label: 'Produto',
      render: (product) => (
        <div className="product-cell">
          <strong>{product.name}</strong>
        </div>
      ),
    },
    { key: 'category', label: 'Categoria' },
    {
      key: 'quantity',
      label: 'Estoque atual',
      render: (product) => formatNumber(product.quantity),
    },
    {
      key: 'minimum_quantity',
      label: 'Mínimo',
      render: (product) => formatNumber(product.minimum_quantity),
    },
    {
      key: 'required_quantity',
      label: 'Necessário repor',
      render: (product) => (
        <strong className="replenishment-quantity">
          {formatNumber(getReplenishmentQuantity(product))} un.
        </strong>
      ),
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
      key: 'priority',
      label: 'Prioridade',
      render: (product) => {
        const priority = getReplenishmentPriority(product)

        return <Badge tone={priority.tone}>{priority.label}</Badge>
      },
    },
    {
      key: 'actions',
      label: 'Ações',
      render: (product) => (
        <div className="replenishment-actions">
          <Button
            onClick={() => openCreationModal(product, 'purchase')}
            size="sm"
          >
            Comprar
          </Button>
          <Button
            onClick={() => openCreationModal(product, 'production')}
            size="sm"
            variant="secondary"
          >
            Produzir
          </Button>
        </div>
      ),
    },
  ]

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
        <>
          <section className="stats-grid replenishment-stats">
            {stats.map((stat) => (
              <StatCard key={stat.label} {...stat} />
            ))}
          </section>

          <Card
            className="replenishment-table"
            title="Produtos que precisam de atenção"
            eyebrow="Estoque"
          >
            {products.length ? (
              <DataTable columns={productColumns} rows={products} />
            ) : (
              <div className="stock-empty">
                <span className="replenishment-empty__symbol" aria-hidden="true">
                  ✓
                </span>
                <h2>Tudo certo por aqui</h2>
                <p>Nenhum produto precisa de reposição no momento.</p>
              </div>
            )}
          </Card>

          <Card
            action={
              <Badge tone={filteredRequests.length ? 'warning' : 'success'}>
                {formatNumber(filteredRequests.length)} neste status
              </Badge>
            }
            className="replenishment-requests"
            title="Acompanhamento das necessidades"
            eyebrow="Acompanhamento"
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

            {filteredRequests.length ? (
              <div className="replenishment-request-grid">
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

                      <div className="replenishment-request-card__details">
                        <div>
                          <span>Quantidade</span>
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
                  Use os filtros acima para acompanhar as outras etapas da
                  reposição.
                </p>
              </div>
            )}
          </Card>
        </>
      )}

      {creationModal ? (
        <div className="modal-backdrop" role="presentation">
          <section className="workspace-modal stock-modal" role="dialog" aria-modal="true">
            <div className="workspace-modal__header">
              <div>
                <span>Reposição</span>
                <h2>Criar necessidade de reposição</h2>
              </div>
              <button
                aria-label="Fechar modal"
                className="icon-button"
                type="button"
                onClick={closeCreationModal}
              >
                x
              </button>
            </div>

            <div className="replenishment-modal__summary">
              <span>Produto selecionado</span>
              <strong>{creationModal.product.name}</strong>
              <div className="replenishment-modal__metrics">
                <div>
                  <span>Tipo</span>
                  <strong>{requestTypeLabels[creationModal.type]}</strong>
                </div>
                <div>
                  <span>Estoque atual</span>
                  <strong>{formatNumber(creationModal.product.quantity)}</strong>
                </div>
                <div>
                  <span>Mínimo cadastrado</span>
                  <strong>
                    {formatNumber(creationModal.product.minimum_quantity)}
                  </strong>
                </div>
                <div>
                  <span>Necessário repor</span>
                  <strong>{formatNumber(quantityNeeded)} un.</strong>
                </div>
              </div>
            </div>

            <form className="stock-form" onSubmit={handleCreateRequest}>
              <label>
                Quantidade prevista
                <input
                  readOnly
                  type="number"
                  value={quantityNeeded}
                />
              </label>
              <p className="stock-form__hint">
                Essa quantidade é apenas uma previsão e não altera o estoque
                automaticamente.
              </p>

              <label>
                Observação (opcional)
                <textarea
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Prazo, fornecedor ou orientação para a produção"
                  value={notes}
                />
              </label>

              {formError ? <p className="form-error">{formError}</p> : null}

              <div className="workspace-form__actions">
                <Button disabled={isSaving} type="submit">
                  {isSaving ? 'Criando...' : 'Confirmar'}
                </Button>
                <Button
                  disabled={isSaving}
                  onClick={closeCreationModal}
                  variant="secondary"
                >
                  Voltar
                </Button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </div>
  )
}

export default ProductionPage
