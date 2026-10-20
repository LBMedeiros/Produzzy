// Password policy for new/changed passwords: 8+ characters, at least one
// number and one special character. Mirrors the backend's
// validate_password_strength so the client shows clear errors before submit.
// Each rule also drives the live checklist shown while the user types.
export const PASSWORD_REQUIREMENTS = [
  {
    id: 'length',
    label: 'Ao menos 8 caracteres',
    error: 'A senha deve ter ao menos 8 caracteres.',
    test: (value) => value.length >= 8,
  },
  {
    id: 'number',
    label: 'Um número',
    error: 'A senha deve conter ao menos um número.',
    test: (value) => /\d/.test(value),
  },
  {
    id: 'special',
    label: 'Um caractere especial',
    error: 'A senha deve conter ao menos um caractere especial.',
    test: (value) => /[^A-Za-z0-9]/.test(value),
  },
]

export function getPasswordError(password) {
  const value = password ?? ''
  const failed = PASSWORD_REQUIREMENTS.find((requirement) => !requirement.test(value))

  return failed ? failed.error : ''
}

export const PASSWORD_HINT =
  'Use ao menos 8 caracteres, com um número e um caractere especial.'
