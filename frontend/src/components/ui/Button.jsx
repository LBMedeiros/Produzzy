function Button({
  children,
  type = 'button',
  variant = 'primary',
  size = 'md',
  icon,
  onClick,
  className = '',
}) {
  return (
    <button
      className={`button button--${variant} button--${size} ${className}`}
      type={type}
      onClick={onClick}
    >
      {icon ? <span className="button__icon">{icon}</span> : null}
      <span>{children}</span>
    </button>
  )
}

export default Button
