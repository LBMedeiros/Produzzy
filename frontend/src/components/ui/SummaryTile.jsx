// Calm summary tile (docs/redesign §3.2): neutral surface, a coloured status
// dot, a big number and one line of context. `tone` (warn | bad | ok) colours
// the dot, and the number too when `highlight` is set.
function SummaryTile({ hint, highlight = false, label, tone, value }) {
  return (
    <div className={`summary-tile${highlight && tone ? ` summary-tile--${tone}` : ''}`}>
      <span className="summary-tile__label">
        <i aria-hidden="true" className={`status-dot${tone ? ` status-dot--${tone}` : ''}`} />
        {label}
      </span>
      <span className="summary-tile__value">{value}</span>
      {hint ? <span className="summary-tile__hint">{hint}</span> : null}
    </div>
  )
}

export default SummaryTile
