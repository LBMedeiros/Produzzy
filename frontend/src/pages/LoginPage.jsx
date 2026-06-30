import { useState } from 'react'
import BrandIcon from '../components/ui/BrandIcon'
import Button from '../components/ui/Button'
import { useAuth } from '../contexts/AuthContext'

const initialForm = {
  confirmPassword: '',
  email: '',
  name: '',
  password: '',
}

function getFriendlyError(error) {
  if (error?.status === 401) {
    return 'Email ou senha inválidos.'
  }

  if (error?.status === 409) {
    return 'Já existe uma conta com este email.'
  }

  return error?.message ?? 'Não foi possível concluir a ação.'
}

function LoginPage() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState(initialForm)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  const isRegisterMode = mode === 'register'

  function updateField(field, value) {
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      if (isRegisterMode) {
        if (form.password !== form.confirmPassword) {
          throw new Error('As senhas precisam ser iguais.')
        }

        await register({
          email: form.email.trim(),
          name: form.name.trim(),
          password: form.password,
        })
      }

      await login(form.email, form.password)
    } catch (submitError) {
      setError(getFriendlyError(submitError))
    } finally {
      setIsSubmitting(false)
    }
  }

  function toggleMode() {
    setMode((currentMode) => (currentMode === 'login' ? 'register' : 'login'))
    setError('')
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <div className="login-panel__brand">
          <BrandIcon />
          <strong>Produzzy</strong>
        </div>
        <div className="login-panel__copy">
          <h1>{isRegisterMode ? 'Crie sua conta' : 'Entre no Produzzy'}</h1>
          <p>
            Use seu email e senha para acessar seus workspaces reais. O estoque
            e a produção continuam mockados nesta fase.
          </p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {isRegisterMode ? (
            <label>
              Nome
              <input
                autoComplete="name"
                onChange={(event) => updateField('name', event.target.value)}
                placeholder="Lucas Medeiros"
                required
                type="text"
                value={form.name}
              />
            </label>
          ) : null}

          <label>
            Email
            <input
              autoComplete="email"
              onChange={(event) => updateField('email', event.target.value)}
              placeholder="lucas@empresa.com"
              required
              type="email"
              value={form.email}
            />
          </label>
          <label>
            Senha
            <input
              autoComplete={isRegisterMode ? 'new-password' : 'current-password'}
              minLength={isRegisterMode ? 8 : 1}
              onChange={(event) => updateField('password', event.target.value)}
              placeholder="Digite sua senha"
              required
              type="password"
              value={form.password}
            />
          </label>

          {isRegisterMode ? (
            <label>
              Confirmar senha
              <input
                autoComplete="new-password"
                minLength="8"
                onChange={(event) =>
                  updateField('confirmPassword', event.target.value)
                }
                placeholder="Repita sua senha"
                required
                type="password"
                value={form.confirmPassword}
              />
            </label>
          ) : null}

          {error ? <p className="form-error">{error}</p> : null}

          <Button
            className="login-form__submit"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting
              ? 'Aguarde...'
              : isRegisterMode
                ? 'Criar conta'
                : 'Entrar'}
          </Button>
        </form>

        <p className="login-panel__footer">
          {isRegisterMode ? 'Já tem uma conta?' : 'Novo por aqui?'}{' '}
          <button type="button" onClick={toggleMode}>
            {isRegisterMode ? 'Entrar agora' : 'Criar conta'}
          </button>
        </p>
      </section>

      <section className="login-hero" aria-label="Resumo visual do produto">
        <div className="login-hero__header">
          <span>Workspaces conectados</span>
          <strong>Estoque, produção e etiquetas no mesmo fluxo</strong>
        </div>
        <div className="hero-metric hero-metric--wide">
          <span>Autenticação real</span>
          <strong>JWT</strong>
        </div>
        <div className="hero-metric">
          <span>Workspaces</span>
          <strong>Reais</strong>
        </div>
        <div className="hero-metric">
          <span>Dados internos</span>
          <strong>Mock</strong>
        </div>
        <div className="label-preview">
          <div className="qr-grid"></div>
          <div>
            <strong>Camiseta premium</strong>
            <span>ID 1024</span>
          </div>
        </div>
      </section>
    </main>
  )
}

export default LoginPage
