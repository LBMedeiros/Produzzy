function MemberAvatars({ members, onToggle, isOpen }) {
  const memberCount = members.length

  return (
    <button
      className={`member-avatars ${isOpen ? 'is-open' : ''}`}
      type="button"
      onClick={onToggle}
      aria-expanded={isOpen}
      aria-label={`Ver membros do workspace (${memberCount})`}
      title="Ver membros do workspace"
    >
      <span className="member-avatars__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          <path d="M16 11a4 4 0 1 0-8 0" />
          <path d="M4.5 19a7.5 7.5 0 0 1 15 0" />
          <path d="M19 9.5a3 3 0 0 1 2.5 3" />
          <path d="M5 9.5a3 3 0 0 0-2.5 3" />
        </svg>
      </span>
      <span className="member-avatars__count">{memberCount}</span>
    </button>
  )
}

export default MemberAvatars
