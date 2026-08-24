import { useEffect, useMemo, useState } from 'react'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { formatWorkspaceRole, getWorkspaceRoleValue } from '../lib/formatters'
import { listWorkspaceMembers } from '../services/workspaceService'

const permissionsByRole = {
  owner: [
    'Gerenciar o workspace e suas configurações',
    'Gerenciar membros do workspace',
    'Gerenciar produtos e categorias',
    'Movimentar o estoque',
    'Criar e acompanhar reposições',
  ],
  admin: [
    'Gerenciar produtos e categorias',
    'Movimentar o estoque',
    'Criar e acompanhar reposições',
    'Gerenciar parte da equipe conforme as regras atuais',
  ],
  employee: [
    'Visualizar produtos e categorias',
    'Movimentar o estoque',
    'Criar e assumir reposições permitidas',
  ],
  viewer: [
    'Visualizar os dados do workspace',
    'Acessar configurações em modo somente leitura',
  ],
  member: [
    'Visualizar os dados liberados para o seu cargo',
    'Realizar ações conforme as permissões definidas pela equipe',
  ],
}

function formatDate(value) {
  if (!value) {
    return 'Não informada'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Não informada'
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'long',
  }).format(date)
}

function getWorkspaceUpdateError(error) {
  if (error?.status === 403) {
    return 'Apenas o Dono pode alterar o nome do workspace.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível salvar as alterações.'
}

function getWorkspaceDeleteError(error) {
  if (error?.status === 403) {
    return 'Apenas o owner principal pode excluir este workspace.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível excluir o workspace.'
}

function DeleteWorkspaceModal({
  activeWorkspace,
  deleteWorkspace,
  onClose,
}) {
  const [confirmationName, setConfirmationName] = useState('')
  const [error, setError] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const workspaceName = activeWorkspace?.name ?? ''
  const canConfirm = confirmationName === workspaceName

  async function handleDeleteWorkspace() {
    if (!activeWorkspace?.id || !canConfirm) {
      return
    }

    setIsDeleting(true)
    setError('')

    try {
      await deleteWorkspace(activeWorkspace.id)
      onClose()
    } catch (deleteError) {
      setError(getWorkspaceDeleteError(deleteError))
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="workspace-modal danger-confirm-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-workspace-title"
      >
        <div className="workspace-modal__header">
          <div>
            <span>Ação irreversível</span>
            <h2 id="delete-workspace-title">Excluir workspace</h2>
          </div>
          <button
            aria-label="Fechar modal"
            className="icon-button"
            disabled={isDeleting}
            onClick={onClose}
            type="button"
          >
            x
          </button>
        </div>

        <div className="workspace-form">
          <p className="workspace-modal__text">
            Esta ação remove o workspace, produtos, categorias, movimentações,
            reposições, convites e membros vinculados. Não será possível desfazer.
          </p>
          <label>
            Digite {workspaceName} para confirmar
            <input
              autoFocus
              disabled={isDeleting}
              onChange={(event) => {
                setConfirmationName(event.target.value)
                setError('')
              }}
              value={confirmationName}
            />
          </label>

          {error ? <p className="form-error">{error}</p> : null}

          <div className="workspace-form__actions">
            <Button
              disabled={!canConfirm || isDeleting}
              onClick={handleDeleteWorkspace}
              variant="danger"
            >
              {isDeleting ? 'Excluindo...' : 'Excluir workspace'}
            </Button>
            <Button disabled={isDeleting} onClick={onClose} variant="secondary">
              Cancelar
            </Button>
          </div>
        </div>
      </section>
    </div>
  )
}

function WorkspaceSettingsSection({
  activeWorkspace,
  canEditWorkspace,
  isResolvingRole,
  roleLabel,
  updateWorkspace,
}) {
  const [workspaceName, setWorkspaceName] = useState(
    activeWorkspace?.name ?? '',
  )
  const [isSavingWorkspace, setIsSavingWorkspace] = useState(false)
  const [workspaceError, setWorkspaceError] = useState('')
  const [workspaceFeedback, setWorkspaceFeedback] = useState('')
  const normalizedWorkspaceName = workspaceName.trim()
  const hasWorkspaceNameChanged =
    normalizedWorkspaceName !== (activeWorkspace?.name ?? '')

  async function handleWorkspaceSubmit(event) {
    event.preventDefault()

    if (!canEditWorkspace || !activeWorkspace?.id) {
      return
    }

    if (!normalizedWorkspaceName) {
      setWorkspaceError('Informe um nome para o workspace.')
      setWorkspaceFeedback('')
      return
    }

    setIsSavingWorkspace(true)
    setWorkspaceError('')
    setWorkspaceFeedback('')

    try {
      const updatedWorkspace = await updateWorkspace(
        activeWorkspace.id,
        normalizedWorkspaceName,
      )
      setWorkspaceName(updatedWorkspace.name)
      setWorkspaceFeedback('Nome do workspace atualizado com sucesso.')
    } catch (error) {
      setWorkspaceError(getWorkspaceUpdateError(error))
    } finally {
      setIsSavingWorkspace(false)
    }
  }

  return (
    <Card
      className="settings-section"
      title="Workspace"
      eyebrow="Organização"
    >
      <p className="settings-section__description">
        Informações do workspace ativo e identificação da sua organização.
      </p>

      <form
        className="settings-workspace-form"
        onSubmit={handleWorkspaceSubmit}
      >
        <label>
          Nome do workspace
          <input
            disabled={!canEditWorkspace || isSavingWorkspace}
            maxLength="100"
            onChange={(event) => {
              setWorkspaceName(event.target.value)
              setWorkspaceError('')
              setWorkspaceFeedback('')
            }}
            required
            value={workspaceName}
          />
        </label>
        <Button
          disabled={
            !canEditWorkspace ||
            !hasWorkspaceNameChanged ||
            !normalizedWorkspaceName ||
            isSavingWorkspace
          }
          type="submit"
        >
          {isSavingWorkspace ? 'Salvando...' : 'Salvar alterações'}
        </Button>
      </form>

      {!canEditWorkspace && !isResolvingRole ? (
        <p className="settings-section__hint">
          Apenas o Dono pode alterar o nome deste workspace.
        </p>
      ) : null}
      {workspaceError ? (
        <p className="settings-feedback settings-feedback--error" role="alert">
          {workspaceError}
        </p>
      ) : null}
      {workspaceFeedback ? (
        <p
          className="settings-feedback settings-feedback--success"
          aria-live="polite"
        >
          {workspaceFeedback}
        </p>
      ) : null}

      <dl className="settings-details">
        <div>
          <dt>ID do workspace</dt>
          <dd>#{activeWorkspace?.id ?? '—'}</dd>
        </div>
        <div>
          <dt>Criado em</dt>
          <dd>{formatDate(activeWorkspace?.created_at)}</dd>
        </div>
        <div>
          <dt>Seu cargo</dt>
          <dd>{roleLabel}</dd>
        </div>
      </dl>
    </Card>
  )
}

function SettingsPage() {
  const { isAuthenticated, user } = useAuth()
  const { activeWorkspace, deleteWorkspace, updateWorkspace } = useWorkspace()
  const { resolvedTheme, setThemePreference, themePreference } = useTheme()
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [resolvedRole, setResolvedRole] = useState({
    role: '',
    workspaceId: null,
  })
  const knownRole = getWorkspaceRoleValue(user, activeWorkspace)
  const resolvedRoleForWorkspace =
    resolvedRole.workspaceId === activeWorkspace?.id ? resolvedRole.role : ''
  const workspaceRole = knownRole || resolvedRoleForWorkspace
  const isResolvingRole = Boolean(
    activeWorkspace?.id && user?.id && !workspaceRole,
  )

  useEffect(() => {
    let shouldIgnore = false

    async function resolveWorkspaceRole() {
      if (!activeWorkspace?.id || !user?.id || knownRole) {
        return
      }

      try {
        const members = await listWorkspaceMembers(activeWorkspace.id)
        const currentMember = members.find(
          (member) => member.user_id === user.id,
        )

        if (!shouldIgnore) {
          setResolvedRole({
            role: currentMember?.role ?? 'member',
            workspaceId: activeWorkspace.id,
          })
        }
      } catch {
        if (!shouldIgnore) {
          setResolvedRole({
            role: 'member',
            workspaceId: activeWorkspace.id,
          })
        }
      }
    }

    resolveWorkspaceRole()

    return () => {
      shouldIgnore = true
    }
  }, [activeWorkspace?.id, knownRole, user?.id])

  const roleLabel = isResolvingRole
    ? 'Verificando...'
    : formatWorkspaceRole(workspaceRole)
  const permissions = useMemo(
    () => permissionsByRole[workspaceRole] ?? permissionsByRole.member,
    [workspaceRole],
  )
  const canEditWorkspace = workspaceRole === 'owner'

  return (
    <div className="page-stack settings-page">
      <div className="page-heading">
        <div>
          <h1>Configurações</h1>
          <p>Gerencie seu workspace, sua conta e suas preferências.</p>
        </div>
      </div>

      <div className="settings-page__grid">
        <WorkspaceSettingsSection
          activeWorkspace={activeWorkspace}
          canEditWorkspace={canEditWorkspace}
          isResolvingRole={isResolvingRole}
          key={activeWorkspace?.id ?? 'no-workspace'}
          roleLabel={roleLabel}
          updateWorkspace={updateWorkspace}
        />

        <Card
          className="settings-section"
          title="Minha conta"
          eyebrow="Perfil"
        >
          <p className="settings-section__description">
            Dados da conta conectada ao Produzzy nesta sessão.
          </p>

          <dl className="settings-details settings-details--account">
            <div>
              <dt>Nome</dt>
              <dd>{user?.name ?? 'Não informado'}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{user?.email ?? 'Não informado'}</dd>
            </div>
            <div>
              <dt>Cargo atual</dt>
              <dd>{roleLabel}</dd>
            </div>
            <div>
              <dt>Status da sessão</dt>
              <dd>
                <span className="settings-session-status">
                  {isAuthenticated && user?.is_active !== false
                    ? 'Ativa'
                    : 'Indisponível'}
                </span>
              </dd>
            </div>
          </dl>
        </Card>

        <Card
          className="settings-section settings-section--wide"
          title="Permissões"
          eyebrow="Acesso"
        >
          <div className="settings-permissions__header">
            <p className="settings-section__description">
              Resumo das ações disponíveis para seu cargo neste workspace.
            </p>
            <span className="settings-role-badge">{roleLabel}</span>
          </div>
          <ul className="settings-permission-list">
            {permissions.map((permission) => (
              <li key={permission}>
                <span aria-hidden="true">✓</span>
                {permission}
              </li>
            ))}
          </ul>
        </Card>

        <Card
          className="settings-section settings-section--wide"
          title="Preferências"
          eyebrow="Experiência"
        >
          <p className="settings-section__description">
            Padrões atuais da interface. Novas opções serão liberadas com
            confirmação antes de qualquer mudança no workspace.
          </p>
          <div className="settings-preferences">
            <div className="settings-preference">
              <div>
                <strong>Tema da interface</strong>
                <span>
                  Preferência atual: {resolvedTheme === 'dark' ? 'Escuro' : 'Claro'}.
                </span>
              </div>
              <select
                className="settings-preference__select"
                onChange={(event) => setThemePreference(event.target.value)}
                value={themePreference}
              >
                <option value="system">Sistema</option>
                <option value="light">Claro</option>
                <option value="dark">Escuro</option>
              </select>
            </div>
            <div className="settings-preference">
              <div>
                <strong>Idioma</strong>
                <span>Idioma padrão da aplicação.</span>
              </div>
              <span className="settings-preference__value">
                Português do Brasil
              </span>
            </div>
            <div className="settings-preference">
              <div>
                <strong>Formato de impressão</strong>
                <span>Aplicado aos QR Codes e etiquetas gerados.</span>
              </div>
              <span className="settings-preference__value">
                Padrão para impressão
              </span>
            </div>
          </div>
        </Card>

        <Card
          className="settings-section settings-section--wide settings-danger"
          title="Área de perigo"
          eyebrow="Ações irreversíveis"
        >
          <div className="settings-danger__content">
            <div>
              <h3>Excluir workspace</h3>
              <p>
                Remove este workspace e seus dados vinculados. Esta ação exige
                confirmação pelo nome e não pode ser desfeita.
              </p>
            </div>
            <Button
              disabled={!canEditWorkspace || isResolvingRole}
              onClick={() => setIsDeleteModalOpen(true)}
              variant="danger"
            >
              Excluir workspace
            </Button>
          </div>
          {!canEditWorkspace && !isResolvingRole ? (
            <p className="settings-section__hint">
              Apenas o owner principal pode excluir este workspace.
            </p>
          ) : null}
        </Card>
      </div>
      {isDeleteModalOpen ? (
        <DeleteWorkspaceModal
          activeWorkspace={activeWorkspace}
          deleteWorkspace={deleteWorkspace}
          onClose={() => setIsDeleteModalOpen(false)}
        />
      ) : null}
    </div>
  )
}

export default SettingsPage
