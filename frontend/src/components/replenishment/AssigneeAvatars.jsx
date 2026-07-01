import { useEffect, useRef, useState } from 'react'
import { getInitials } from '../../lib/formatters'
import AssigneesPopover from './AssigneesPopover'

function AssigneeAvatars({ assignees = [] }) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef(null)
  const visibleAssignees = assignees.slice(0, 3)
  const hiddenCount = Math.max(assignees.length - visibleAssignees.length, 0)

  useEffect(() => {
    if (!isOpen) {
      return undefined
    }

    function handlePointerDown(event) {
      if (!containerRef.current?.contains(event.target)) {
        setIsOpen(false)
      }
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  if (!assignees.length) {
    return <span className="replenishment-assignees-empty">Não atribuído</span>
  }

  return (
    <div className="replenishment-assignees" ref={containerRef}>
      <button
        aria-expanded={isOpen}
        aria-label="Ver responsáveis"
        className={`replenishment-assignee-avatars ${isOpen ? 'is-open' : ''}`}
        onClick={() => setIsOpen((currentValue) => !currentValue)}
        type="button"
      >
        {visibleAssignees.map((assignee) => (
          <span
            className="replenishment-assignee-avatar"
            key={assignee.id}
            title={assignee.name}
          >
            {getInitials(assignee.name)}
          </span>
        ))}
        {hiddenCount > 0 ? (
          <span className="replenishment-assignee-avatar replenishment-assignee-avatar--more">
            +{hiddenCount}
          </span>
        ) : null}
      </button>
      {isOpen ? <AssigneesPopover assignees={assignees} /> : null}
    </div>
  )
}

export default AssigneeAvatars
