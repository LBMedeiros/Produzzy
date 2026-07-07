import Badge from '../ui/Badge'
import { formatWorkspaceRole } from '../../lib/formatters'

const ROLE_OPTIONS = [
  { label: 'Admin', value: 'admin' },
  { label: 'Funcionário', value: 'employee' },
  { label: 'Visualizador', value: 'viewer' },
]

function formatMembersCount(count) {
  return `${count} ${count === 1 ? 'membro' : 'membros'}`
}

function MembersPopover({
  canManageRoles,
  currentUserId,
  error,
  feedback,
  isLoading,
  members,
  onRoleChange,
  ownerUserId,
  savingMemberId,
}) {
  return (
    <div className="members-popover" role="dialog" aria-label="Membros do workspace">
      <div className="members-popover__header">
        <strong>Equipe do workspace</strong>
        <span>{formatMembersCount(members.length)}</span>
      </div>
      {error ? (
        <p className="members-popover__feedback members-popover__feedback--error">
          {error}
        </p>
      ) : null}
      {feedback ? (
        <p className="members-popover__feedback members-popover__feedback--success">
          {feedback}
        </p>
      ) : null}
      <div className="members-popover__list">
        {isLoading ? (
          <p className="members-popover__empty">Carregando equipe...</p>
        ) : null}
        {members.map((member) => (
          <div className="member-row" key={member.id}>
            <span className="member-avatar">{member.initials}</span>
            <div className="member-row__identity">
              <strong>{member.name}</strong>
              <small>{member.email}</small>
            </div>
            <div className="member-row__meta">
              {canManageRoles &&
              !member.isInvite &&
              member.role !== 'owner' &&
              member.user_id !== ownerUserId &&
              member.user_id !== currentUserId ? (
                <select
                  aria-label={`Cargo de ${member.name}`}
                  className="member-row__role-select"
                  disabled={savingMemberId !== null}
                  onChange={(event) => onRoleChange(member.id, event.target.value)}
                  value={member.role}
                >
                  {ROLE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="member-row__role">
                  {formatWorkspaceRole(member.role)}
                </span>
              )}
              <Badge tone={member.status === 'Ativo' ? 'success' : 'warning'}>
                {savingMemberId === member.id ? 'Salvando...' : member.status}
              </Badge>
            </div>
          </div>
        ))}
        {!isLoading && !members.length && !error ? (
          <p className="members-popover__empty">Nenhum membro encontrado.</p>
        ) : null}
      </div>
    </div>
  )
}

export default MembersPopover
