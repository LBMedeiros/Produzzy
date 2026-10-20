import { PASSWORD_REQUIREMENTS } from '../../lib/password'

function RequirementIcon({ isMet }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      {isMet ? <path d="m5 12.5 4.5 4.5L19 7.5" /> : <path d="M7 7l10 10M17 7 7 17" />}
    </svg>
  )
}

// Live checklist under the sign-up password: each rule turns from red to
// green as soon as the typed password satisfies it.
function PasswordRequirements({ password }) {
  const value = password ?? ''

  return (
    <ul aria-label="Requisitos da senha" className="password-requirements">
      {PASSWORD_REQUIREMENTS.map((requirement) => {
        const isMet = requirement.test(value)

        return (
          <li
            className={`password-requirements__item ${isMet ? 'is-met' : ''}`}
            key={requirement.id}
          >
            <span className="password-requirements__icon">
              <RequirementIcon isMet={isMet} />
            </span>
            {requirement.label}
            <span className="password-requirements__status">
              {isMet ? ' (atendido)' : ' (pendente)'}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

export default PasswordRequirements
