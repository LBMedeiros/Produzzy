import { useEffect, useId, useRef, useState } from 'react'

function SelectMenu({
  ariaLabel,
  className = '',
  disabled = false,
  onChange,
  options,
  value,
}) {
  const menuId = useId()
  const containerRef = useRef(null)
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const selectedIndex = options.findIndex(
    (option) => String(option.value) === String(value),
  )
  const selectedOption = options[selectedIndex] ?? options[0]

  useEffect(() => {
    function handlePointerDown(event) {
      if (!containerRef.current?.contains(event.target)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [])

  function openMenu() {
    if (disabled) return

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

      {isOpen ? (
        <div className="select-menu__menu" id={menuId} role="listbox">
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
      ) : null}
    </div>
  )
}

export default SelectMenu
