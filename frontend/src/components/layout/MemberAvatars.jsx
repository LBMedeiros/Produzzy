function MemberAvatars({ members, onToggle, isOpen }) {
  const visibleMembers = members.slice(0, 3)
  const hiddenCount = Math.max(members.length - visibleMembers.length, 0)

  return (
    <button
      className={`member-avatars ${isOpen ? 'is-open' : ''}`}
      type="button"
      onClick={onToggle}
      aria-expanded={isOpen}
      title="Ver membros do workspace"
    >
      {visibleMembers.map((member) => (
        <span className="member-avatar" key={member.id} title={member.name}>
          {member.initials}
        </span>
      ))}
      {hiddenCount > 0 ? <span className="member-avatar member-avatar--more">+{hiddenCount}</span> : null}
    </button>
  )
}

export default MemberAvatars
