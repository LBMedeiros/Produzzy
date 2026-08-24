import { useState } from 'react'
import BrandIcon from '../components/ui/BrandIcon'
import Button from '../components/ui/Button'
import { useAuth } from '../contexts/AuthContext'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ''
const GOOGLE_SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

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

let googleScriptPromise = null

function loadGoogleIdentityScript() {
  if (window.google?.accounts?.oauth2) {
    return Promise.resolve()
  }

  if (googleScriptPromise) {
    return googleScriptPromise
  }

  googleScriptPromise = new Promise((resolve, reject) => {
    const existingScript = document.querySelector(
      `script[src="${GOOGLE_SCRIPT_SRC}"]`,
    )

    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(), { once: true })
      existingScript.addEventListener(
        'error',
        () => reject(new Error('Não foi possível carregar o Google.')),
        { once: true },
      )
      return
    }

    const script = document.createElement('script')
    script.async = true
    script.defer = true
    script.src = GOOGLE_SCRIPT_SRC
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Não foi possível carregar o Google.'))

    document.head.appendChild(script)
  })

  return googleScriptPromise
}

function GoogleIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path
        d="M21.6 12.23c0-.78-.07-1.53-.2-2.23H12v4.22h5.38a4.6 4.6 0 0 1-2 3.02v2.51h3.24c1.9-1.75 2.98-4.32 2.98-7.52Z"
        fill="#4285F4"
      />
      <path
        d="M12 22c2.7 0 4.97-.9 6.62-2.45l-3.24-2.51c-.9.6-2.05.96-3.38.96-2.6 0-4.8-1.76-5.59-4.12H3.07v2.59A10 10 0 0 0 12 22Z"
        fill="#34A853"
      />
      <path
        d="M6.41 13.88A6 6 0 0 1 6.1 12c0-.65.11-1.28.31-1.88V7.53H3.07A10 10 0 0 0 2 12c0 1.61.39 3.14 1.07 4.47l3.34-2.59Z"
        fill="#FBBC05"
      />
      <path
        d="M12 6c1.47 0 2.79.51 3.83 1.5l2.87-2.87A9.62 9.62 0 0 0 12 2a10 10 0 0 0-8.93 5.53l3.34 2.59C7.2 7.76 9.4 6 12 6Z"
        fill="#EA4335"
      />
    </svg>
  )
}

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
    return error?.message ?? 'Já existe uma conta com este email.'
  }

  return error?.message ?? 'Não foi possível concluir a ação.'
}

function getGooglePopupError(error) {
  if (error?.type === 'popup_closed') {
    return 'Login com Google cancelado.'
  }

  if (error?.type === 'popup_failed_to_open') {
    return 'Não foi possível abrir o Google. Verifique o bloqueador de pop-up.'
  }

  return 'Não foi possível continuar com Google.'
}

function getGoogleResponseError(error) {
  if (error === 'access_denied') {
    return 'Login com Google cancelado.'
  }

  return 'Não foi possível continuar com Google.'
}

function LoginPage() {
  const { login, loginWithGoogle, register } = useAuth()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState(initialForm)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false)
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

  async function handleGoogleLogin() {
    setError('')
    setIsGoogleSubmitting(true)

    try {
      if (!GOOGLE_CLIENT_ID) {
        throw new Error('Login com Google ainda não configurado.')
      }

      await loadGoogleIdentityScript()

      if (!window.google?.accounts?.oauth2) {
        throw new Error('Não foi possível carregar o Google.')
      }

      await new Promise((resolve, reject) => {
        let settled = false

        function finish(callback, value) {
          if (settled) {
            return
          }

          settled = true
          callback(value)
        }

        const client = window.google.accounts.oauth2.initCodeClient({
          callback: async (response) => {
            if (response.error) {
              finish(reject, new Error(getGoogleResponseError(response.error)))
              return
            }

            if (!response.code) {
              finish(
                reject,
                new Error('Não foi possível obter autorização do Google.'),
              )
              return
            }

            try {
              await loginWithGoogle(response.code, window.location.origin)
              finish(resolve)
            } catch (googleError) {
              finish(reject, googleError)
            }
          },
          client_id: GOOGLE_CLIENT_ID,
          error_callback: (googleError) => {
            finish(reject, new Error(getGooglePopupError(googleError)))
          },
          include_granted_scopes: false,
          scope: 'openid email profile',
          ux_mode: 'popup',
        })

        client.requestCode()
      })
    } catch (googleError) {
      setError(getFriendlyError(googleError))
    } finally {
      setIsGoogleSubmitting(false)
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
          <p>Use Google ou seu email e senha para acessar seus workspaces.</p>
        </div>

        <div className="login-social">
          <button
            aria-label="Continuar com Google"
            className="google-auth-button"
            disabled={isSubmitting || isGoogleSubmitting}
            onClick={handleGoogleLogin}
            type="button"
          >
            <span className="google-auth-button__icon">
              <GoogleIcon />
            </span>
            <span>
              {isGoogleSubmitting ? 'Conectando...' : 'Continuar com Google'}
            </span>
          </button>
        </div>

        <div className="login-divider" role="separator">
          <span>ou continue com email</span>
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
            disabled={isSubmitting || isGoogleSubmitting}
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
