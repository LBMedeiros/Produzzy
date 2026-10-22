import { daysSince } from '../../lib/activity'
import { getFirstName } from '../../lib/formatters'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import SelectMenu from '../ui/SelectMenu'
import StockLevel from '../ui/StockLevel'
import AssigneeAvatars from './AssigneeAvatars'

const numberFormatter = new Intl.NumberFormat('pt-BR')
// Same threshold as the dashboard's "paradas" (backend STALLED_REPLENISHMENT_AFTER).
const STALLED_AFTER_DAYS = 3

const typeLabels = {
  production: 'produção',
  purchase: 'compra',
}

function formatAge(days) {
  if (days === 0) {
    return 'hoje'
  }

  return days === 1 ? 'ontem' : `há ${days} dias`
}

// "aberta há 2 dias", "há 4 dias parada" (amber), "pronta hoje"...
function getTimeNote(request, now) {
  if (request.status === 'open') {
    return { text: `aberta ${formatAge(daysSince(request.created_at, now))}` }
  }

  if (request.status === 'in_progress') {
    const idleDays = daysSince(request.updated_at, now)

    return idleDays >= STALLED_AFTER_DAYS
      ? { stalled: true, text: `há ${idleDays} dias parada` }
      : { text: `atualizada ${formatAge(idleDays)}` }
  }

  if (request.status === 'completed') {
    return { text: `pronta ${formatAge(daysSince(request.completed_at ?? request.updated_at, now))}` }
  }

  if (request.status === 'stocked') {
    return { text: `estocada ${formatAge(daysSince(request.updated_at, now))}` }
  }

  return { text: `cancelada ${formatAge(daysSince(request.updated_at, now))}` }
}

function ChatIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 9 9 0 0 1-4-.9L3 21l1.9-5.5a8.38 8.38 0 0 1-.9-4 8.5 8.5 0 0 1 17 0Z" />
    </svg>
  )
}

// One card of the replenishment board (docs/redesign Fase 4): name,
// categoria · tipo, StockLevel with "repor N", who is on it, how long it has
// been there, and the next action. No badge repeating the column name.
function ReplenishmentBoardCard({
  assignableMembers,
  currentUserId,
  isUpdating = false,
  now,
  onAddAssignee,
  onAssign,
  onChat,
  onCreate,
  onEntry,
  onRemoveAssignee,
  onStatusChange,
  product,
  request,
}) {
  if (product) {
    return (
      <article className="board-card board-card--compact">
        <div className="board-card__row">
          <div className="board-card__head">
            <h3>{product.name}</h3>
            <span>{product.category} · sem reposição aberta</span>
          </div>
          <Button onClick={() => onCreate(product)} size="sm">
            Repor
          </Button>
        </div>
        <StockLevel
          minimum={product.minimum_quantity}
          quantity={product.quantity}
          showReplenish
        />
      </article>
    )
  }

  const assignees = request.assignees ?? []
  const isAssigned = assignees.some((assignee) => assignee.id === currentUserId)
  const canAssign = request.status === 'open' || request.status === 'in_progress'
  const isFinished = request.status === 'stocked' || request.status === 'canceled'
  const timeNote = getTimeNote(request, now)
  const lead = assignees[0]?.name ?? request.assigned_to_name
  // Owners/admins get `assignableMembers` and can add anyone not yet on it.
  const canManageAssignees = Boolean(assignableMembers) && canAssign
  const addOptions = canManageAssignees
    ? assignableMembers
        .filter((member) => !assignees.some((assignee) => assignee.id === member.user_id))
        .map((member) => ({ label: member.user_name, value: member.user_id }))
    : []

  return (
    <article
      className={`board-card${timeNote.stalled ? ' is-stalled' : ''}`}
      id={`replenishment-request-${request.id}`}
    >
      <div className="board-card__head">
        <h3>{request.product_name}</h3>
        <span>
          {request.product_category ? `${request.product_category} · ` : ''}
          {typeLabels[request.type] ?? request.type} ·{' '}
          {numberFormatter.format(request.quantity_needed)} un. previstas
        </span>
        {isFinished ? (
          <Badge tone={request.status === 'stocked' ? 'ok' : 'muted'}>
            {request.status === 'stocked' ? 'Estocada' : 'Cancelada'}
          </Badge>
        ) : null}
      </div>

      {request.current_quantity != null && request.minimum_quantity != null ? (
        <StockLevel
          minimum={request.minimum_quantity}
          quantity={request.current_quantity}
          showReplenish={!isFinished}
        />
      ) : null}

      <div className="board-card__meta">
        <AssigneeAvatars
          assignees={assignees}
          isUpdating={isUpdating}
          onRemove={
            canManageAssignees
              ? (userId) => onRemoveAssignee(request, userId)
              : undefined
          }
        />
        <span className="board-card__who">
          {lead ? getFirstName(lead) : null}
          {lead && assignees.length > 1 ? ` +${assignees.length - 1}` : null}
        </span>
        <span className={`board-card__time${timeNote.stalled ? ' is-stalled' : ''}`}>
          {timeNote.text}
        </span>
      </div>

      {request.notes ? <p className="board-card__notes">{request.notes}</p> : null}

      <div className="board-card__actions">
        {request.status === 'open' ? (
          <Button
            disabled={isUpdating}
            onClick={() => onStatusChange(request, 'in_progress')}
            size="sm"
          >
            Iniciar
          </Button>
        ) : null}
        {request.status === 'in_progress' ? (
          <Button
            disabled={isUpdating}
            onClick={() => onStatusChange(request, 'completed')}
            size="sm"
          >
            Marcar como pronta
          </Button>
        ) : null}
        {request.status === 'completed' ? (
          <Button onClick={() => onEntry(request)} size="sm">
            Estocar
          </Button>
        ) : null}
        {canAssign && !isAssigned ? (
          <Button
            disabled={isUpdating}
            onClick={() => onAssign(request, true)}
            size="sm"
            variant="secondary"
          >
            Assumir
          </Button>
        ) : null}
        {addOptions.length ? (
          <SelectMenu
            ariaLabel={`Adicionar responsável à reposição de ${request.product_name}`}
            className="board-card__assign"
            disabled={isUpdating}
            menuClassName="board-card__assign-menu"
            onChange={(userId) => onAddAssignee(request, Number(userId))}
            options={addOptions}
            placeholder="+ Responsável"
            portal
            value=""
          />
        ) : null}
        {canAssign ? (
          <button
            className="board-card__cancel"
            disabled={isUpdating}
            onClick={() => onStatusChange(request, 'canceled')}
            type="button"
          >
            Cancelar
          </button>
        ) : null}
        <button
          aria-label={`Abrir chat da reposição de ${request.product_name}`}
          className="replenishment-chat-trigger board-card__chat"
          onClick={() => onChat(request)}
          title="Chat da reposição"
          type="button"
        >
          <ChatIcon />
        </button>
      </div>
    </article>
  )
}

export default ReplenishmentBoardCard
