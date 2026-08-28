import { useEffect, useMemo, useRef, useState } from 'react'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import UserAvatar from '../components/ui/UserAvatar'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { formatWorkspaceRole, getWorkspaceRoleValue } from '../lib/formatters'
import { listWorkspaceMembers } from '../services/workspaceService'

const MAX_AVATAR_FILE_SIZE = 5 * 1024 * 1024
const allowedAvatarTypes = new Set(['image/jpeg', 'image/png', 'image/webp'])

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

function getProfileUpdateError(error) {
  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível atualizar seu perfil.'
}

function getEmailChangeError(error) {
  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível alterar o email.'
}

function getAvatarError(error) {
  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível atualizar sua foto.'
}

function PasswordVisibilityIcon({ isVisible }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M2.5 12s3.6-6.5 9.5-6.5S21.5 12 21.5 12 17.9 18.5 12 18.5 2.5 12 2.5 12Z" />
      <path d="M12 9.25a2.75 2.75 0 1 1 0 5.5 2.75 2.75 0 0 1 0-5.5Z" />
      {isVisible ? <path d="M4.5 4.5 19.5 19.5" /> : null}
    </svg>
  )
}

function EmailChangeModal({ currentEmail, onClose, onSubmit }) {
  const [email, setEmail] = useState(currentEmail ?? '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [isPasswordVisible, setIsPasswordVisible] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const visibilityLabel = isPasswordVisible ? 'Ocultar senha' : 'Mostrar senha'

  async function handleSubmit(event) {
    event.preventDefault()

    const normalizedEmail = email.trim()

    if (!normalizedEmail) {
      setError('Informe o novo email.')
      return
    }

    if (!currentPassword) {
      setError('Informe sua senha atual.')
      return
    }

    setIsSaving(true)
    setError('')

    try {
      await onSubmit({
        current_password: currentPassword,
        email: normalizedEmail,
      })
      onClose()
    } catch (submitError) {
      setError(getEmailChangeError(submitError))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="workspace-modal settings-email-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="change-email-title"
      >
        <div className="workspace-modal__header">
          <div>
            <span>Ação sensível</span>
            <h2 id="change-email-title">Alterar email</h2>
          </div>
          <button
            aria-label="Fechar modal"
            className="icon-button"
            disabled={isSaving}
            onClick={onClose}
            type="button"
          >
            x
          </button>
        </div>

        <form className="workspace-form" onSubmit={handleSubmit}>
          <label>
            Novo email
            <input
              autoComplete="email"
              disabled={isSaving}
              onChange={(event) => {
                setEmail(event.target.value)
                setError('')
              }}
              placeholder="novo@email.com"
              required
              type="email"
              value={email}
            />
          </label>

          <label className="settings-password-label" htmlFor="settings-current-password">
            Senha atual
          </label>
          <span className="settings-password-field">
            <input
              autoComplete="current-password"
              disabled={isSaving}
              id="settings-current-password"
              onChange={(event) => {
                setCurrentPassword(event.target.value)
                setError('')
              }}
              placeholder="Digite sua senha"
              required
              type={isPasswordVisible ? 'text' : 'password'}
              value={currentPassword}
            />
            <button
              aria-label={visibilityLabel}
              aria-pressed={isPasswordVisible}
              className="settings-password-field__toggle"
              disabled={isSaving}
              onClick={() => setIsPasswordVisible((value) => !value)}
              type="button"
            >
              <PasswordVisibilityIcon isVisible={isPasswordVisible} />
            </button>
          </span>

          {error ? <p className="form-error">{error}</p> : null}

          <div className="workspace-form__actions">
            <Button disabled={isSaving} type="submit">
              {isSaving ? 'Alterando...' : 'Alterar email'}
            </Button>
            <Button disabled={isSaving} onClick={onClose} variant="secondary">
              Cancelar
            </Button>
          </div>
        </form>
      </section>
    </div>
  )
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

function ProfilePhotoSection({ removeAvatar, uploadAvatar, user }) {
  const fileInputRef = useRef(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [avatarError, setAvatarError] = useState('')
  const [avatarFeedback, setAvatarFeedback] = useState('')
  const [isRemovingAvatar, setIsRemovingAvatar] = useState(false)
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false)
  const displayedAvatarUrl = previewUrl || user?.avatar_url || ''
  const hasAvatar = Boolean(user?.avatar_url || previewUrl)

  useEffect(() => {
    if (!previewUrl) {
      return undefined
    }

    return () => {
      URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  async function handleAvatarFileChange(event) {
    const file = event.target.files?.[0]
    event.target.value = ''

    if (!file) {
      return
    }

    if (!allowedAvatarTypes.has(file.type)) {
      setAvatarError('Use uma imagem JPG, PNG ou WebP.')
      setAvatarFeedback('')
      return
    }

    if (file.size > MAX_AVATAR_FILE_SIZE) {
      setAvatarError('A imagem deve ter no máximo 5 MB.')
      setAvatarFeedback('')
      return
    }

    const localPreviewUrl = URL.createObjectURL(file)
    setPreviewUrl(localPreviewUrl)
    setIsUploadingAvatar(true)
    setAvatarError('')
    setAvatarFeedback('')

    try {
      await uploadAvatar(file)
      setAvatarFeedback('Foto de perfil atualizada com sucesso.')
    } catch (error) {
      setAvatarError(getAvatarError(error))
    } finally {
      setPreviewUrl('')
      setIsUploadingAvatar(false)
    }
  }

  async function handleRemoveAvatar() {
    if (!hasAvatar || isUploadingAvatar || isRemovingAvatar) {
      return
    }

    if (user?.avatar_url && !window.confirm('Remover sua foto de perfil?')) {
      return
    }

    if (!user?.avatar_url && previewUrl) {
      setPreviewUrl('')
      return
    }

    setIsRemovingAvatar(true)
    setAvatarError('')
    setAvatarFeedback('')

    try {
      await removeAvatar()
      setAvatarFeedback('Foto de perfil removida.')
    } catch (error) {
      setAvatarError(getAvatarError(error))
    } finally {
      setIsRemovingAvatar(false)
    }
  }

  return (
    <Card
      className="settings-section settings-section--wide settings-profile-photo"
      title="Foto de perfil"
      eyebrow="Perfil"
    >
      <div className="settings-profile-photo__content">
        <UserAvatar
          alt={user?.name ? `Foto de ${user.name}` : 'Foto de perfil'}
          className="settings-profile-photo__avatar"
          name={user?.name}
          src={displayedAvatarUrl}
        />
        <div className="settings-profile-photo__identity">
          <strong>{user?.name ?? 'Usuário'}</strong>
          <span>{user?.email ?? 'Email não informado'}</span>
        </div>
        <div className="settings-profile-photo__actions">
          <input
            accept="image/jpeg,image/png,image/webp"
            className="settings-profile-photo__input"
            disabled={isUploadingAvatar || isRemovingAvatar}
            onChange={handleAvatarFileChange}
            ref={fileInputRef}
            type="file"
          />
          <Button
            disabled={isUploadingAvatar || isRemovingAvatar}
            onClick={() => fileInputRef.current?.click()}
            variant="secondary"
          >
            {isUploadingAvatar ? 'Enviando...' : 'Alterar foto'}
          </Button>
          <Button
            disabled={!hasAvatar || isUploadingAvatar || isRemovingAvatar}
            onClick={handleRemoveAvatar}
            variant="ghost"
          >
            {isRemovingAvatar ? 'Removendo...' : 'Remover foto'}
          </Button>
        </div>
      </div>

      {avatarError ? (
        <p className="settings-feedback settings-feedback--error" role="alert">
          {avatarError}
        </p>
      ) : null}
      {avatarFeedback ? (
        <p
          className="settings-feedback settings-feedback--success"
          aria-live="polite"
        >
          {avatarFeedback}
        </p>
      ) : null}
    </Card>
  )
}

function ProfileSettingsSection({
  changeEmail,
  isAuthenticated,
  roleLabel,
  updateProfile,
  user,
}) {
  const [profileName, setProfileName] = useState(user?.name ?? '')
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false)
  const [isSavingProfile, setIsSavingProfile] = useState(false)
  const [profileError, setProfileError] = useState('')
  const [profileFeedback, setProfileFeedback] = useState('')
  const normalizedProfileName = profileName.trim()
  const hasProfileNameChanged = normalizedProfileName !== (user?.name ?? '')

  async function handleProfileSubmit(event) {
    event.preventDefault()

    if (!normalizedProfileName) {
      setProfileError('Informe seu nome.')
      setProfileFeedback('')
      return
    }

    setIsSavingProfile(true)
    setProfileError('')
    setProfileFeedback('')

    try {
      const updatedUser = await updateProfile({ name: normalizedProfileName })
      setProfileName(updatedUser.name)
      setProfileFeedback('Nome atualizado com sucesso.')
    } catch (error) {
      setProfileError(getProfileUpdateError(error))
    } finally {
      setIsSavingProfile(false)
    }
  }

  async function handleEmailChange(data) {
    await changeEmail(data)
    setProfileFeedback('Email atualizado com sucesso.')
    setProfileError('')
  }

  return (
    <Card
      className="settings-section settings-profile-section"
      title="Perfil"
      eyebrow="Minha conta"
    >
      <p className="settings-section__description">
        Dados da sua conta conectada ao Produzzy nesta sessão.
      </p>

      <form className="settings-profile-form" onSubmit={handleProfileSubmit}>
        <label>
          Nome
          <input
            autoComplete="name"
            disabled={isSavingProfile}
            maxLength="100"
            onChange={(event) => {
              setProfileName(event.target.value)
              setProfileError('')
              setProfileFeedback('')
            }}
            required
            value={profileName}
          />
        </label>
        <Button
          disabled={
            !hasProfileNameChanged ||
            !normalizedProfileName ||
            isSavingProfile
          }
          type="submit"
        >
          {isSavingProfile ? 'Salvando...' : 'Salvar'}
        </Button>
      </form>

      <div className="settings-profile-fields">
        <div className="settings-profile-field">
          <span>Email</span>
          <strong>{user?.email ?? 'Não informado'}</strong>
          <Button
            onClick={() => {
              setIsEmailModalOpen(true)
              setProfileError('')
              setProfileFeedback('')
            }}
            size="sm"
            variant="secondary"
          >
            Alterar email
          </Button>
        </div>
        <div className="settings-profile-field">
          <span>Cargo atual</span>
          <strong>{roleLabel}</strong>
        </div>
        <div className="settings-profile-field">
          <span>Status da sessão</span>
          <strong>
            <span className="settings-session-status">
              {isAuthenticated && user?.is_active !== false
                ? 'Ativa'
                : 'Indisponível'}
            </span>
          </strong>
        </div>
      </div>

      {profileError ? (
        <p className="settings-feedback settings-feedback--error" role="alert">
          {profileError}
        </p>
      ) : null}
      {profileFeedback ? (
        <p
          className="settings-feedback settings-feedback--success"
          aria-live="polite"
        >
          {profileFeedback}
        </p>
      ) : null}

      {isEmailModalOpen ? (
        <EmailChangeModal
          currentEmail={user?.email}
          onClose={() => setIsEmailModalOpen(false)}
          onSubmit={handleEmailChange}
        />
      ) : null}
    </Card>
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
  const {
    changeEmail,
    isAuthenticated,
    removeAvatar,
    updateProfile,
    uploadAvatar,
    user,
  } = useAuth()
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
        <ProfilePhotoSection
          removeAvatar={removeAvatar}
          uploadAvatar={uploadAvatar}
          user={user}
        />

        <ProfileSettingsSection
          changeEmail={changeEmail}
          isAuthenticated={isAuthenticated}
          key={user?.id ?? 'no-user'}
          roleLabel={roleLabel}
          updateProfile={updateProfile}
          user={user}
        />

        <WorkspaceSettingsSection
          activeWorkspace={activeWorkspace}
          canEditWorkspace={canEditWorkspace}
          isResolvingRole={isResolvingRole}
          key={activeWorkspace?.id ?? 'no-workspace'}
          roleLabel={roleLabel}
          updateWorkspace={updateWorkspace}
        />

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
