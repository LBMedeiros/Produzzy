// Status pill. Tones: neutral, success, warning, danger, replenishment-open,
// plus the redesign tones ok, warn, bad and muted (docs/redesign §3.2).
function Badge({ children, tone = 'neutral' }) {
  return <span className={`badge badge--${tone}`}>{children}</span>
}

export default Badge
