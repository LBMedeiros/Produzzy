import { useCallback, useState } from 'react'

// The API caps `limit` at 100 per request, so lists that the UI filters and
// searches client-side must walk every page or items past the 100th vanish.
export const API_PAGE_SIZE = 100
const MAX_API_PAGES = 100

export async function fetchAllPages(fetchPage) {
  const items = []
  const seenIds = new Set()

  for (let page = 1; page <= MAX_API_PAGES; page += 1) {
    const pageItems = await fetchPage({ limit: API_PAGE_SIZE, page })

    pageItems.forEach((item) => {
      // A row can shift between pages if something changes mid-walk.
      if (item?.id === undefined || !seenIds.has(item.id)) {
        seenIds.add(item?.id)
        items.push(item)
      }
    })

    if (pageItems.length < API_PAGE_SIZE) {
      break
    }
  }

  return items
}

function scrollToElement(element) {
  const prefersReducedMotion = window.matchMedia(
    '(prefers-reduced-motion: reduce)',
  ).matches

  element?.scrollIntoView({
    behavior: prefersReducedMotion ? 'auto' : 'smooth',
    block: 'start',
  })
}

// Client-side pagination over an already-loaded list. `resetKey` sends the
// view back to page 1 whenever the filters behind `items` change; `listRef`
// is scrolled into view when the user changes page.
export function usePagination(items, pageSize, resetKey, listRef) {
  const [state, setState] = useState({ key: resetKey, page: 1 })
  const totalItems = items.length
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const requestedPage = state.key === resetKey ? state.page : 1
  const page = Math.min(Math.max(requestedPage, 1), totalPages)
  const start = (page - 1) * pageSize
  const pageItems = items.slice(start, start + pageSize)

  const setPage = useCallback(
    (nextPage, options = {}) => {
      setState({ key: resetKey, page: nextPage })

      if (options.scroll === false) {
        return
      }

      window.requestAnimationFrame(() => scrollToElement(listRef.current))
    },
    [listRef, resetKey],
  )

  const goToItem = useCallback(
    (predicate) => {
      const index = items.findIndex(predicate)

      if (index >= 0) {
        setPage(Math.floor(index / pageSize) + 1, { scroll: false })
      }
    },
    [items, pageSize, setPage],
  )

  return {
    goToItem,
    page,
    pageItems,
    pageSize,
    setPage,
    totalItems,
    totalPages,
  }
}
