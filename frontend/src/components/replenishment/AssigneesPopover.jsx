import Badge from '../ui/Badge'
import { formatWorkspaceRole, getInitials } from '../../lib/formatters'

// `onRemove` is passed only to owners/admins, who manage assignees.
function AssigneesPopover({ assignees, isUpdating = false, onRemove }) {
  return (
    <div
      aria-label="Responsáveis pela necessidade"
      className="replenishment-assignees-popover"
      role="dialog"
    >
      <div className="replenishment-assignees-popover__header">
        <strong>Responsáveis</strong>
        <span>{assignees.length}</span>
      </div>
      <div className="replenishment-assignees-popover__list">
        {assignees.map((assignee) => (
          <div className="replenishment-assignee-row" key={assignee.id}>
            <span className="replenishment-assignee-avatar">
              {getInitials(assignee.name)}
            </span>
            <div>
              <strong>{assignee.name}</strong>
              <small>{assignee.email}</small>
            </div>
            <Badge tone="neutral">
              {formatWorkspaceRole(assignee.role)}
            </Badge>
            {onRemove ? (
              <button
                aria-label={`Remover ${assignee.name} dos responsáveis`}
                className="replenishment-assignee-row__remove"
                disabled={isUpdating}
                onClick={() => onRemove(assignee.id)}
                type="button"
              >
                Remover
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  )
}

export default AssigneesPopover
