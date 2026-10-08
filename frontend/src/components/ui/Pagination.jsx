// Always the first and last page plus the current one and its neighbours, so
// the row stays short enough for a phone: ‹ 1 … 4 5 6 … 12 ›
function getPageItems(page, totalPages) {
  if (totalPages <= 5) {
    return Array.from({ length: totalPages }, (_, index) => index + 1)
  }

  const sorted = [...new Set([1, page - 1, page, page + 1, totalPages])]
    .filter((value) => value >= 1 && value <= totalPages)
    .sort((a, b) => a - b)
  const result = []

  sorted.forEach((value, index) => {
    const gap = index > 0 ? value - sorted[index - 1] : 0

    if (gap === 2) {
      result.push(value - 1)
    } else if (gap > 2) {
      result.push(`gap-${value}`)
    }

    result.push(value)
  })

  return result
}

function Pagination({ itemLabel = 'itens', onPageChange, page, pageSize, totalItems }) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))

  if (totalItems <= pageSize) {
    return null
  }

  const firstItem = (page - 1) * pageSize + 1
  const lastItem = Math.min(page * pageSize, totalItems)
  const formatter = new Intl.NumberFormat('pt-BR')

  return (
    <nav aria-label="Paginação" className="pagination">
      <p className="pagination__summary">
        {formatter.format(firstItem)}–{formatter.format(lastItem)} de{' '}
        {formatter.format(totalItems)} {itemLabel}
      </p>

      <div className="pagination__controls">
        <button
          aria-label="Página anterior"
          className="pagination__button pagination__button--step"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          type="button"
        >
          ‹
        </button>

        {getPageItems(page, totalPages).map((item) =>
          typeof item === 'string' ? (
            <span aria-hidden="true" className="pagination__gap" key={item}>
              …
            </span>
          ) : (
            <button
              aria-current={item === page ? 'page' : undefined}
              aria-label={`Página ${item}`}
              className={`pagination__button${item === page ? ' is-active' : ''}`}
              key={item}
              onClick={() => onPageChange(item)}
              type="button"
            >
              {item}
            </button>
          ),
        )}

        <button
          aria-label="Próxima página"
          className="pagination__button pagination__button--step"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          type="button"
        >
          ›
        </button>
      </div>
    </nav>
  )
}

export default Pagination
