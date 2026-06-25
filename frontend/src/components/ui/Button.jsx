function Button({
  children,
  disabled = false,
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
      disabled={disabled}
      type={type}
      onClick={onClick}
    >
      {icon ? <span className="button__icon">{icon}</span> : null}
      <span>{children}</span>
    </button>
  )
}

export default Button
