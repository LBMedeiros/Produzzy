import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from 'react'
import { createPortal } from 'react-dom'

const MENU_GAP = 8
const VIEWPORT_MARGIN = 12

function clamp(value, min, max) {
  if (max < min) {
    return min
  }

  return Math.min(Math.max(value, min), max)
}

function ActionMenu({ items, label = 'Mais ações', className = '' }) {
  const [isOpen, setIsOpen] = useState(false)
  const [menuPosition, setMenuPosition] = useState(null)
  const triggerRef = useRef(null)
  const contentRef = useRef(null)
  const menuId = useId()
  const visibleItems = items.filter(Boolean)

  const closeMenu = useCallback(() => {
    setIsOpen(false)
    setMenuPosition(null)
  }, [])

  const openMenu = useCallback(() => {
    setMenuPosition(null)
    setIsOpen(true)
  }, [])

  const updateMenuPosition = useCallback(() => {
    const trigger = triggerRef.current
    const content = contentRef.current

    if (!trigger || !content) {
      return
    }

    const triggerRect = trigger.getBoundingClientRect()
    const contentRect = content.getBoundingClientRect()
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight
    const maxHeight = Math.max(viewportHeight - VIEWPORT_MARGIN * 2, 120)
    const menuWidth = contentRect.width
    const menuHeight = Math.min(contentRect.height, maxHeight)
    const spaceBelow = viewportHeight - triggerRect.bottom - MENU_GAP - VIEWPORT_MARGIN
    const spaceAbove = triggerRect.top - MENU_GAP - VIEWPORT_MARGIN
    const shouldOpenUp = spaceBelow < menuHeight && spaceAbove > spaceBelow
    const preferredLeft = triggerRect.right - menuWidth
    const left = clamp(
      preferredLeft,
      VIEWPORT_MARGIN,
      viewportWidth - menuWidth - VIEWPORT_MARGIN,
    )
    const preferredTop = shouldOpenUp
      ? triggerRect.top - MENU_GAP - menuHeight
      : triggerRect.bottom + MENU_GAP
    const top = clamp(
      preferredTop,
      VIEWPORT_MARGIN,
      viewportHeight - menuHeight - VIEWPORT_MARGIN,
    )

    setMenuPosition({
      left,
      maxHeight,
      top,
    })
  }, [])

  useEffect(() => {
    if (!isOpen) {
      return undefined
    }

    function handlePointerDown(event) {
      if (
        triggerRef.current?.contains(event.target) ||
        contentRef.current?.contains(event.target)
      ) {
        return
      }

      closeMenu()
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        closeMenu()
      }
    }

    function handleViewportChange() {
      window.requestAnimationFrame(updateMenuPosition)
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    window.addEventListener('resize', handleViewportChange)
    window.addEventListener('scroll', handleViewportChange, true)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('resize', handleViewportChange)
      window.removeEventListener('scroll', handleViewportChange, true)
    }
  }, [closeMenu, isOpen, updateMenuPosition])

  useEffect(() => {
    if (!isOpen) {
      return undefined
    }

    const frameId = window.requestAnimationFrame(updateMenuPosition)

    return () => window.cancelAnimationFrame(frameId)
  }, [isOpen, updateMenuPosition, visibleItems.length])

  function handleItemClick(item) {
    if (item.disabled) {
      return
    }

    closeMenu()
    item.onClick?.()
  }

  const menuContent =
    isOpen && typeof document !== 'undefined'
      ? createPortal(
          <div
            className="action-menu__content"
            id={menuId}
            ref={contentRef}
            role="menu"
            style={{
              left: menuPosition?.left ?? 0,
              maxHeight: menuPosition?.maxHeight,
              top: menuPosition?.top ?? 0,
              visibility: menuPosition ? 'visible' : 'hidden',
            }}
          >
            {visibleItems.map((item) => (
              <div
                className="action-menu__row"
                key={item.id ?? item.label}
                role="none"
              >
                {item.separatorBefore ? (
                  <span className="action-menu__separator" aria-hidden="true" />
                ) : null}
                <button
                  className={item.destructive ? 'action-menu__item--danger' : ''}
                  disabled={item.disabled}
                  role="menuitem"
                  type="button"
                  onClick={() => handleItemClick(item)}
                >
                  <span>{item.label}</span>
                </button>
              </div>
            ))}
          </div>,
          document.body,
        )
      : null

  return (
    <div
      className={`action-menu ${isOpen ? 'is-open' : ''} ${className}`}
    >
      <button
        aria-controls={isOpen ? menuId : undefined}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-label={label}
        className="action-menu__trigger"
        ref={triggerRef}
        type="button"
        onClick={() => {
          if (isOpen) {
            closeMenu()
          } else {
            openMenu()
          }
        }}
      >
        ⋯
      </button>

      {menuContent}
    </div>
  )
}

export default ActionMenu
