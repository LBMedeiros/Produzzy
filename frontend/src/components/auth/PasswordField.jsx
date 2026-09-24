function PasswordVisibilityIcon({ isVisible }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M2.5 12s3.6-6.5 9.5-6.5S21.5 12 21.5 12 17.9 18.5 12 18.5 2.5 12 2.5 12Z" />
      <path d="M12 9.25a2.75 2.75 0 1 1 0 5.5 2.75 2.75 0 0 1 0-5.5Z" />
      {isVisible ? <path d="M4.5 4.5 19.5 19.5" /> : null}
    </svg>
  )
}

function PasswordField({
  autoComplete,
  id,
  isVisible,
  label,
  minLength,
  onChange,
  onToggle,
  placeholder,
  value,
}) {
  const visibilityLabel = isVisible ? 'Ocultar senha' : 'Mostrar senha'

  return (
    <div className="login-field">
      <label htmlFor={id}>{label}</label>
      <span className="login-password-field">
        <input
          autoComplete={autoComplete}
          id={id}
          minLength={minLength}
          onChange={onChange}
          placeholder={placeholder}
          required
          type={isVisible ? 'text' : 'password'}
          value={value}
        />
        <button
          aria-label={visibilityLabel}
          aria-pressed={isVisible}
          className="login-password-field__toggle"
          type="button"
          onClick={onToggle}
        >
          <PasswordVisibilityIcon isVisible={isVisible} />
        </button>
      </span>
    </div>
  )
}

export default PasswordField
