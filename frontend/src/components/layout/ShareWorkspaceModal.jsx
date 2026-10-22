import { useCallback, useEffect, useMemo, useState } from 'react'
import Button from '../ui/Button'
import ModalPortal from '../ui/ModalPortal'
import SelectMenu from '../ui/SelectMenu'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { memberTitleOptions } from '../../lib/formatters'
import {
  createWorkspaceInvite,
  createWorkspaceInviteLink,
  listWorkspaceInviteLinks,
  revokeWorkspaceInviteLink,
} from '../../services/workspaceService'

function buildIndividualInviteLink(invite) {
  if (!invite?.token) {
    return ''
  }

  return `${window.location.origin}/invites/${encodeURIComponent(
    invite.token,
  )}/accept`
}

function buildSharedInviteLink(inviteLink) {
  if (!inviteLink?.token) {
    return ''
  }

  return `${window.location.origin}/join/${encodeURIComponent(
    inviteLink.token,
  )}`
}

// What each permission allows (mirrors the role matrix in AGENTS.md).
const ROLE_DESCRIPTIONS = {
  admin:
    'Cadastra produtos e categorias, movimenta o estoque, cuida das reposições e da equipe.',
  employee: 'Movimenta o estoque e trabalha nas reposições.',
  viewer: 'Só consulta: vê o estoque e as reposições, sem alterar nada.',
}

const TITLE_OPTIONS = [
  { label: 'Sem cargo', value: '' },
  ...memberTitleOptions.map((title) => ({ label: title, value: title })),
]

const LINK_STATUS_LABELS = {
  active: 'Ativo',
  expired: 'Expirado',
  revoked: 'Revogado',
}

function formatDate(value) {
  if (!value) {
    return 'Sem data'
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
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
    return 'Você não tem permissão para revogar este link.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível revogar o link.'
}

function getRoleOptions(currentMemberRole) {
  if (currentMemberRole === 'owner') {
    return [
      { label: 'Administrador', value: 'admin' },
      { label: 'Funcionário', value: 'employee' },
      { label: 'Visualizador', value: 'viewer' },
    ]
  }

  if (currentMemberRole === 'admin') {
    return [
      { label: 'Funcionário', value: 'employee' },
      { label: 'Visualizador', value: 'viewer' },
    ]
  }

  return []
}

function ShareWorkspaceModal({ currentMemberRole, onClose, onInviteCreated }) {
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id
  const [activeTab, setActiveTab] = useState('shared-link')
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [inviteLinks, setInviteLinks] = useState([])
  const [createdInviteLink, setCreatedInviteLink] = useState(null)
  const [createdIndividualInvite, setCreatedIndividualInvite] = useState(null)
  const [individualEmail, setIndividualEmail] = useState('')
  const [individualRole, setIndividualRole] = useState('viewer')
  const [individualTitle, setIndividualTitle] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingLinks, setIsLoadingLinks] = useState(false)
  const [isRevoking, setIsRevoking] = useState(false)
  const [copiedTarget, setCopiedTarget] = useState('')
  const roleOptions = useMemo(
    () => getRoleOptions(currentMemberRole),
    [currentMemberRole],
  )
  const selectedIndividualRole = roleOptions.some(
    (option) => option.value === individualRole,
  )
    ? individualRole
    : roleOptions[0]?.value ?? ''
  const canInvite = Boolean(
    workspaceId && (currentMemberRole === 'owner' || currentMemberRole === 'admin'),
  )
  const activeInviteLink = useMemo(
    () =>
      createdInviteLink ??
      inviteLinks.find((inviteLink) => inviteLink.status === 'active') ??
      inviteLinks[0] ??
      null,
    [createdInviteLink, inviteLinks],
  )
  const sharedInviteLink = buildSharedInviteLink(createdInviteLink)
  const individualInviteLink = buildIndividualInviteLink(createdIndividualInvite)

  const loadInviteLinks = useCallback(async () => {
    if (!workspaceId || !canInvite) {
      setInviteLinks([])
      return
    }

    setIsLoadingLinks(true)

    try {
      const links = await listWorkspaceInviteLinks(workspaceId)
      setInviteLinks(Array.isArray(links) ? links : [])
    } catch {
      setInviteLinks([])
    } finally {
      setIsLoadingLinks(false)
    }
  }, [canInvite, workspaceId])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadInviteLinks()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadInviteLinks])

  async function refreshTeamContext() {
    try {
      await onInviteCreated?.()
    } catch {
      // A lista de equipe pode ser recarregada novamente pelo usuário.
    }
  }

  async function handleCreateInviteLink() {
    setError('')
    setFeedback('')
    setCopiedTarget('')

    if (!canInvite) {
      setError('Você não tem permissão para convidar membros neste workspace.')
      return
    }

    setIsSubmitting(true)

    try {
      const inviteLink = await createWorkspaceInviteLink(workspaceId)

      setCreatedInviteLink(inviteLink)
      setFeedback('Link compartilhável disponível para entrada como visualizador.')
      await loadInviteLinks()
      await refreshTeamContext()
    } catch (submitError) {
      setError(getInviteError(submitError))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleCreateIndividualInvite(event) {
    event.preventDefault()
    setError('')
    setFeedback('')
    setCopiedTarget('')
    setCreatedIndividualInvite(null)

    if (!canInvite) {
      setError('Você não tem permissão para convidar membros neste workspace.')
      return
    }

    const email = individualEmail.trim()

    if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      setError('Informe um e-mail válido ou deixe o campo em branco.')
      return
    }

    setIsSubmitting(true)

    try {
      // Without an e-mail the API creates a single-use link.
      const invite = await createWorkspaceInvite(workspaceId, {
        email: email || null,
        role: selectedIndividualRole,
        title: individualTitle || null,
      })

      setCreatedIndividualInvite(invite)
      setIndividualEmail('')
      setFeedback(
        email
          ? `Convite criado. Envie o link para ${email}.`
          : 'Link de convite criado. Ele vale para uma pessoa e expira em 7 dias.',
      )
      await refreshTeamContext()
    } catch (submitError) {
      setError(getInviteError(submitError))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRevokeInviteLink() {
    if (!workspaceId || !activeInviteLink?.id) {
      return
    }

    setIsRevoking(true)
    setError('')
    setFeedback('')

    try {
      await revokeWorkspaceInviteLink(workspaceId, activeInviteLink.id)
      setCreatedInviteLink(null)
      setCopiedTarget('')
      setFeedback('Link compartilhável revogado.')
      await loadInviteLinks()
      await refreshTeamContext()
    } catch (revokeError) {
      setError(getRevokeError(revokeError))
    } finally {
      setIsRevoking(false)
    }
  }

  async function handleCopy(value, target) {
    if (!value) {
      return
    }

    try {
      await navigator.clipboard.writeText(value)
      setCopiedTarget(target)
      setFeedback('Link copiado.')
    } catch {
      setError('Não foi possível copiar automaticamente.')
    }
  }

  return (
    <ModalPortal>
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

          <div
            aria-label="Escolher tipo de convite"
            className="workspace-share-tabs"
          >
            <button
              className={activeTab === 'shared-link' ? 'is-active' : ''}
              onClick={() => {
                setActiveTab('shared-link')
                setError('')
                setFeedback('')
              }}
              type="button"
            >
              Link compartilhável
            </button>
            <button
              className={activeTab === 'individual' ? 'is-active' : ''}
              onClick={() => {
                setActiveTab('individual')
                setError('')
                setFeedback('')
              }}
              type="button"
            >
              Convite individual
            </button>
          </div>

          {error ? <p className="form-error">{error}</p> : null}
          {feedback ? <p className="form-success">{feedback}</p> : null}

          {activeTab === 'shared-link' ? (
            <>
              <p className="workspace-modal__text">
                Qualquer pessoa com este link pode entrar no workspace como
                Visualizador.
              </p>

              {activeInviteLink ? (
                <div className="invite-link">
                  <span>Link compartilhável</span>
                  {sharedInviteLink ? (
                    <code>{sharedInviteLink}</code>
                  ) : (
                    <code>Gere o link para copiar a URL de entrada.</code>
                  )}
                  <div className="invite-link__meta">
                    <span>
                      Status:{' '}
                      {LINK_STATUS_LABELS[activeInviteLink.status] ?? activeInviteLink.status}
                    </span>
                    <span>Validade: {formatDate(activeInviteLink.expires_at)}</span>
                    <span>
                      Pessoas que entraram: {activeInviteLink.usage_count ?? 0}
                    </span>
                  </div>
                  <Button
                    disabled={!sharedInviteLink || copiedTarget === 'shared'}
                    onClick={() => handleCopy(sharedInviteLink, 'shared')}
                    variant="secondary"
                  >
                    {copiedTarget === 'shared' ? 'Copiado' : 'Copiar link'}
                  </Button>
                  {activeInviteLink.status === 'active' ? (
                    <Button
                      disabled={isRevoking}
                      onClick={handleRevokeInviteLink}
                      variant="secondary"
                    >
                      {isRevoking ? 'Revogando...' : 'Revogar link'}
                    </Button>
                  ) : null}
                </div>
              ) : null}

              <div className="workspace-form__actions">
                <Button
                  disabled={isSubmitting || isLoadingLinks || !canInvite}
                  onClick={handleCreateInviteLink}
                >
                  {isSubmitting ? 'Gerando...' : 'Gerar link'}
                </Button>
                <Button
                  disabled={isSubmitting || isRevoking}
                  onClick={onClose}
                  variant="secondary"
                >
                  Fechar
                </Button>
              </div>
            </>
          ) : (
            <form noValidate className="workspace-form" onSubmit={handleCreateIndividualInvite}>
              <p className="workspace-modal__text">
                Gera um link para uma pessoa entrar com a permissão e o cargo
                escolhidos. Com e-mail, só essa pessoa consegue usar o link. Sem
                e-mail, o link vale para quem entrar primeiro.
              </p>

              <label>
                <span>
                  E-mail <span className="field-optional">(opcional)</span>
                </span>
                <input
                  autoComplete="email"
                  disabled={isSubmitting}
                  onChange={(event) => setIndividualEmail(event.target.value)}
                  placeholder="pessoa@empresa.com"
                  type="email"
                  value={individualEmail}
                />
              </label>

              <div className="workspace-form__field">
                <span>Permissão</span>
                <SelectMenu
                  ariaLabel="Permissão do convidado"
                  disabled={isSubmitting || !roleOptions.length}
                  onChange={setIndividualRole}
                  options={roleOptions}
                  portal
                  value={selectedIndividualRole}
                />
                {ROLE_DESCRIPTIONS[selectedIndividualRole] ? (
                  <small className="workspace-form__hint">
                    {ROLE_DESCRIPTIONS[selectedIndividualRole]}
                  </small>
                ) : null}
              </div>

              <div className="workspace-form__field">
                <span>
                  Cargo <span className="field-optional">(opcional)</span>
                </span>
                <SelectMenu
                  ariaLabel="Cargo do convidado"
                  disabled={isSubmitting}
                  onChange={setIndividualTitle}
                  options={TITLE_OPTIONS}
                  portal
                  value={individualTitle}
                />
                <small className="workspace-form__hint">
                  Só o nome que a equipe vê, como Estoquista. Não muda o acesso.
                </small>
              </div>

              {individualInviteLink ? (
                <div className="invite-link">
                  <span>
                    {createdIndividualInvite?.is_open_invite
                      ? 'Link de uso único'
                      : 'Link individual'}
                  </span>
                  <code>{individualInviteLink}</code>
                  <Button
                    disabled={copiedTarget === 'individual'}
                    onClick={() => handleCopy(individualInviteLink, 'individual')}
                    type="button"
                    variant="secondary"
                  >
                    {copiedTarget === 'individual' ? 'Copiado' : 'Copiar link'}
                  </Button>
                </div>
              ) : null}

              <div className="workspace-form__actions">
                <Button
                  disabled={isSubmitting || !canInvite || !roleOptions.length}
                  type="submit"
                >
                  {isSubmitting
                    ? 'Criando...'
                    : individualEmail.trim()
                      ? 'Criar convite'
                      : 'Gerar link de convite'}
                </Button>
                <Button disabled={isSubmitting} onClick={onClose} variant="secondary">
                  Fechar
                </Button>
              </div>
            </form>
          )}
        </div>
      </section>
      </div>
    </ModalPortal>
  )
}

export default ShareWorkspaceModal
