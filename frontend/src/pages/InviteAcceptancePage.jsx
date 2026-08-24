import { useCallback, useEffect, useState } from 'react'
import BrandIcon from '../components/ui/BrandIcon'
import Button from '../components/ui/Button'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { acceptWorkspaceInvite } from '../services/workspaceService'

function getInviteError(error) {
  if (error?.status === 403) {
    return 'Este convite pertence a outro e-mail.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível aceitar o convite.'
}

function InviteAcceptancePage({ onDone, token }) {
  const { loadWorkspaces, selectWorkspace } = useWorkspace()
  const [status, setStatus] = useState('loading')
  const [message, setMessage] = useState('Aceitando convite...')

  const acceptInvite = useCallback(async () => {
    if (!token) {
      setStatus('error')
      setMessage('Convite inválido.')
      return
    }

    setStatus('loading')
    setMessage('Aceitando convite...')

    try {
      const membership = await acceptWorkspaceInvite(token)
      const workspaces = await loadWorkspaces()
      const acceptedWorkspace = workspaces.find(
        (workspace) => workspace.id === membership.workspace_id,
      )

      if (acceptedWorkspace) {
        selectWorkspace(acceptedWorkspace)
      }

      window.history.replaceState(window.history.state, '', '/')
      setStatus('success')
      setMessage('Convite aceito. O workspace foi adicionado à sua conta.')
    } catch (error) {
      setStatus('error')
      setMessage(getInviteError(error))
    }
  }, [loadWorkspaces, selectWorkspace, token])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      acceptInvite()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [acceptInvite])

  return (
    <main className="workspace-empty-page">
      <section className="workspace-empty-card invite-acceptance-card">
        <div className="login-panel__brand">
          <BrandIcon />
          <strong>Produzzy</strong>
        </div>

        <div className="workspace-empty-card__copy">
          <span>Convite de workspace</span>
          <h1>{status === 'success' ? 'Convite aceito' : 'Aceitar convite'}</h1>
          <p>{message}</p>
        </div>

        <div className="workspace-form__actions">
          {status === 'error' ? (
            <Button onClick={acceptInvite} variant="secondary">
              Tentar novamente
            </Button>
          ) : null}
          <Button disabled={status === 'loading'} onClick={onDone}>
            {status === 'success' ? 'Entrar no workspace' : 'Voltar'}
          </Button>
        </div>
      </section>
    </main>
  )
}

export default InviteAcceptancePage
