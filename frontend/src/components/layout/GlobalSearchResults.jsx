/**
 * Renders the global-search result states (loading / error / empty / grouped
 * results). Shared between the desktop dropdown panel and the mobile full-screen
 * search overlay so both stay in sync.
 */
function GlobalSearchResults({
  activeId,
  error,
  flatResults,
  groups,
  isLoading,
  onHover,
  onSelect,
}) {
  if (isLoading) {
    return (
      <p className="global-search__state" role="status">
        Buscando...
      </p>
    )
  }

  if (error) {
    return (
      <p className="global-search__state global-search__state--error">{error}</p>
    )
  }

  if (!flatResults.length) {
    return (
      <p className="global-search__state">Nenhum resultado encontrado.</p>
    )
  }

  return groups.map((group) => (
    <div className="global-search__group" key={group.name}>
      <span>{group.name}</span>
      {group.items.map((item) => (
        <button
          aria-selected={activeId === item.id}
          className={activeId === item.id ? 'is-active' : ''}
          id={item.id}
          key={item.id}
          role="option"
          type="button"
          onClick={() => onSelect(item)}
          onMouseEnter={() => onHover(item)}
        >
          <strong>{item.label}</strong>
          <small>{item.description}</small>
        </button>
      ))}
    </div>
  ))
}

export default GlobalSearchResults
