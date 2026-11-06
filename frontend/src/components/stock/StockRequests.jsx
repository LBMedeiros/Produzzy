import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import ChatModal from '../ui/ChatModal'
import ModalPortal from '../ui/ModalPortal'
import SelectMenu from '../ui/SelectMenu'
import { formatRelativeTime } from '../../lib/activity'
import {
  getFirstName,
  stockRequestCreateRoles,
  stockRequestReviewRoles,
} from '../../lib/formatters'
import {
  approveStockRequest,
  cancelStockRequest,
  createStockRequest,
  createStockRequestMessage,
  listStockRequestMessages,
  listStockRequests,
  rejectStockRequest,
} from '../../services/stockRequestService'

const STOCK_REQUESTS_KEY = (workspaceId, status) => [
  'stock-requests',
  workspaceId,
  status,
]

const typeLabels = { entrada: 'Entrada', saida: 'Saída' }

const statusBadges = {
  approved: { label: 'Aprovada', tone: 'ok' },
  canceled: { label: 'Cancelada', tone: 'muted' },
  pending: { label: 'Pendente', tone: 'warn' },
  rejected: { label: 'Recusada', tone: 'bad' },
}

const numberFormatter = new Intl.NumberFormat('pt-BR')

function ChatIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 9 9 0 0 1-4-.9L3 21l1.9-5.5a8.38 8.38 0 0 1-.9-4 8.5 8.5 0 0 1 17 0Z" />
    </svg>
  )
}

function describeQuantity(stockRequest) {
  const requested = numberFormatter.format(stockRequest.requested_quantity)

  if (
    stockRequest.approved_quantity != null &&
    stockRequest.approved_quantity !== stockRequest.requested_quantity
  ) {
    return `${numberFormatter.format(stockRequest.approved_quantity)} de ${requested} un.`
  }

  return `${requested} un.`
}

function ModalShell({ children, eyebrow, onClose, title, isBusy = false }) {
  return (
    <ModalPortal>
      <div className="modal-backdrop" role="presentation">
        <section className="workspace-modal stock-modal" role="dialog" aria-modal="true">
          <div className="workspace-modal__header">
            <div>
              <span>{eyebrow}</span>
              <h2>{title}</h2>
            </div>
            <button
              aria-label="Fechar modal"
              className="icon-button"
              disabled={isBusy}
              onClick={onClose}
              type="button"
            >
              x
            </button>
          </div>
          {children}
        </section>
      </div>
    </ModalPortal>
  )
}

// Solicitante: ask Operação to move stock for a product.
export function StockRequestCreateModal({ onClose, onCreated, product, workspaceId }) {
  const [movementType, setMovementType] = useState('saida')
  const [quantity, setQuantity] = useState('1')
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()

    const numericQuantity = Number(quantity)

    if (!Number.isInteger(numericQuantity) || numericQuantity <= 0) {
      setError('Informe uma quantidade maior que zero.')
      return
    }

    if (movementType === 'saida' && numericQuantity > product.quantity) {
      setError('Quantidade de saída maior que o estoque atual.')
      return
    }

    if (!reason.trim()) {
      setError('Conte o motivo da solicitação.')
      return
    }

    setIsSaving(true)
    setError('')

    try {
      const created = await createStockRequest(workspaceId, {
        movement_type: movementType,
        product_id: product.id,
        quantity: numericQuantity,
        reason: reason.trim(),
      })
      await onCreated(created)
    } catch (saveError) {
      setError(saveError?.message ?? 'Não foi possível enviar a solicitação.')
      setIsSaving(false)
    }
  }

  return (
    <ModalShell eyebrow="Solicitar movimentação" isBusy={isSaving} onClose={onClose} title={product.name}>
      <form className="stock-form" noValidate onSubmit={handleSubmit}>
        <p className="stock-form__hint">
          Estoque atual: {numberFormatter.format(product.quantity)} un. Quem cuida do
          estoque vai aprovar ou recusar o pedido.
        </p>

        <label>
          Tipo
          <SelectMenu
            ariaLabel="Tipo de movimentação"
            disabled={isSaving}
            onChange={setMovementType}
            options={[
              { label: 'Saída', value: 'saida' },
              { label: 'Entrada', value: 'entrada' },
            ]}
            portal
            value={movementType}
          />
        </label>

        <label>
          Quantidade
          <input
            disabled={isSaving}
            min="1"
            onChange={(event) => {
              setQuantity(event.target.value)
              setError('')
            }}
            required
            type="number"
            value={quantity}
          />
        </label>

        <label>
          Motivo
          <textarea
            disabled={isSaving}
            maxLength={255}
            onChange={(event) => {
              setReason(event.target.value)
              setError('')
            }}
            placeholder="Ex.: pedido do cliente, amostra, devolução"
            required
            rows={3}
            value={reason}
          />
        </label>

        {error ? <p className="form-error">{error}</p> : null}

        <div className="workspace-form__actions">
          <Button disabled={isSaving} type="submit">
            {isSaving ? 'Enviando...' : 'Enviar solicitação'}
          </Button>
          <Button disabled={isSaving} onClick={onClose} variant="secondary">
            Cancelar
          </Button>
        </div>
      </form>
    </ModalShell>
  )
}

// Operação and up: approve (optionally with another quantity) or reject.
function StockRequestReviewModal({ mode, onClose, onReviewed, stockRequest, workspaceId }) {
  const isApprove = mode === 'approve'
  const [quantity, setQuantity] = useState(String(stockRequest.requested_quantity))
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const numericQuantity = Number(quantity)
  const quantityChanged =
    isApprove && numericQuantity !== stockRequest.requested_quantity

  async function handleSubmit(event) {
    event.preventDefault()

    if (isApprove && (!Number.isInteger(numericQuantity) || numericQuantity <= 0)) {
      setError('Informe uma quantidade maior que zero.')
      return
    }

    if ((quantityChanged || !isApprove) && !note.trim()) {
      setError(
        isApprove
          ? 'Informe o motivo da alteração da quantidade.'
          : 'Informe o motivo da recusa.',
      )
      return
    }

    setIsSaving(true)
    setError('')

    try {
      const reviewed = isApprove
        ? await approveStockRequest(workspaceId, stockRequest.id, {
            note: note.trim() || null,
            quantity: numericQuantity,
          })
        : await rejectStockRequest(workspaceId, stockRequest.id, note.trim())
      await onReviewed(reviewed)
    } catch (reviewError) {
      setError(reviewError?.message ?? 'Não foi possível concluir a análise.')
      setIsSaving(false)
    }
  }

  return (
    <ModalShell
      eyebrow={isApprove ? 'Aprovar solicitação' : 'Recusar solicitação'}
      isBusy={isSaving}
      onClose={onClose}
      title={stockRequest.product_name ?? 'Produto'}
    >
      <form className="stock-form" noValidate onSubmit={handleSubmit}>
        <dl className="stock-request-summary">
          <div>
            <dt>Pedido</dt>
            <dd>
              {typeLabels[stockRequest.movement_type]} de{' '}
              {numberFormatter.format(stockRequest.requested_quantity)} un.
            </dd>
          </div>
          <div>
            <dt>Por</dt>
            <dd>{stockRequest.requested_by_name ?? 'Usuário'}</dd>
          </div>
          <div>
            <dt>Estoque atual</dt>
            <dd>{numberFormatter.format(stockRequest.product_quantity ?? 0)} un.</dd>
          </div>
          <div className="stock-request-summary__wide">
            <dt>Motivo</dt>
            <dd>{stockRequest.reason}</dd>
          </div>
        </dl>

        {isApprove ? (
          <label>
            Quantidade aprovada
            <input
              disabled={isSaving}
              min="1"
              onChange={(event) => {
                setQuantity(event.target.value)
                setError('')
              }}
              type="number"
              value={quantity}
            />
          </label>
        ) : null}

        {!isApprove || quantityChanged ? (
          <label>
            {isApprove ? 'Motivo da alteração' : 'Motivo da recusa'}
            <textarea
              disabled={isSaving}
              maxLength={255}
              onChange={(event) => {
                setNote(event.target.value)
                setError('')
              }}
              rows={3}
              value={note}
            />
          </label>
        ) : null}

        {isApprove ? (
          <p className="stock-form__hint">
            Ao aprovar, a movimentação é registrada no estoque em seu nome.
          </p>
        ) : null}

        {error ? <p className="form-error">{error}</p> : null}

        <div className="workspace-form__actions">
          <Button disabled={isSaving} type="submit" variant={isApprove ? 'primary' : 'danger'}>
            {isSaving
              ? 'Salvando...'
              : isApprove
                ? 'Aprovar e movimentar'
                : 'Recusar solicitação'}
          </Button>
          <Button disabled={isSaving} onClick={onClose} variant="secondary">
            Voltar
          </Button>
        </div>
      </form>
    </ModalShell>
  )
}

// "Solicitações" section of the Estoque page. Reviewers see every pending
// request of the workspace; a Solicitante sees their own.
function StockRequestsPanel({ currentUserId, onStockChanged, role, workspaceId }) {
  const queryClient = useQueryClient()
  const isReviewer = stockRequestReviewRoles.has(role)
  const isRequester = stockRequestCreateRoles.has(role)
  const [view, setView] = useState('pending')
  const [review, setReview] = useState(null)
  const [chatRequest, setChatRequest] = useState(null)
  const [cancelingId, setCancelingId] = useState(null)
  const [feedback, setFeedback] = useState('')
  const [error, setError] = useState('')
  const canSee = isReviewer || isRequester

  const pendingQuery = useQuery({
    enabled: Boolean(workspaceId) && canSee,
    queryFn: () => listStockRequests(workspaceId, { status: 'pending' }),
    queryKey: STOCK_REQUESTS_KEY(workspaceId, 'pending'),
  })
  const closedQuery = useQuery({
    enabled: Boolean(workspaceId) && canSee && view === 'closed',
    queryFn: () => listStockRequests(workspaceId, { status: 'closed' }),
    queryKey: STOCK_REQUESTS_KEY(workspaceId, 'closed'),
  })

  if (!canSee) {
    return null
  }

  const pending = pendingQuery.data ?? []
  const activeQuery = view === 'pending' ? pendingQuery : closedQuery
  const items = activeQuery.data ?? []

  // Reviewers with nothing waiting get no section at all (unless it still has
  // a result to show, e.g. right after approving the last one); the
  // Solicitante always has it (it is where their requests live).
  if (
    isReviewer &&
    !pending.length &&
    view === 'pending' &&
    !pendingQuery.isLoading &&
    !feedback &&
    !error
  ) {
    return null
  }

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ['stock-requests', workspaceId] })
  }

  async function handleReviewed(reviewed) {
    setReview(null)
    setError('')
    setFeedback(
      reviewed.status === 'approved'
        ? `Solicitação aprovada. Estoque de ${reviewed.product_name} atualizado.`
        : 'Solicitação recusada.',
    )
    await refresh()

    if (reviewed.status === 'approved') {
      await onStockChanged?.()
    }
  }

  async function handleCancel(stockRequest) {
    setCancelingId(stockRequest.id)
    setError('')
    setFeedback('')

    try {
      await cancelStockRequest(workspaceId, stockRequest.id)
      setFeedback('Solicitação cancelada.')
      await refresh()
    } catch (cancelError) {
      setError(cancelError?.message ?? 'Não foi possível cancelar a solicitação.')
    } finally {
      setCancelingId(null)
    }
  }

  return (
    <section aria-labelledby="stock-requests-title" className="stock-requests">
      <div className="stock-requests__header">
        <p className="stock-requests__title" id="stock-requests-title">
          {isReviewer ? 'Solicitações de movimentação' : 'Minhas solicitações'}
          {pending.length ? (
            <span className="stock-requests__count" aria-label={`${pending.length} pendentes`}>
              {pending.length}
            </span>
          ) : null}
        </p>
        <div aria-label="Solicitações" className="stock-requests__views" role="tablist">
          <button
            aria-selected={view === 'pending'}
            className={`filter-pill${view === 'pending' ? ' is-active' : ''}`}
            onClick={() => setView('pending')}
            role="tab"
            type="button"
          >
            Pendentes
          </button>
          <button
            aria-selected={view === 'closed'}
            className={`filter-pill${view === 'closed' ? ' is-active' : ''}`}
            onClick={() => setView('closed')}
            role="tab"
            type="button"
          >
            Histórico
          </button>
        </div>
      </div>

      {feedback ? <p className="stock-feedback stock-feedback--success">{feedback}</p> : null}
      {error ? <p className="stock-feedback stock-feedback--error">{error}</p> : null}

      {activeQuery.isLoading ? (
        <p className="stock-requests__empty">Carregando solicitações...</p>
      ) : activeQuery.isError ? (
        <p className="stock-requests__empty">Não foi possível carregar as solicitações.</p>
      ) : !items.length ? (
        <p className="stock-requests__empty">
          {view !== 'pending'
            ? 'Nenhuma solicitação concluída ainda.'
            : isRequester
              ? 'Nenhuma solicitação pendente. Use "Solicitar" em um produto para pedir uma movimentação.'
              : 'Nenhuma solicitação pendente.'}
        </p>
      ) : (
        <ul className="stock-requests__list">
          {items.map((stockRequest) => {
            const badge = statusBadges[stockRequest.status] ?? statusBadges.pending
            const isPending = stockRequest.status === 'pending'
            const isMine = stockRequest.requested_by_user_id === currentUserId

            return (
              <li className="stock-requests__item" key={stockRequest.id}>
                <div className="stock-requests__info">
                  <strong>{stockRequest.product_name}</strong>
                  <span>
                    {typeLabels[stockRequest.movement_type]} de {describeQuantity(stockRequest)}
                    {isReviewer
                      ? ` · ${getFirstName(stockRequest.requested_by_name)}`
                      : ''}{' '}
                    · {formatRelativeTime(stockRequest.created_at)}
                  </span>
                  <span className="stock-requests__reason">{stockRequest.reason}</span>
                  {stockRequest.review_note ? (
                    <span className="stock-requests__note">
                      {getFirstName(stockRequest.reviewed_by_name)}: {stockRequest.review_note}
                    </span>
                  ) : null}
                </div>
                <div className="stock-requests__actions">
                  {isPending ? null : <Badge tone={badge.tone}>{badge.label}</Badge>}
                  {isPending && isReviewer ? (
                    <>
                      <Button
                        onClick={() => setReview({ mode: 'approve', stockRequest })}
                        size="sm"
                      >
                        Aprovar
                      </Button>
                      <Button
                        onClick={() => setReview({ mode: 'reject', stockRequest })}
                        size="sm"
                        variant="secondary"
                      >
                        Recusar
                      </Button>
                    </>
                  ) : null}
                  {isPending && isMine ? (
                    <Button
                      disabled={cancelingId === stockRequest.id}
                      onClick={() => handleCancel(stockRequest)}
                      size="sm"
                      variant="secondary"
                    >
                      {cancelingId === stockRequest.id ? 'Cancelando...' : 'Cancelar'}
                    </Button>
                  ) : null}
                  <button
                    aria-label={`Conversa da solicitação de ${stockRequest.product_name}`}
                    className="replenishment-chat-trigger"
                    onClick={() => setChatRequest(stockRequest)}
                    title="Conversa da solicitação"
                    type="button"
                  >
                    <ChatIcon />
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {review ? (
        <StockRequestReviewModal
          mode={review.mode}
          onClose={() => setReview(null)}
          onReviewed={handleReviewed}
          stockRequest={review.stockRequest}
          workspaceId={workspaceId}
        />
      ) : null}

      {chatRequest ? (
        <ChatModal
          canPost
          currentUserId={currentUserId}
          emptyText="Nenhuma mensagem ainda. Combine aqui o motivo e a confirmação do pedido."
          eyebrow="Conversa da solicitação"
          loadMessages={() => listStockRequestMessages(workspaceId, chatRequest.id)}
          onClose={() => setChatRequest(null)}
          placeholder="Escreva uma mensagem..."
          queryKey={['stock-request-messages', workspaceId, chatRequest.id]}
          sendMessage={(body) =>
            createStockRequestMessage(workspaceId, chatRequest.id, body)
          }
          title={`${typeLabels[chatRequest.movement_type]} de ${chatRequest.product_name}`}
        />
      ) : null}
    </section>
  )
}

export default StockRequestsPanel
