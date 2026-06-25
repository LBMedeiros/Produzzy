import Button from './Button'

function EmptyState({ title, description, actionLabel }) {
  return (
    <div className="empty-state">
      <div className="empty-state__symbol">+</div>
      <h2>{title}</h2>
      <p>{description}</p>
      {actionLabel ? <Button variant="secondary">{actionLabel}</Button> : null}
    </div>
  )
}

export default EmptyState
