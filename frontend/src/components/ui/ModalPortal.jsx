import { useEffect } from 'react'
import { createPortal } from 'react-dom'

/**
 * Renders a modal into <body> so it escapes any ancestor that would trap a
 * `position: fixed` element (an ancestor with transform/filter/contain/
 * will-change becomes the containing block, breaking viewport centering and
 * scrolling). Also locks page scroll while open. Wrap the `.modal-backdrop`.
 */
function ModalPortal({ children }) {
  useEffect(() => {
    const scroller = document.querySelector('.app-shell__main')
    const previousBodyOverflow = document.body.style.overflow
    const previousScrollerOverflow = scroller?.style.overflow

    document.body.style.overflow = 'hidden'
    if (scroller) {
      scroller.style.overflow = 'hidden'
    }

    return () => {
      document.body.style.overflow = previousBodyOverflow
      if (scroller) {
        scroller.style.overflow = previousScrollerOverflow ?? ''
      }
    }
  }, [])

  return createPortal(children, document.body)
}

export default ModalPortal
