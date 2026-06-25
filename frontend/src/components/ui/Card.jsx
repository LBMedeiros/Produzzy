function Card({ children, className = '', title, eyebrow, action }) {
  return (
    <section className={`card ${className}`}>
      {title || eyebrow || action ? (
        <div className="card__header">
          <div>
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            {title ? <h2>{title}</h2> : null}
          </div>
          {action ? <div className="card__action">{action}</div> : null}
        </div>
      ) : null}
      {children}
    </section>
  )
}

export default Card
