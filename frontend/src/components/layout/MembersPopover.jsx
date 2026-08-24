import Badge from '../ui/Badge'
import Button from '../ui/Button'
import { formatWorkspaceRole } from '../../lib/formatters'

const ROLE_OPTIONS = [
  { label: 'Admin', value: 'admin' },
  { label: 'Funcionário', value: 'employee' },
  { label: 'Visualizador', value: 'viewer' },
]
const ADMIN_MANAGED_ROLES = new Set(['employee', 'viewer'])

function formatMembersCount(count) {
  return `${count} ${count === 1 ? 'membro' : 'membros'}`
}

function MembersPopover({
  canManageRoles,
  currentMemberRole,
  currentUserId,
  error,
  feedback,
  isLoading,
  members,
  onInviteRevoke,
  onMemberRemove,
  onRoleChange,
  ownerUserId,
  removingMemberId,
  revokingInviteId,
  savingMemberId,
}) {
  const roleOptions =
    currentMemberRole === 'admin'
      ? ROLE_OPTIONS.filter((option) => ADMIN_MANAGED_ROLES.has(option.value))
      : ROLE_OPTIONS

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
        {members.map((member) => {
          const adminCanManageRole =
            currentMemberRole !== 'admin' || ADMIN_MANAGED_ROLES.has(member.role)
          const canChangeMemberRole =
            canManageRoles &&
            !member.isInvite &&
            member.role !== 'owner' &&
            member.user_id !== ownerUserId &&
            member.user_id !== currentUserId &&
            adminCanManageRole
          const canRevokeInvite =
            canManageRoles &&
            member.isInvite &&
            (currentMemberRole !== 'admin' || ADMIN_MANAGED_ROLES.has(member.role))
          const canRemoveMember =
            canManageRoles &&
            !member.isInvite &&
            member.role !== 'owner' &&
            member.user_id !== ownerUserId &&
            member.user_id !== currentUserId &&
            adminCanManageRole

          return (
            <div className="member-row" key={member.id}>
              <span className="member-avatar">{member.initials}</span>
              <div className="member-row__identity">
                <strong>{member.name}</strong>
                <small>{member.email}</small>
              </div>
              <div className="member-row__meta">
                {canChangeMemberRole ? (
                  <select
                    aria-label={`Cargo de ${member.name}`}
                    className="member-row__role-select"
                    disabled={savingMemberId !== null}
                    onChange={(event) => onRoleChange(member.id, event.target.value)}
                    value={member.role}
                  >
                    {roleOptions.map((option) => (
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
                {canRevokeInvite ? (
                  <Button
                    className="member-row__action"
                    disabled={
                      savingMemberId !== null ||
                      revokingInviteId !== null ||
                      removingMemberId !== null
                    }
                    onClick={() => onInviteRevoke(member.inviteId)}
                    size="sm"
                    variant="secondary"
                  >
                    {revokingInviteId === member.inviteId
                      ? 'Revogando...'
                      : 'Revogar'}
                  </Button>
                ) : null}
                {canRemoveMember ? (
                  <Button
                    className="member-row__action"
                    disabled={
                      savingMemberId !== null ||
                      revokingInviteId !== null ||
                      removingMemberId !== null
                    }
                    onClick={() => onMemberRemove(member.id)}
                    size="sm"
                    variant="secondary"
                  >
                    {removingMemberId === member.id ? 'Removendo...' : 'Remover'}
                  </Button>
                ) : null}
              </div>
            </div>
          )
        })}
        {!isLoading && !members.length && !error ? (
          <p className="members-popover__empty">Nenhum membro encontrado.</p>
        ) : null}
      </div>
    </div>
  )
}

export default MembersPopover
