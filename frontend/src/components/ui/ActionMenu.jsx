import { useEffect, useId, useRef, useState } from 'react'

function ActionMenu({ items, label = 'Mais ações', className = '' }) {
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef(null)
  const menuId = useId()
  const visibleItems = items.filter(Boolean)

  useEffect(() => {
    if (!isOpen) {
      return undefined
    }

    function handlePointerDown(event) {
      if (menuRef.current?.contains(event.target)) {
        return
      }

      setIsOpen(false)
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

  function handleItemClick(item) {
    if (item.disabled) {
      return
    }

    setIsOpen(false)
    item.onClick?.()
  }

  return (
    <div
      className={`action-menu ${isOpen ? 'is-open' : ''} ${className}`}
      ref={menuRef}
    >
      <button
        aria-controls={isOpen ? menuId : undefined}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-label={label}
        className="action-menu__trigger"
        type="button"
        onClick={() => setIsOpen((currentValue) => !currentValue)}
      >
        ⋯
      </button>

      {isOpen ? (
        <div className="action-menu__content" id={menuId} role="menu">
          {visibleItems.map((item) => (
            <div className="action-menu__row" key={item.id ?? item.label} role="none">
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
        </div>
      ) : null}
    </div>
  )
}

export default ActionMenu
