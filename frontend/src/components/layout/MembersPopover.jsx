import Badge from '../ui/Badge'
import Button from '../ui/Button'
import SelectMenu from '../ui/SelectMenu'
import {
  adminManagedRoles,
  formatWorkspaceRole,
  getMemberTitleSelectOptions,
  memberNeedsTitle,
  memberTitleOptions,
  memberTitleRoles,
  workspaceRoleDescriptions,
  workspaceRoleLevels,
} from '../../lib/formatters'

const OWNER_LABEL = 'Responsável pelo workspace'

function formatMembersCount(count) {
  return `${count} ${count === 1 ? 'membro' : 'membros'}`
}

function CrownIcon() {
  return (
    <svg aria-hidden="true" fill="none" focusable="false" viewBox="0 0 24 24">
      <path d="M4 8l4 4 4-6 4 6 4-4-1.5 10h-13z" />
      <path d="M5.5 21h13" />
    </svg>
  )
}

function MemberRowAvatar({ member }) {
  return (
    <span className="member-avatar">
      {member.avatar_url ? <img alt="" src={member.avatar_url} /> : member.initials}
    </span>
  )
}

// "O que cada cargo pode fazer?" — each level, its cargos and what it allows.
function CargoLegend() {
  return (
    <details className="members-popover__legend">
      <summary>O que cada cargo pode fazer?</summary>
      <dl>
        <div>
          <dt>
            <span className="members-popover__legend-crown" aria-hidden="true">
              <CrownIcon />
            </span>
            {OWNER_LABEL}
          </dt>
          <dd>{workspaceRoleDescriptions.owner}</dd>
        </div>
        {workspaceRoleLevels.map((role) => {
          const cargos = memberTitleOptions
            .filter((title) => memberTitleRoles[title] === role)
            .join(', ')

          return (
            <div key={role}>
              <dt>{formatWorkspaceRole(role)}</dt>
              <dd>
                {cargos !== formatWorkspaceRole(role) ? (
                  <span className="members-popover__legend-cargos">{cargos}</span>
                ) : null}
                {workspaceRoleDescriptions[role]}
              </dd>
            </div>
          )
        })}
      </dl>
    </details>
  )
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
  onInvite,
  onInviteRevoke,
  onMemberRemove,
  onTitleChange,
  ownerUserId,
  removingMemberId,
  revokingInviteId,
  savingTitleMemberId,
}) {
  const activeMembers = members.filter((member) => !member.isInvite)
  const pendingInvites = members.filter((member) => member.isInvite)
  const isBusy = revokingInviteId !== null || removingMemberId !== null
  const isAdmin = currentMemberRole === 'admin'

  function renderMemberRow(member) {
    const isOwner = !member.isInvite && (member.role === 'owner' || member.user_id === ownerUserId)
    const isSelf = member.user_id === currentUserId
    const adminCanManage = !isAdmin || adminManagedRoles.has(member.role)
    const canRevokeInvite = canManageRoles && member.isInvite && adminCanManage
    const canRemoveMember =
      canManageRoles && !member.isInvite && !isOwner && !isSelf && adminCanManage
    // The owner picks their own cargo (it does not change their access);
    // everyone else gets theirs from the owner or the Administração.
    const canChangeTitle =
      canManageTitles &&
      !member.isInvite &&
      (isOwner ? isSelf && !isAdmin : !isSelf && adminCanManage)
    const needsTitle = !member.isInvite && memberNeedsTitle(member)
    const titleOptions = getMemberTitleSelectOptions(
      isAdmin && !isOwner ? adminManagedRoles : null,
    )

    return (
      <div className="member-row" key={member.id}>
        <MemberRowAvatar member={member} />
        <div className="member-row__identity">
          <strong>{member.name}</strong>
          <small>{member.email}</small>
          <div className="member-row__controls">
            {canChangeTitle ? (
              <SelectMenu
                ariaLabel={`Cargo de ${member.name}`}
                className="member-row__title-select"
                disabled={savingTitleMemberId !== null}
                onChange={(value) => onTitleChange(member.id, value)}
                options={titleOptions}
                placeholder={isOwner ? 'Sem cargo' : 'Definir cargo'}
                portal
                value={member.title || ''}
              />
            ) : member.title ? (
              <span className="member-row__title">{member.title}</span>
            ) : null}
            {isOwner ? null : (
              <span
                className="member-row__role"
                title={workspaceRoleDescriptions[member.role]}
              >
                {formatWorkspaceRole(member.role)}
              </span>
            )}
          </div>
        </div>
        <div className="member-row__meta">
          {isOwner ? (
            <span
              aria-label={OWNER_LABEL}
              className="member-row__crown"
              role="img"
              title={OWNER_LABEL}
            >
              <CrownIcon />
            </span>
          ) : null}
          <Badge tone={member.status === 'Ativo' ? 'success' : 'warning'}>
            {savingTitleMemberId === member.id ? 'Salvando...' : member.status}
          </Badge>
          {needsTitle && canChangeTitle ? (
            <Badge tone="warning">Definir cargo</Badge>
          ) : null}
          {canRevokeInvite ? (
            <Button
              className="member-row__action"
              disabled={isBusy}
              onClick={() => onInviteRevoke(member.inviteId)}
              size="sm"
              variant="secondary"
            >
              {revokingInviteId === member.inviteId ? 'Revogando...' : 'Revogar'}
            </Button>
          ) : null}
          {canRemoveMember ? (
            <Button
              className="member-row__action"
              disabled={isBusy}
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
  }

  return (
    <div className="members-popover" role="dialog" aria-label="Membros do workspace">
      <div className="members-popover__header">
        <strong>Equipe do workspace</strong>
        <span>{formatMembersCount(activeMembers.length)}</span>
      </div>
      {canManageRoles && onInvite ? (
        <div className="members-popover__invite">
          <Button onClick={onInvite} size="sm" variant="secondary">
            Convidar membro
          </Button>
        </div>
      ) : null}
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
        <CargoLegend />
        {isLoading ? (
          <p className="members-popover__empty">Carregando equipe...</p>
        ) : null}
        {activeMembers.map(renderMemberRow)}
        {pendingInvites.length ? (
          <>
            <div className="members-popover__section">
              <span>Convites pendentes</span>
              <span>{pendingInvites.length}</span>
            </div>
            {pendingInvites.map(renderMemberRow)}
          </>
        ) : null}
        {!isLoading && !members.length && !error ? (
          <p className="members-popover__empty">Nenhum membro encontrado.</p>
        ) : null}
      </div>
    </div>
  )
}

export default MembersPopover
