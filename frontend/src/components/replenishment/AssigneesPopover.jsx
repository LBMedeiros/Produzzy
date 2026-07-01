import Badge from '../ui/Badge'
import { getInitials } from '../../lib/formatters'

const roleLabels = {
  admin: 'Admin',
  employee: 'Colaborador',
  owner: 'Owner',
  viewer: 'Visualizador',
}

function AssigneesPopover({ assignees }) {
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
              {roleLabels[assignee.role] ?? assignee.role ?? 'Membro'}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  )
}

export default AssigneesPopover
