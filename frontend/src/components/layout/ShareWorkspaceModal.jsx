import { useState } from 'react'
import Button from '../ui/Button'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import {
  createWorkspaceInviteLink,
  revokeWorkspaceInvite,
} from '../../services/workspaceService'

function buildInviteLink(invite) {
  if (!invite?.token) {
    return ''
  }

  return `${window.location.origin}/invites/${encodeURIComponent(
    invite.token,
  )}/accept`
}

function getInviteError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para convidar membros neste workspace.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível criar o convite.'
}

function getRevokeError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para revogar este convite.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível revogar o convite.'
}

function ShareWorkspaceModal({ currentMemberRole, onClose, onInviteCreated }) {
  const { activeWorkspace } = useWorkspace()
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [createdInvite, setCreatedInvite] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isRevoking, setIsRevoking] = useState(false)
  const [isCopied, setIsCopied] = useState(false)
  const inviteLink = buildInviteLink(createdInvite)
  const canInvite = Boolean(
    activeWorkspace?.id &&
      (currentMemberRole === 'owner' || currentMemberRole === 'admin'),
  )

  async function handleCreateInviteLink() {
    setError('')
    setFeedback('')
    setIsCopied(false)

    if (!canInvite) {
      setError('Você não tem permissão para convidar membros neste workspace.')
      return
    }

    setIsSubmitting(true)

    try {
      const invite = await createWorkspaceInviteLink(activeWorkspace.id)

      setCreatedInvite(invite)
      setFeedback('Link de convite criado com acesso de visualizador.')

      try {
        await onInviteCreated?.()
      } catch {
        // A lista de equipe pode ser recarregada novamente pelo usuário.
      }
    } catch (submitError) {
      setError(getInviteError(submitError))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRevokeInviteLink() {
    if (!activeWorkspace?.id || !createdInvite?.id) {
      return
    }

    setIsRevoking(true)
    setError('')
    setFeedback('')

    try {
      await revokeWorkspaceInvite(activeWorkspace.id, createdInvite.id)
      setCreatedInvite(null)
      setIsCopied(false)
      setFeedback('Link de convite revogado.')
      await onInviteCreated?.()
    } catch (revokeError) {
      setError(getRevokeError(revokeError))
    } finally {
      setIsRevoking(false)
    }
  }

  async function handleCopyInviteLink() {
    if (!inviteLink) {
      return
    }

    try {
      await navigator.clipboard.writeText(inviteLink)
      setIsCopied(true)
      setFeedback('Link do convite copiado.')
    } catch {
      setError('Não foi possível copiar automaticamente.')
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="workspace-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-workspace-title"
      >
        <div className="workspace-modal__header">
          <div>
            <span>Convite</span>
            <h2 id="share-workspace-title">Compartilhar workspace</h2>
          </div>
          <button
            aria-label="Fechar modal"
            className="icon-button"
            type="button"
            onClick={onClose}
          >
            x
          </button>
        </div>

        <div className="workspace-form">
          {activeWorkspace?.name ? (
            <p className="workspace-modal__text">
              Workspace atual: {activeWorkspace.name}
            </p>
          ) : null}
          <p className="workspace-modal__text">
            Gere um link para entrada no workspace. Quem aceitar entra como
            visualizador; cargos maiores podem ser definidos depois pela equipe.
          </p>

          {error ? <p className="form-error">{error}</p> : null}
          {feedback ? <p className="form-success">{feedback}</p> : null}

          {inviteLink ? (
            <div className="invite-link">
              <span>Link do convite</span>
              <code>{inviteLink}</code>
              <Button
                disabled={isSubmitting || isCopied}
                onClick={handleCopyInviteLink}
                variant="secondary"
              >
                {isCopied ? 'Copiado' : 'Copiar link'}
              </Button>
              <Button
                disabled={isRevoking}
                onClick={handleRevokeInviteLink}
                variant="secondary"
              >
                {isRevoking ? 'Revogando...' : 'Revogar link'}
              </Button>
            </div>
          ) : null}

          <div className="workspace-form__actions">
            <Button
              disabled={isSubmitting || !canInvite}
              onClick={handleCreateInviteLink}
            >
              {isSubmitting ? 'Gerando...' : 'Gerar link'}
            </Button>
            <Button disabled={isSubmitting} onClick={onClose} variant="secondary">
              Fechar
            </Button>
          </div>
        </div>
      </section>
    </div>
  )
}

export default ShareWorkspaceModal
