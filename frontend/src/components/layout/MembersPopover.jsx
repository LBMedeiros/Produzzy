import Badge from '../ui/Badge'

function MembersPopover({ members }) {
  return (
    <div className="members-popover" role="dialog" aria-label="Membros do workspace">
      <div className="members-popover__header">
        <strong>Equipe do workspace</strong>
        <span>{members.length} membros</span>
      </div>
      <div className="members-popover__list">
        {members.map((member) => (
          <div className="member-row" key={member.id}>
            <span className="member-avatar">{member.initials}</span>
            <div>
              <strong>{member.name}</strong>
              <small>{member.email}</small>
            </div>
            <div className="member-row__meta">
              <span>{member.role}</span>
              <Badge tone={member.status === 'Ativo' ? 'success' : 'warning'}>
                {member.status}
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default MembersPopover
