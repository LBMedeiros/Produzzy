import { useCallback, useEffect } from 'react'

const DROP_DISTANCE = 64 // px an item falls from
const DROP_RANGE = 0.36 // share of the screen height the fall takes
const DELAY_TO_SCROLL = 0.14 // turns a --delay (ms) into a scroll offset (px)
const SCROLL_DURATION = 1200

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function easeOutCubic(t) {
  return 1 - (1 - t) ** 3
}

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2
}

// Login landing motion:
// - items marked [data-reveal] fall into place from above as the page scrolls
//   down and lift back out, in reverse, on the way up (tied to scroll position);
// - the login card eases out as the page scrolls past it;
// - scrollToSection() glides to a section in 1.2s.
// With reduced motion everything stays put and scrolling is instant.
export function useAuthLandingMotion(rootRef) {
  useEffect(() => {
    const root = rootRef.current

    if (!root || prefersReducedMotion()) {
      return undefined
    }

    const card = root.querySelector('[data-hero-card]')
    const hint = root.querySelector('[data-hero-hint]')
    const hero = root.querySelector('[data-hero]')
    const items = Array.from(root.querySelectorAll('[data-reveal]')).map((el) => ({
      el,
      base: 0,
      current: 0,
      offset: (parseFloat(el.style.getPropertyValue('--delay')) || 0) * DELAY_TO_SCROLL,
      rotate: el.dataset.revealRotate ? ` rotate(${el.dataset.revealRotate})` : '',
    }))

    function apply(item) {
      const eased = easeOutCubic(item.current)
      item.el.style.opacity = eased.toFixed(3)
      item.el.style.filter = eased > 0.995 ? '' : `blur(${((1 - eased) * 6).toFixed(2)}px)`
      item.el.style.transform = `translateY(${(-(1 - eased) * DROP_DISTANCE).toFixed(1)}px) scale(${(0.97 + 0.03 * eased).toFixed(4)})${item.rotate}`
    }

    function goal(item) {
      const viewport = window.innerHeight
      const distance = viewport * DROP_RANGE
      const maxScroll = document.documentElement.scrollHeight - viewport
      // Start as the item enters the screen (later for staggered items), but
      // always finish by the bottom of the page.
      const start = Math.max(viewport * 0.98 - item.offset, item.base - maxScroll + distance)
      const top = item.base - window.scrollY

      return Math.min(1, Math.max(0, (start - top) / distance))
    }

    function measure() {
      items.forEach(({ el }) => {
        el.style.transform = ''
        el.style.opacity = ''
        el.style.filter = ''
      })
      items.forEach((item) => {
        item.base = item.el.getBoundingClientRect().top + window.scrollY
      })
      items.forEach(apply)
    }

    function updateHero() {
      if (!card || !hero) {
        return
      }

      const progress = Math.min(1, Math.max(0, window.scrollY / (hero.offsetHeight * 0.8)))
      card.style.opacity = String(1 - progress * 0.85)
      card.style.transform = `translateY(${-progress * 70}px) scale(${1 - progress * 0.05})`

      if (hint) {
        hint.style.opacity = String(Math.max(0, 1 - progress * 2.2))
      }
    }

    let frameId = 0

    function frame() {
      frameId = 0
      let moving = false

      items.forEach((item) => {
        const target = goal(item)
        const diff = target - item.current

        if (Math.abs(diff) > 0.001) {
          item.current += diff * 0.16
          moving = true
        } else {
          item.current = target
        }

        apply(item)
      })
      updateHero()

      if (moving) {
        frameId = window.requestAnimationFrame(frame)
      }
    }

    function kick() {
      if (!frameId) {
        frameId = window.requestAnimationFrame(frame)
      }
    }

    function remeasure() {
      measure()
      kick()
    }

    measure()
    items.forEach((item) => {
      item.current = goal(item)
      apply(item)
    })
    updateHero()

    // Layout shifts (switching login/register, fonts loading) move the items.
    const resizeObserver = new ResizeObserver(remeasure)
    resizeObserver.observe(root)
    window.addEventListener('scroll', kick, { passive: true })
    window.addEventListener('resize', remeasure)

    return () => {
      window.cancelAnimationFrame(frameId)
      resizeObserver.disconnect()
      window.removeEventListener('scroll', kick)
      window.removeEventListener('resize', remeasure)
      items.forEach(({ el }) => {
        el.style.transform = ''
        el.style.opacity = ''
        el.style.filter = ''
      })

      if (card) {
        card.style.opacity = ''
        card.style.transform = ''
      }

      if (hint) {
        hint.style.opacity = ''
      }
    }
  }, [rootRef])

  return useCallback((element) => {
    if (!element) {
      return
    }

    const targetY = element.getBoundingClientRect().top + window.scrollY

    if (prefersReducedMotion()) {
      window.scrollTo(0, targetY)
      return
    }

    const fromY = window.scrollY
    const delta = targetY - fromY
    let startTime = null

    function step(now) {
      if (startTime === null) {
        startTime = now
      }

      const t = Math.min(1, (now - startTime) / SCROLL_DURATION)
      window.scrollTo(0, fromY + delta * easeInOutCubic(t))

      if (t < 1) {
        window.requestAnimationFrame(step)
      }
    }

    window.requestAnimationFrame(step)
  }, [])
}
