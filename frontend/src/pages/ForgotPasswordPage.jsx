import { useState } from 'react'
import { Link } from 'react-router-dom'
import AuthHero from '../components/auth/AuthHero'
import BrandIcon from '../components/ui/BrandIcon'
import Button from '../components/ui/Button'
import { requestPasswordReset } from '../services/authService'

function getFriendlyError(error) {
  if (error?.status === 429) {
    return 'Muitas tentativas. Aguarde alguns minutos e tente novamente.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível enviar o link. Tente novamente.'
}

function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSent, setIsSent] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      await requestPasswordReset(email)
      setIsSent(true)
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
          <h1>Recuperar acesso</h1>
          <p>
            Informe o e-mail da sua conta e enviaremos um link para você criar
            uma nova senha.
          </p>
        </div>

        {isSent ? (
          <div className="auth-feedback" role="status">
            <h2>Verifique seu e-mail</h2>
            <p>
              Se existir uma conta com esse e-mail, você vai receber um link
              para redefinir a senha em instantes. Confira também a caixa de
              spam.
            </p>
          </div>
        ) : (
          <form className="login-form" onSubmit={handleSubmit}>
            <label>
              Email
              <input
                autoComplete="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="Digite seu email"
                required
                type="email"
                value={email}
              />
            </label>

            {error ? <p className="form-error">{error}</p> : null}

            <Button
              className="login-form__submit"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? 'Enviando...' : 'Enviar link de redefinição'}
            </Button>
          </form>
        )}

        <p className="login-panel__footer">
          Lembrou a senha? <Link to="/login">Voltar para o login</Link>
        </p>
      </section>

      <AuthHero />
    </main>
  )
}

export default ForgotPasswordPage
