function StatCard({ label, value, trend, tone = 'blue' }) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__marker"></div>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{trend}</span>
    </article>
  )
}

export default StatCard
