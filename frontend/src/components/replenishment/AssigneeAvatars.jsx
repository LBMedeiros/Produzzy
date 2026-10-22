import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { getInitials } from '../../lib/formatters'
import AssigneesPopover from './AssigneesPopover'

function AssigneeAvatars({ assignees = [], isUpdating = false, onRemove }) {
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState(null)
  const containerRef = useRef(null)
  const popoverRef = useRef(null)
  const visibleAssignees = assignees.slice(0, 3)
  const hiddenCount = Math.max(assignees.length - visibleAssignees.length, 0)

  useEffect(() => {
    if (!isOpen) {
      return undefined
    }

    function handlePointerDown(event) {
      if (
        !containerRef.current?.contains(event.target) &&
        !popoverRef.current?.contains(event.target)
      ) {
        setIsOpen(false)
      }
    }

    // The popover is fixed to the viewport, so close it when the page or a
    // board column scrolls instead of leaving it floating.
    function handleScroll(event) {
      if (!popoverRef.current?.contains(event.target)) {
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
    window.addEventListener('scroll', handleScroll, true)
    window.addEventListener('resize', handleScroll)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('scroll', handleScroll, true)
      window.removeEventListener('resize', handleScroll)
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
        onClick={() => {
          if (isOpen) {
            setIsOpen(false)
            return
          }

          // Rendered in <body> (board columns scroll and would clip it).
          const rect = containerRef.current?.getBoundingClientRect()
          const width = Math.min(360, window.innerWidth - 32)

          if (rect) {
            setPosition({
              left: Math.max(16, Math.min(rect.left, window.innerWidth - width - 16)),
              top: rect.bottom + 8,
              width,
            })
          }

          setIsOpen(true)
        }}
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
      {isOpen && position
        ? createPortal(
            <div
              className="replenishment-assignees-portal"
              ref={popoverRef}
              style={position}
            >
              <AssigneesPopover
                assignees={assignees}
                isUpdating={isUpdating}
                onRemove={onRemove}
              />
            </div>,
            document.body,
          )
        : null}
    </div>
  )
}

export default AssigneeAvatars
