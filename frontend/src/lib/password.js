// Password policy for new/changed passwords: 8+ characters, at least one
// number and one special character. Mirrors the backend's
// validate_password_strength so the client shows clear errors before submit.
export function getPasswordError(password) {
  const value = password ?? ''

  if (value.length < 8) {
    return 'A senha deve ter ao menos 8 caracteres.'
  }

  if (!/\d/.test(value)) {
    return 'A senha deve conter ao menos um número.'
  }

  if (!/[^A-Za-z0-9]/.test(value)) {
    return 'A senha deve conter ao menos um caractere especial.'
  }

  return ''
}

export const PASSWORD_HINT =
  'Use ao menos 8 caracteres, com um número e um caractere especial.'
