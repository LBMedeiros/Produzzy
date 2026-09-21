import Badge from '../ui/Badge'
import Button from '../ui/Button'
import SelectMenu from '../ui/SelectMenu'
import { memberTitleOptions } from '../../lib/formatters'

const ADMIN_MANAGED_ROLES = new Set(['employee', 'viewer'])

function formatMembersCount(count) {
  return `${count} ${count === 1 ? 'membro' : 'membros'}`
}

function MembersPopover({
  canManageRoles,
  canManageTitles,
  currentMemberRole,
  currentUserId,
  error,
  feedback,
  isLoading,
  members,
  onInviteRevoke,
  onMemberRemove,
  onTitleChange,
  ownerUserId,
  removingMemberId,
  revokingInviteId,
  savingMemberId,
  savingTitleMemberId,
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
        {members.map((member) => {
          const adminCanManageRole =
            currentMemberRole !== 'admin' || ADMIN_MANAGED_ROLES.has(member.role)
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
                {!member.isInvite && canManageTitles ? (
                  <SelectMenu
                    ariaLabel={`Cargo de ${member.name}`}
                    className="member-row__title-select"
                    disabled={savingTitleMemberId !== null}
                    onChange={(value) => onTitleChange(member.id, value)}
                    options={[
                      { label: 'Sem cargo', value: '' },
                      ...memberTitleOptions.map((title) => ({
                        label: title,
                        value: title,
                      })),
                    ]}
                    portal
                    value={member.title || ''}
                  />
                ) : !member.isInvite && member.title ? (
                  <span className="member-row__title">{member.title}</span>
                ) : null}
              </div>
              <div className="member-row__meta">
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
