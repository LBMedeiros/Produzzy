import { useCallback, useEffect, useState } from 'react'
import BrandIcon from '../components/ui/BrandIcon'
import Button from '../components/ui/Button'
import { useWorkspace } from '../contexts/WorkspaceContext'
import {
  acceptWorkspaceInvite,
  acceptWorkspaceInviteLink,
} from '../services/workspaceService'

function getInviteError(error, type) {
  if (type === 'individual' && error?.status === 403) {
    return 'Este convite pertence a outro e-mail.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível aceitar o convite.'
}

function InviteAcceptancePage({ onDone, token, type = 'individual' }) {
  const { loadWorkspaces, selectWorkspace } = useWorkspace()
  const [status, setStatus] = useState('loading')
  const [message, setMessage] = useState(
    type === 'link'
      ? 'Você foi convidado para participar deste workspace como Visualizador.'
      : 'Aceitando convite...',
  )
  const isInviteLink = type === 'link'

  const acceptInvite = useCallback(async () => {
    if (!token) {
      setStatus('error')
      setMessage(isInviteLink ? 'Link de convite inválido.' : 'Convite inválido.')
      return
    }

    setStatus('loading')
    setMessage(
      isInviteLink
        ? 'Entrando no workspace como Visualizador...'
        : 'Aceitando convite...',
    )

    try {
      const membership = isInviteLink
        ? await acceptWorkspaceInviteLink(token)
        : await acceptWorkspaceInvite(token)
      const workspaces = await loadWorkspaces()
      const acceptedWorkspace = workspaces.find(
        (workspace) => workspace.id === membership.workspace_id,
      )

      if (acceptedWorkspace) {
        selectWorkspace(acceptedWorkspace)
      }

      window.history.replaceState(window.history.state, '', '/')
      setStatus('success')
      setMessage(
        isInviteLink
          ? 'Entrada confirmada. O workspace foi adicionado à sua conta.'
          : 'Convite aceito. O workspace foi adicionado à sua conta.',
      )
    } catch (error) {
      setStatus('error')
      setMessage(getInviteError(error, type))
    }
  }, [isInviteLink, loadWorkspaces, selectWorkspace, token, type])

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
          <span>
            {isInviteLink ? 'Link compartilhável' : 'Convite de workspace'}
          </span>
          <h1>
            {status === 'success'
              ? isInviteLink
                ? 'Entrada confirmada'
                : 'Convite aceito'
              : isInviteLink
                ? 'Entrar no workspace'
                : 'Aceitar convite'}
          </h1>
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
