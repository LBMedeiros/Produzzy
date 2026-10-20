import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import LoginShowcase from '../components/auth/LoginShowcase'
import PasswordField from '../components/auth/PasswordField'
import BrandIcon from '../components/ui/BrandIcon'
import Button from '../components/ui/Button'
import { useAuth } from '../contexts/AuthContext'
import { getPasswordError, PASSWORD_HINT } from '../lib/password'
import { useAuthLandingMotion } from '../lib/useAuthLandingMotion'
import { resendVerification } from '../services/authService'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ''
const GOOGLE_SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

const initialForm = {
  confirmPassword: '',
  email: '',
  name: '',
  password: '',
}

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

function getFriendlyError(error) {
  if (error?.status === 401) {
    return 'E-mail ou senha inválidos.'
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

// Diferente do login por senha: aqui NÃO mapeamos 401 para "e-mail ou senha
// inválidos". Mostramos o detalhe real vindo do backend (ex.: "Credencial do
// Google inválida.", "Origem do login com Google não permitida.") para ajudar
// no diagnóstico.
function getGoogleLoginError(error) {
  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  if (typeof error?.status === 'number' && error.status > 0) {
    return error?.message ?? 'Não foi possível continuar com Google.'
  }

  return error?.message ?? 'Não foi possível continuar com Google.'
}

function LoginPage() {
  const { login, loginWithGoogle, register } = useAuth()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState(initialForm)
  const [visiblePasswords, setVisiblePasswords] = useState({
    confirmPassword: false,
    password: false,
  })
  const [rememberMe, setRememberMe] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false)
  const [error, setError] = useState('')
  // When set, the account exists but the e-mail is not confirmed yet.
  // { email, context: 'register' | 'login' }
  const [verificationNotice, setVerificationNotice] = useState(null)
  const [resendState, setResendState] = useState('idle')

  const isRegisterMode = mode === 'register'
  const landingRef = useRef(null)
  const showcaseRef = useRef(null)
  const scrollToSection = useAuthLandingMotion(landingRef)

  function updateField(field, value) {
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }))
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
    setVerificationNotice(null)
    setIsSubmitting(true)

    try {
      if (isRegisterMode) {
        const passwordError = getPasswordError(form.password)

        if (passwordError) {
          throw new Error(passwordError)
        }

        if (form.password !== form.confirmPassword) {
          throw new Error('As senhas precisam ser iguais.')
        }

        await register({
          email: form.email.trim(),
          name: form.name.trim(),
          password: form.password,
        })

        // The account is active right away — log the user straight in.
        await login(form.email.trim(), form.password, { rememberMe })
        return
      }

      await login(form.email, form.password, { rememberMe })
    } catch (submitError) {
      if (submitError?.status === 403) {
        // Credentials are valid, but the e-mail isn't confirmed yet.
        setResendState('idle')
        setVerificationNotice({ context: 'login', email: form.email.trim() })
      } else {
        setError(getFriendlyError(submitError))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleResendVerification() {
    if (!verificationNotice?.email) {
      return
    }

    setResendState('sending')

    try {
      await resendVerification(verificationNotice.email)
      setResendState('sent')
    } catch {
      setResendState('error')
    }
  }

  function backToLogin() {
    setVerificationNotice(null)
    setResendState('idle')
    setError('')
    setMode('login')
  }

  async function handleGoogleLogin() {
    setError('')
    setVerificationNotice(null)
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
              await loginWithGoogle(response.code, window.location.origin, {
                rememberMe: !isRegisterMode && rememberMe,
              })
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
      setError(getGoogleLoginError(googleError))
    } finally {
      setIsGoogleSubmitting(false)
    }
  }

  function openRegister() {
    if (!isRegisterMode) {
      toggleMode()
    }

    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function toggleMode() {
    setMode((currentMode) => (currentMode === 'login' ? 'register' : 'login'))
    setVisiblePasswords({
      confirmPassword: false,
      password: false,
    })
    setError('')
    setVerificationNotice(null)
    setResendState('idle')
  }

  const title = verificationNotice
    ? 'Confirme seu e-mail'
    : isRegisterMode
      ? 'Crie sua conta'
      : 'Bem-vindo de volta'
  const subtitle = verificationNotice
    ? 'Falta um passo: confirme seu e-mail para acessar sua conta.'
    : isRegisterMode
      ? 'Comece a organizar seu estoque em poucos minutos.'
      : 'Entre para acessar seus workspaces.'

  return (
    <main className="auth-landing" ref={landingRef}>
      <section className="auth-hero" data-hero>
        <div className="auth-card" data-hero-card>
          <div className="auth-card__brand">
            <BrandIcon />
            <strong>Produzzy</strong>
          </div>
          <div className="auth-card__copy">
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>

          {verificationNotice ? (
            <>
              <div className="auth-feedback" role="status">
                <h2>
                  {verificationNotice.context === 'register'
                    ? 'Conta criada! Confirme seu e-mail'
                    : 'Confirmação pendente'}
                </h2>
                <p>
                  Enviamos um link de confirmação para{' '}
                  <strong>{verificationNotice.email}</strong>. Abra o e-mail e
                  clique no link para ativar o acesso. Confira também o spam.
                </p>
                {resendState === 'sent' ? (
                  <p className="form-success">
                    Reenviamos o link. Verifique seu e-mail.
                  </p>
                ) : null}
                {resendState === 'error' ? (
                  <p className="form-error">
                    Não foi possível reenviar agora. Tente novamente em instantes.
                  </p>
                ) : null}
                <Button
                  className="auth-form__submit"
                  variant="secondary"
                  disabled={resendState === 'sending'}
                  onClick={handleResendVerification}
                >
                  {resendState === 'sending'
                    ? 'Reenviando...'
                    : 'Reenviar e-mail de confirmação'}
                </Button>
              </div>
              <p className="auth-card__switch">
                <button type="button" onClick={backToLogin}>
                  Voltar para o login
                </button>
              </p>
            </>
          ) : (
            <>
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

              <div className="auth-divider" role="separator">
                <span>ou com e-mail</span>
              </div>

              <form className="login-form auth-form" onSubmit={handleSubmit}>
                {isRegisterMode ? (
                  <label>
                    Nome
                    <input
                      autoComplete="name"
                      onChange={(event) => updateField('name', event.target.value)}
                      placeholder="Seu nome"
                      required
                      type="text"
                      value={form.name}
                    />
                  </label>
                ) : null}

                <label>
                  E-mail
                  <input
                    autoComplete="email"
                    onChange={(event) => updateField('email', event.target.value)}
                    placeholder="voce@empresa.com"
                    required
                    type="email"
                    value={form.email}
                  />
                </label>
                <PasswordField
                  action={
                    !isRegisterMode ? (
                      <Link className="auth-link" to="/forgot-password">
                        Esqueceu a senha?
                      </Link>
                    ) : null
                  }
                  autoComplete={isRegisterMode ? 'new-password' : 'current-password'}
                  id="login-password"
                  isVisible={visiblePasswords.password}
                  label="Senha"
                  minLength={isRegisterMode ? 8 : 1}
                  placeholder={isRegisterMode ? 'Crie uma senha' : 'Sua senha'}
                  value={form.password}
                  onChange={(event) => updateField('password', event.target.value)}
                  onToggle={() => togglePasswordVisibility('password')}
                />

                {isRegisterMode ? <p className="login-hint">{PASSWORD_HINT}</p> : null}

                {isRegisterMode ? (
                  <PasswordField
                    autoComplete="new-password"
                    id="login-confirm-password"
                    isVisible={visiblePasswords.confirmPassword}
                    label="Confirmar senha"
                    minLength="8"
                    placeholder="Repita a senha"
                    value={form.confirmPassword}
                    onChange={(event) =>
                      updateField('confirmPassword', event.target.value)
                    }
                    onToggle={() => togglePasswordVisibility('confirmPassword')}
                  />
                ) : null}

                {!isRegisterMode ? (
                  <label className="login-remember">
                    <input
                      checked={rememberMe}
                      type="checkbox"
                      onChange={(event) => setRememberMe(event.target.checked)}
                    />
                    <span className="login-remember__box" aria-hidden="true"></span>
                    <span>Lembrar de mim por 30 dias</span>
                  </label>
                ) : null}

                {error ? <p className="form-error">{error}</p> : null}

                <Button
                  className="auth-form__submit"
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

              <p className="auth-card__switch">
                {isRegisterMode ? 'Já tem uma conta?' : 'Novo por aqui?'}{' '}
                <button type="button" onClick={toggleMode}>
                  {isRegisterMode ? 'Entrar' : 'Criar conta'}
                </button>
              </p>
            </>
          )}

          <p className="auth-card__legal">
            Ao continuar, você concorda com os{' '}
            <Link to="/termos">Termos de Uso</Link> e a{' '}
            <Link to="/privacidade">Política de Privacidade</Link>.
          </p>
        </div>

        <button
          className="auth-more"
          data-hero-hint
          onClick={() => scrollToSection(showcaseRef.current)}
          type="button"
        >
          Conheça o Produzzy
          <span aria-hidden="true">↓</span>
        </button>
      </section>

      <LoginShowcase onCreateAccount={openRegister} sectionRef={showcaseRef} />
    </main>
  )
}

export default LoginPage
