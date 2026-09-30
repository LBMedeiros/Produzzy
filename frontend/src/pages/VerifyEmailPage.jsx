import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AuthHero from '../components/auth/AuthHero'
import BrandIcon from '../components/ui/BrandIcon'
import { verifyEmail, verifyRecoveryEmail } from '../services/authService'

function getFriendlyError(error) {
  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  if (error?.status === 429) {
    return 'Muitas tentativas. Aguarde alguns minutos e tente novamente.'
  }

  return error?.message ?? 'Não foi possível confirmar o e-mail.'
}

function VerifyEmailPage({ variant = 'account' }) {
  const { token } = useParams()
  const isRecovery = variant === 'recovery'
  const [status, setStatus] = useState('verifying') // verifying | success | error
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const verify = isRecovery ? verifyRecoveryEmail : verifyEmail

    verify(token)
      .then(() => {
        if (active) {
          setStatus('success')
        }
      })
      .catch((verifyError) => {
        if (!active) {
          return
        }

        setError(getFriendlyError(verifyError))
        setStatus('error')
      })

    return () => {
      active = false
    }
  }, [token, isRecovery])

  return (
    <main className="login-page">
      <section className="login-panel">
        <div className="login-panel__brand">
          <BrandIcon />
          <strong>Produzzy</strong>
        </div>
        <div className="login-panel__copy">
          <h1>
            {isRecovery ? 'E-mail de recuperação' : 'Confirmação de e-mail'}
          </h1>
          <p>
            {isRecovery
              ? 'Confirmação do seu e-mail de backup.'
              : 'Ativação da sua conta Produzzy.'}
          </p>
        </div>

        {status === 'verifying' ? (
          <div className="auth-feedback" role="status">
            <p>Confirmando seu e-mail, um instante...</p>
          </div>
        ) : status === 'success' ? (
          <div className="auth-feedback" role="status">
            <h2>E-mail confirmado! 🎉</h2>
            <p>
              {isRecovery
                ? 'Pronto! Agora ele também recebe o link de redefinição de senha se você perder acesso ao principal.'
                : 'Sua conta foi ativada. Agora é só entrar.'}
            </p>
          </div>
        ) : (
          <div className="auth-feedback" role="status">
            <h2>Não foi possível confirmar</h2>
            <p>{error}</p>
            <p>
              {isRecovery
                ? 'O link pode ter expirado. Cadastre o e-mail de recuperação novamente nas Configurações.'
                : 'O link pode ter expirado. Faça login e use "reenviar confirmação" para receber um novo.'}
            </p>
          </div>
        )}

        <p className="login-panel__footer">
          <Link to="/login">Ir para o login</Link>
        </p>
      </section>

      <AuthHero />
    </main>
  )
}

export default VerifyEmailPage
