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

const benefits = [
  {
    description:
      'Cadastre produtos, categorias e acompanhe movimentações em tempo real.',
    icon: 'stock',
    title: 'Estoque organizado',
  },
  {
    description:
      'Identifique o que precisa comprar ou produzir antes de faltar.',
    icon: 'restock',
    title: 'Reposição inteligente',
  },
  {
    description:
      'Gere QR Codes, códigos de barras e etiquetas prontas para impressão.',
    icon: 'labels',
    title: 'Etiquetas prontas',
  },
]

function BenefitIcon({ type }) {
  if (type === 'stock') {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="m4 7 8-4 8 4-8 4-8-4Z" />
        <path d="m4 7 8 4 8-4M4 12l8 4 8-4M4 17l8 4 8-4" />
      </svg>
    )
  }

  if (type === 'restock') {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M20 7v5h-5" />
        <path d="M18.5 16a8 8 0 1 1 .8-8.1L20 12" />
      </svg>
    )
  }

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M4 5a2 2 0 0 1 2-2h8l6 6v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5Z" />
      <path d="M14 3v6h6M8 14h8M8 17h5" />
    </svg>
  )
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
          <p>Use seu email e senha para acessar seus workspaces.</p>
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

      <section className="login-hero" aria-labelledby="login-hero-title">
        <div className="login-hero__content">
          <div className="login-hero__header">
            <span>Gestão simples, do cadastro à reposição</span>
            <h2 id="login-hero-title">
              Estoque, etiquetas e reposição no mesmo fluxo
            </h2>
            <p>
              Controle produtos, acompanhe o baixo estoque, gere QR Codes e
              códigos de barras e saiba quando precisa repor.
            </p>
          </div>

          <div className="login-benefits">
            {benefits.map((benefit) => (
              <article className="login-benefit" key={benefit.title}>
                <span className="login-benefit__icon">
                  <BenefitIcon type={benefit.icon} />
                </span>
                <div>
                  <h3>{benefit.title}</h3>
                  <p>{benefit.description}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  )
}

export default LoginPage
