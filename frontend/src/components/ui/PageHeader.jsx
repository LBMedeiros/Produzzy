// Page title + subtitle, with an optional actions area on the right.
// Renders the existing `.page-heading` markup, so pages can adopt it without
// any visual change.
function PageHeader({ actions, subtitle, title }) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {actions ? <div className="page-heading__actions">{actions}</div> : null}
    </div>
  )
}

export default PageHeader
