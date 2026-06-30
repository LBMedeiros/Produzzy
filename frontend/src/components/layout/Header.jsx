import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Button from '../ui/Button'
import CreateWorkspaceModal from './CreateWorkspaceModal'
import MemberAvatars from './MemberAvatars'
import MembersPopover from './MembersPopover'
import ShareWorkspaceModal from './ShareWorkspaceModal'
import UserMenu from './UserMenu'
import { useAuth } from '../../contexts/AuthContext'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { getFirstName, getInitials } from '../../lib/formatters'
import {
  listWorkspaceInvites,
  listWorkspaceMembers,
  updateWorkspaceMember,
} from '../../services/workspaceService'

function normalizeMember(member) {
  return {
    ...member,
    email: member.user_email ?? '',
    initials: getInitials(member.user_name, 'US'),
    name: member.user_name ?? member.user_email ?? 'Membro',
    status: 'Ativo',
  }
}

function normalizeInvite(invite) {
  return {
    email: invite.email,
    id: `invite-${invite.id}`,
    initials: getInitials(invite.email?.split('@')[0], 'CV'),
    isInvite: true,
    name: 'Convite pendente',
    role: invite.role,
    status: 'Convidada',
  }
}

function getMembersError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para visualizar a equipe deste workspace.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível carregar os membros.'
}

function getRoleUpdateError(error) {
  if (error?.status === 403) {
    return 'Apenas Owner ou Admin podem alterar cargos de outros membros.'
  }

  return error?.message ?? 'Não foi possível atualizar o cargo.'
}

function Header() {
  const [isCreateWorkspaceOpen, setIsCreateWorkspaceOpen] = useState(false)
  const [isMembersOpen, setIsMembersOpen] = useState(false)
  const [isShareOpen, setIsShareOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const [workspaceMembers, setWorkspaceMembers] = useState([])
  const [isMembersLoading, setIsMembersLoading] = useState(false)
  const [membersError, setMembersError] = useState('')
  const [membersFeedback, setMembersFeedback] = useState('')
  const [savingMemberId, setSavingMemberId] = useState(null)
  const membersContainerRef = useRef(null)
  const userMenuContainerRef = useRef(null)
  const membersRequestIdRef = useRef(0)
  const { user } = useAuth()
  const { activeWorkspace, selectWorkspace, workspaces } = useWorkspace()
  const workspaceId = activeWorkspace?.id
  const activeWorkspaceIdRef = useRef(workspaceId)
  const currentMemberRole = workspaceMembers.find(
    (member) => member.user_id === user?.id,
  )?.role
  const canManageRoles =
    activeWorkspace?.owner_id === user?.id ||
    currentMemberRole === 'owner' ||
    currentMemberRole === 'admin'

  useEffect(() => {
    activeWorkspaceIdRef.current = workspaceId
  }, [workspaceId])

  const avatarMembers = useMemo(() => {
    if (workspaceMembers.length) {
      return workspaceMembers
    }

    if (!user) {
      return []
    }

    return [
      {
        id: `current-${user.id}`,
        initials: getInitials(user.name),
        name: user.name,
      },
    ]
  }, [user, workspaceMembers])

  const loadMembers = useCallback(async () => {
    if (!workspaceId) {
      setWorkspaceMembers([])
      return []
    }

    const requestId = membersRequestIdRef.current + 1
    membersRequestIdRef.current = requestId
    setIsMembersLoading(true)
    setMembersError('')

    try {
      const [memberItems, inviteItems] = await Promise.all([
        listWorkspaceMembers(workspaceId),
        listWorkspaceInvites(workspaceId),
      ])
      const normalizedMembers = (Array.isArray(memberItems) ? memberItems : []).map(
        normalizeMember,
      )
      const pendingInvites = (Array.isArray(inviteItems) ? inviteItems : [])
        .filter((invite) => invite.status === 'pending')
        .map(normalizeInvite)
      const teamItems = [...normalizedMembers, ...pendingInvites]

      if (membersRequestIdRef.current === requestId) {
        setWorkspaceMembers(teamItems)
      }

      return teamItems
    } catch (error) {
      if (membersRequestIdRef.current === requestId) {
        setWorkspaceMembers([])
        setMembersError(getMembersError(error))
      }

      return []
    } finally {
      if (membersRequestIdRef.current === requestId) {
        setIsMembersLoading(false)
      }
    }
  }, [workspaceId])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setMembersFeedback('')
      setSavingMemberId(null)
      loadMembers()
    }, 0)

    return () => {
      window.clearTimeout(timeoutId)
      membersRequestIdRef.current += 1
    }
  }, [loadMembers])

  useEffect(() => {
    if (!isMembersOpen && !isUserMenuOpen) {
      return undefined
    }

    function handlePointerDown(event) {
      if (
        isMembersOpen &&
        !membersContainerRef.current?.contains(event.target)
      ) {
        setIsMembersOpen(false)
      }

      if (
        isUserMenuOpen &&
        !userMenuContainerRef.current?.contains(event.target)
      ) {
        setIsUserMenuOpen(false)
      }
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setIsMembersOpen(false)
        setIsUserMenuOpen(false)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isMembersOpen, isUserMenuOpen])

  async function handleMemberRoleChange(memberId, role) {
    if (!canManageRoles) {
      setMembersError(
        'Apenas Owner ou Admin podem alterar cargos de outros membros.',
      )
      return
    }

    const member = workspaceMembers.find((item) => item.id === memberId)

    if (!member || member.isInvite) {
      setMembersError('Não foi possível atualizar o cargo.')
      return
    }

    if (member.role === 'owner' || member.user_id === activeWorkspace.owner_id) {
      setMembersError('Não é possível alterar o cargo do dono do workspace.')
      return
    }

    setSavingMemberId(memberId)
    setMembersError('')
    setMembersFeedback('')

    try {
      const updatedMember = await updateWorkspaceMember(workspaceId, memberId, {
        role,
      })

      if (activeWorkspaceIdRef.current !== workspaceId) {
        return
      }

      const normalizedMember = normalizeMember(updatedMember)

      setWorkspaceMembers((currentMembers) =>
        currentMembers.map((currentMember) =>
          currentMember.id === memberId ? normalizedMember : currentMember,
        ),
      )
      setMembersFeedback('Cargo atualizado com sucesso.')
    } catch (error) {
      if (activeWorkspaceIdRef.current === workspaceId) {
        setMembersError(getRoleUpdateError(error))
      }
    } finally {
      if (activeWorkspaceIdRef.current === workspaceId) {
        setSavingMemberId(null)
      }
    }
  }

  function handleWorkspaceChange(event) {
    const selectedWorkspace = workspaces.find(
      (workspace) => String(workspace.id) === event.target.value,
    )

    if (selectedWorkspace) {
      selectWorkspace(selectedWorkspace)
    }
  }

  return (
    <>
      <header className="topbar">
        <div className="workspace-switcher">
          <select
            aria-label="Workspace atual"
            onChange={handleWorkspaceChange}
            value={activeWorkspace?.id ?? ''}
          >
            {workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>
                {workspace.name}
              </option>
            ))}
          </select>
          <span className="select-chevron" aria-hidden="true"></span>
        </div>

        <label className="search-field">
          <input type="search" placeholder="Buscar produtos, categorias ou membros" />
        </label>

        <div className="topbar__actions">
          <Button
            className="topbar__create"
            icon="+"
            onClick={() => setIsCreateWorkspaceOpen(true)}
          >
            Criar workspace
          </Button>
          <Button
            className="topbar__share"
            onClick={() => setIsShareOpen(true)}
            variant="secondary"
          >
            Compartilhar
          </Button>

          <div className="topbar__members" ref={membersContainerRef}>
            <MemberAvatars
              members={avatarMembers}
              isOpen={isMembersOpen}
              onToggle={() => {
                setIsMembersOpen((value) => {
                  const nextValue = !value

                  if (nextValue) {
                    setMembersFeedback('')
                    loadMembers()
                  }

                  return nextValue
                })
                setIsUserMenuOpen(false)
              }}
            />
            {isMembersOpen ? (
              <MembersPopover
                canManageRoles={canManageRoles}
                error={membersError}
                feedback={membersFeedback}
                isLoading={isMembersLoading}
                members={workspaceMembers}
                onRoleChange={handleMemberRoleChange}
                currentUserId={user?.id}
                ownerUserId={activeWorkspace?.owner_id}
                savingMemberId={savingMemberId}
              />
            ) : null}
          </div>

          <div className="topbar__user-wrap" ref={userMenuContainerRef}>
            <button
              className={`topbar__user ${isUserMenuOpen ? 'is-open' : ''}`}
              type="button"
              onClick={() => {
                setIsUserMenuOpen((value) => !value)
                setIsMembersOpen(false)
              }}
              aria-expanded={isUserMenuOpen}
              title={user?.email}
            >
              <div className="avatar avatar--light">{getInitials(user?.name)}</div>
              <strong>{getFirstName(user?.name)}</strong>
              <span className="select-chevron" aria-hidden="true"></span>
            </button>
            {isUserMenuOpen ? <UserMenu user={user} /> : null}
          </div>
        </div>
      </header>

      {isCreateWorkspaceOpen ? (
        <CreateWorkspaceModal onClose={() => setIsCreateWorkspaceOpen(false)} />
      ) : null}
      {isShareOpen ? <ShareWorkspaceModal onClose={() => setIsShareOpen(false)} /> : null}
    </>
  )
}

export default Header
