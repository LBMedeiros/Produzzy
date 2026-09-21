import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

function SelectMenu({
  ariaLabel,
  className = '',
  disabled = false,
  onChange,
  options,
  portal = false,
  value,
}) {
  const menuId = useId()
  const containerRef = useRef(null)
  const menuRef = useRef(null)
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const [portalPosition, setPortalPosition] = useState(null)
  const selectedIndex = options.findIndex(
    (option) => String(option.value) === String(value),
  )
  const selectedOption = options[selectedIndex] ?? options[0]

  useEffect(() => {
    function handlePointerDown(event) {
      if (
        !containerRef.current?.contains(event.target) &&
        !menuRef.current?.contains(event.target)
      ) {
        setIsOpen(false)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [])

  useEffect(() => {
    if (!isOpen || !portal) return undefined

    function updatePortalPosition() {
      const rect = containerRef.current?.getBoundingClientRect()

      if (rect) {
        setPortalPosition({
          left: rect.left,
          top: rect.bottom + 6,
          width: rect.width,
        })
      }
    }

    updatePortalPosition()
    window.addEventListener('resize', updatePortalPosition)
    window.addEventListener('scroll', updatePortalPosition, true)

    return () => {
      window.removeEventListener('resize', updatePortalPosition)
      window.removeEventListener('scroll', updatePortalPosition, true)
    }
  }, [isOpen, portal])

  function openMenu() {
    if (disabled) return

    if (portal) {
      const rect = containerRef.current?.getBoundingClientRect()

      if (rect) {
        setPortalPosition({
          left: rect.left,
          top: rect.bottom + 6,
          width: rect.width,
        })
      }
    }

    const firstEnabledIndex = options.findIndex((option) => !option.disabled)
    setActiveIndex(
      selectedIndex >= 0 && !options[selectedIndex]?.disabled
        ? selectedIndex
        : Math.max(firstEnabledIndex, 0),
    )
    setIsOpen(true)
  }

  function selectOption(option) {
    if (option.disabled) return

    onChange(String(option.value))
    setIsOpen(false)
  }

  function moveActiveIndex(direction) {
    if (!options.length) return

    let nextIndex = activeIndex

    do {
      nextIndex = (nextIndex + direction + options.length) % options.length
    } while (options[nextIndex]?.disabled && nextIndex !== activeIndex)

    setActiveIndex(nextIndex)
  }

  function handleKeyDown(event) {
    if (event.key === 'Escape') {
      setIsOpen(false)
      return
    }

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()

      if (!isOpen) {
        openMenu()
        return
      }

      moveActiveIndex(event.key === 'ArrowDown' ? 1 : -1)
      return
    }

    if ((event.key === 'Enter' || event.key === ' ') && isOpen) {
      event.preventDefault()
      selectOption(options[activeIndex])
    }
  }

  const menu = isOpen ? (
    <div
      className={`select-menu__menu ${portal ? 'select-menu__menu--portal' : ''}`}
      id={menuId}
      ref={menuRef}
      role="listbox"
      style={
        portal && portalPosition
          ? {
              left: portalPosition.left,
              right: 'auto',
              top: portalPosition.top,
              width: portalPosition.width,
            }
          : undefined
      }
    >
      {options.map((option, index) => (
        <button
          aria-disabled={option.disabled || undefined}
          aria-selected={String(option.value) === String(value)}
          className={`select-menu__option ${
            index === activeIndex ? 'is-active' : ''
          } ${String(option.value) === String(value) ? 'is-selected' : ''}`}
          disabled={option.disabled}
          key={String(option.value)}
          role="option"
          type="button"
          onClick={() => selectOption(option)}
          onMouseEnter={() => {
            if (!option.disabled) setActiveIndex(index)
          }}
        >
          <span>{option.label}</span>
        </button>
      ))}
    </div>
  ) : null

  return (
    <div
      className={`select-menu ${className}`.trim()}
      onKeyDown={handleKeyDown}
      ref={containerRef}
    >
      <button
        aria-controls={menuId}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label={ariaLabel}
        className="select-menu__button"
        disabled={disabled}
        type="button"
        onClick={() => (isOpen ? setIsOpen(false) : openMenu())}
      >
        <span>{selectedOption?.label ?? ''}</span>
        <span className="select-chevron" aria-hidden="true" />
      </button>

      {portal && menu ? createPortal(menu, document.body) : menu}
    </div>
  )
}

export default SelectMenu
