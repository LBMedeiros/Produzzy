function StatCard({ label, value, trend, tone = 'blue' }) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{trend}</span>
    </article>
  )
}

export default StatCard
