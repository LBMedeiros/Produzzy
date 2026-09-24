import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AuthHero from '../components/auth/AuthHero'
import PasswordField from '../components/auth/PasswordField'
import BrandIcon from '../components/ui/BrandIcon'
import Button from '../components/ui/Button'
import { resetPassword } from '../services/authService'

function getFriendlyError(error) {
  if (error?.status === 429) {
    return 'Muitas tentativas. Aguarde alguns minutos e tente novamente.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return (
    error?.message ?? 'Não foi possível redefinir a senha. Tente novamente.'
  )
}

function ResetPasswordPage() {
  const { token } = useParams()
  const navigate = useNavigate()
  const [form, setForm] = useState({ confirmPassword: '', password: '' })
  const [visiblePasswords, setVisiblePasswords] = useState({
    confirmPassword: false,
    password: false,
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDone, setIsDone] = useState(false)
  const [error, setError] = useState('')

  function updateField(field, value) {
    setForm((currentForm) => ({ ...currentForm, [field]: value }))
  }

  function togglePasswordVisibility(field) {
    setVisiblePasswords((currentState) => ({
      ...currentState,
      [field]: !currentState[field],
    }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (form.password !== form.confirmPassword) {
      setError('As senhas precisam ser iguais.')
      return
    }

    setIsSubmitting(true)

    try {
      await resetPassword(token, form.password)
      setIsDone(true)
    } catch (submitError) {
      setError(getFriendlyError(submitError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <div className="login-panel__brand">
          <BrandIcon />
          <strong>Produzzy</strong>
        </div>
        <div className="login-panel__copy">
          <h1>Criar nova senha</h1>
          <p>Escolha uma nova senha para voltar a acessar sua conta.</p>
        </div>

        {isDone ? (
          <div className="auth-feedback" role="status">
            <h2>Senha redefinida!</h2>
            <p>Sua senha foi atualizada. Agora é só entrar com a nova senha.</p>
            <Button
              className="login-form__submit"
              onClick={() => navigate('/login')}
            >
              Ir para o login
            </Button>
          </div>
        ) : (
          <form className="login-form" onSubmit={handleSubmit}>
            <PasswordField
              autoComplete="new-password"
              id="reset-password"
              isVisible={visiblePasswords.password}
              label="Nova senha"
              minLength={8}
              placeholder="Digite a nova senha"
              value={form.password}
              onChange={(event) => updateField('password', event.target.value)}
              onToggle={() => togglePasswordVisibility('password')}
            />
            <PasswordField
              autoComplete="new-password"
              id="reset-confirm-password"
              isVisible={visiblePasswords.confirmPassword}
              label="Confirmar nova senha"
              minLength={8}
              placeholder="Repita a nova senha"
              value={form.confirmPassword}
              onChange={(event) =>
                updateField('confirmPassword', event.target.value)
              }
              onToggle={() => togglePasswordVisibility('confirmPassword')}
            />

            {error ? <p className="form-error">{error}</p> : null}

            <Button
              className="login-form__submit"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? 'Salvando...' : 'Redefinir senha'}
            </Button>
          </form>
        )}

        <p className="login-panel__footer">
          <Link to="/login">Voltar para o login</Link>
        </p>
      </section>

      <AuthHero />
    </main>
  )
}

export default ResetPasswordPage
