import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Button from '../ui/Button'
import CreateWorkspaceModal from './CreateWorkspaceModal'
import MemberAvatars from './MemberAvatars'
import MembersPopover from './MembersPopover'
import ShareWorkspaceModal from './ShareWorkspaceModal'
import UserMenu from './UserMenu'
import { useAuth } from '../../contexts/AuthContext'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import {
  getFirstName,
  getInitials,
  getWorkspaceRoleValue,
} from '../../lib/formatters'
import {
  deleteWorkspaceMember,
  listWorkspaceInvites,
  listWorkspaceMembers,
  revokeWorkspaceInvite,
  updateWorkspaceMember,
} from '../../services/workspaceService'
import { searchWorkspace } from '../../services/searchService'

const WORKSPACE_MENU_TRANSITION_MS = 150
const GLOBAL_SEARCH_MIN_LENGTH = 2
const GLOBAL_SEARCH_DEBOUNCE_MS = 250
const EMPTY_SEARCH_RESULTS = { products: [], replenishments: [] }

const navigationSearchItems = [
  {
    description: 'Visão geral do estoque',
    label: 'Dashboard',
    page: 'dashboard',
    terms: ['dashboard', 'painel', 'inicio', 'início'],
  },
  {
    description: 'Produtos, filtros e movimentações',
    label: 'Estoque',
    page: 'stock',
    terms: ['estoque', 'produtos', 'movimentacoes', 'movimentações'],
  },
  {
    description: 'Quadro de necessidades',
    label: 'Reposição',
    page: 'production',
    terms: ['reposicao', 'reposição', 'necessidades', 'producao', 'produção'],
  },
  {
    description: 'QR Codes e etiquetas para impressão',
    label: 'Etiquetas',
    page: 'labels',
    terms: ['etiquetas', 'qr code', 'qrcode', 'codigos', 'códigos'],
  },
  {
    description: 'Preferências e workspace',
    label: 'Configurações',
    page: 'settings',
    terms: ['configuracoes', 'configurações', 'settings', 'preferencias'],
  },
]

const replenishmentStatusLabels = {
  canceled: 'Cancelada',
  completed: 'Pronto para estocar',
  in_progress: 'Em andamento',
  open: 'Necessário repor',
  stocked: 'Estocado',
}

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
  const isLinkInvite = invite.email?.endsWith('@invite.produzzy.local')

  return {
    email: isLinkInvite ? 'Link compartilhável' : invite.email,
    id: `invite-${invite.id}`,
    inviteId: invite.id,
    initials: isLinkInvite ? 'LK' : getInitials(invite.email?.split('@')[0], 'CV'),
    isInvite: true,
    name: isLinkInvite ? 'Link de convite' : 'Convite pendente',
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
    return 'Apenas Dono ou Admin podem alterar cargos de outros membros.'
  }

  return error?.message ?? 'Não foi possível atualizar o cargo.'
}

function getInviteRevokeError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para revogar este convite.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível revogar o convite.'
}

function getMemberRemoveError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para remover este membro.'
  }

  return error?.message ?? 'Não foi possível remover o membro.'
}

function getSearchError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para buscar neste workspace.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível concluir a busca.'
}

function Header({ onNavigate }) {
  const [isCreateWorkspaceOpen, setIsCreateWorkspaceOpen] = useState(false)
  const [isMembersOpen, setIsMembersOpen] = useState(false)
  const [isShareOpen, setIsShareOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const [isWorkspaceMenuMounted, setIsWorkspaceMenuMounted] = useState(false)
  const [isWorkspaceMenuOpen, setIsWorkspaceMenuOpen] = useState(false)
  const [workspaceMenuIndex, setWorkspaceMenuIndex] = useState(0)
  const [searchTerm, setSearchTerm] = useState('')
  const [searchResults, setSearchResults] = useState(EMPTY_SEARCH_RESULTS)
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [isSearchLoading, setIsSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [activeSearchIndex, setActiveSearchIndex] = useState(0)
  const [workspaceMembers, setWorkspaceMembers] = useState([])
  const [isMembersLoading, setIsMembersLoading] = useState(false)
  const [membersError, setMembersError] = useState('')
  const [membersFeedback, setMembersFeedback] = useState('')
  const [removingMemberId, setRemovingMemberId] = useState(null)
  const [revokingInviteId, setRevokingInviteId] = useState(null)
  const [savingMemberId, setSavingMemberId] = useState(null)
  const searchContainerRef = useRef(null)
  const searchInputRef = useRef(null)
  const membersContainerRef = useRef(null)
  const userMenuContainerRef = useRef(null)
  const workspaceSwitcherRef = useRef(null)
  const membersRequestIdRef = useRef(0)
  const searchRequestIdRef = useRef(0)
  const workspaceMenuTimeoutRef = useRef(null)
  const { user } = useAuth()
  const { activeWorkspace, selectWorkspace, workspaces } = useWorkspace()
  const workspaceId = activeWorkspace?.id
  const activeWorkspaceIdRef = useRef(workspaceId)
  const workspaceRole = getWorkspaceRoleValue(user, activeWorkspace)
  const currentMemberRole = workspaceMembers.find(
    (member) => member.user_id === user?.id,
  )?.role ?? workspaceRole
  const canManageRoles =
    activeWorkspace?.owner_id === user?.id ||
    currentMemberRole === 'owner' ||
    currentMemberRole === 'admin'

  const openWorkspaceMenu = useCallback(() => {
    const activeWorkspaceIndex = workspaces.findIndex(
      (workspace) => workspace.id === activeWorkspace?.id,
    )

    window.clearTimeout(workspaceMenuTimeoutRef.current)
    setWorkspaceMenuIndex(activeWorkspaceIndex >= 0 ? activeWorkspaceIndex : 0)
    setIsWorkspaceMenuMounted(true)

    window.requestAnimationFrame(() => {
      setIsWorkspaceMenuOpen(true)
    })
  }, [activeWorkspace?.id, workspaces])

  const closeWorkspaceMenu = useCallback(() => {
    window.clearTimeout(workspaceMenuTimeoutRef.current)
    setIsWorkspaceMenuOpen(false)
    workspaceMenuTimeoutRef.current = window.setTimeout(() => {
      setIsWorkspaceMenuMounted(false)
    }, WORKSPACE_MENU_TRANSITION_MS)
  }, [])

  const closeSearchPanel = useCallback(() => {
    setIsSearchOpen(false)
    setActiveSearchIndex(0)
  }, [])

  useEffect(() => {
    activeWorkspaceIdRef.current = workspaceId
  }, [workspaceId])

  useEffect(
    () => () => {
      window.clearTimeout(workspaceMenuTimeoutRef.current)
    },
    [],
  )

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

  const searchQuery = searchTerm.trim()
  const canSearch = searchQuery.length >= GLOBAL_SEARCH_MIN_LENGTH

  const navigationResults = useMemo(() => {
    if (!canSearch) {
      return []
    }

    const normalizedQuery = searchQuery.toLowerCase()

    return navigationSearchItems.filter((item) =>
      item.terms.some((term) => term.includes(normalizedQuery)),
    )
  }, [canSearch, searchQuery])

  const flatSearchResults = useMemo(() => {
    if (!canSearch) {
      return []
    }

    return [
      ...navigationResults.map((item) => ({
        ...item,
        group: 'Navegação',
        id: `navigation-${item.page}`,
        type: 'navigation',
      })),
      ...(searchResults.products ?? []).map((product) => ({
        description: `#${product.code} · ${product.category} · ${product.quantity} un.`,
        group: 'Produtos',
        id: `product-${product.id}`,
        label: product.name,
        productId: product.id,
        type: 'product',
      })),
      ...(searchResults.replenishments ?? []).map((replenishment) => ({
        description: `${
          replenishmentStatusLabels[replenishment.status] ?? replenishment.status
        } · #${replenishment.product_code} · ${replenishment.quantity_needed} un.`,
        group: 'Reposições',
        id: `replenishment-${replenishment.id}`,
        label: replenishment.product_name,
        replenishmentId: replenishment.id,
        status: replenishment.status,
        type: 'replenishment',
      })),
    ]
  }, [canSearch, navigationResults, searchResults])

  const groupedSearchResults = useMemo(
    () =>
      flatSearchResults.reduce((groups, item) => {
        const group = groups.find((currentGroup) => currentGroup.name === item.group)

        if (group) {
          group.items.push(item)
          return groups
        }

        return [...groups, { items: [item], name: item.group }]
      }, []),
    [flatSearchResults],
  )
  const boundedActiveSearchIndex = flatSearchResults.length
    ? Math.min(activeSearchIndex, flatSearchResults.length - 1)
    : 0
  const activeSearchResult = flatSearchResults[boundedActiveSearchIndex]

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
      setRemovingMemberId(null)
      setSavingMemberId(null)
      loadMembers()
    }, 0)

    return () => {
      window.clearTimeout(timeoutId)
      membersRequestIdRef.current += 1
    }
  }, [loadMembers])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setSearchTerm('')
      setSearchResults(EMPTY_SEARCH_RESULTS)
      setSearchError('')
      setIsSearchLoading(false)
      closeSearchPanel()
      closeWorkspaceMenu()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [closeSearchPanel, closeWorkspaceMenu, workspaceId])

  useEffect(() => {
    const requestId = searchRequestIdRef.current + 1
    searchRequestIdRef.current = requestId

    const timeoutId = window.setTimeout(async () => {
      setActiveSearchIndex(0)

      if (!workspaceId || !canSearch) {
        setSearchResults(EMPTY_SEARCH_RESULTS)
        setSearchError('')
        setIsSearchLoading(false)
        return
      }

      setIsSearchLoading(true)
      setSearchError('')

      try {
        const data = await searchWorkspace(workspaceId, searchQuery)

        if (searchRequestIdRef.current === requestId) {
          setSearchResults({
            products: data.products ?? [],
            replenishments: data.replenishments ?? [],
          })
        }
      } catch (error) {
        if (searchRequestIdRef.current === requestId) {
          setSearchResults(EMPTY_SEARCH_RESULTS)
          setSearchError(getSearchError(error))
        }
      } finally {
        if (searchRequestIdRef.current === requestId) {
          setIsSearchLoading(false)
        }
      }
    }, canSearch ? GLOBAL_SEARCH_DEBOUNCE_MS : 0)

    return () => window.clearTimeout(timeoutId)
  }, [canSearch, searchQuery, workspaceId])

  useEffect(() => {
    function handleKeyDown(event) {
      const target = event.target
      const isTypingTarget =
        target instanceof HTMLElement &&
        (target.matches('input, textarea, select') || target.isContentEditable)

      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === 'k' &&
        !isTypingTarget
      ) {
        event.preventDefault()
        searchInputRef.current?.focus()
        setIsSearchOpen(true)
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  useEffect(() => {
    if (
      !isMembersOpen &&
      !isUserMenuOpen &&
      !isWorkspaceMenuMounted &&
      !isSearchOpen
    ) {
      return undefined
    }

    function handlePointerDown(event) {
      if (
        isWorkspaceMenuMounted &&
        !workspaceSwitcherRef.current?.contains(event.target)
      ) {
        closeWorkspaceMenu()
      }

      if (
        isSearchOpen &&
        !searchContainerRef.current?.contains(event.target)
      ) {
        closeSearchPanel()
      }

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
        closeWorkspaceMenu()
        closeSearchPanel()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [
    closeSearchPanel,
    closeWorkspaceMenu,
    isMembersOpen,
    isSearchOpen,
    isUserMenuOpen,
    isWorkspaceMenuMounted,
  ])

  async function handleMemberRoleChange(memberId, role) {
    if (!canManageRoles) {
      setMembersError(
        'Apenas Dono ou Admin podem alterar cargos de outros membros.',
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

  async function handleInviteRevoke(inviteId) {
    if (!canManageRoles) {
      setMembersError('Apenas Dono ou Admin podem revogar convites.')
      return
    }

    if (!workspaceId) {
      setMembersError('Selecione um workspace para revogar convites.')
      return
    }

    if (revokingInviteId !== null) {
      return
    }

    const invite = workspaceMembers.find(
      (item) => item.isInvite && item.inviteId === inviteId,
    )

    if (!invite) {
      setMembersError('Não foi possível localizar o convite.')
      return
    }

    setRevokingInviteId(inviteId)
    setMembersError('')
    setMembersFeedback('')

    try {
      await revokeWorkspaceInvite(workspaceId, inviteId)

      if (activeWorkspaceIdRef.current !== workspaceId) {
        return
      }

      setWorkspaceMembers((currentMembers) =>
        currentMembers.filter(
          (currentMember) =>
            !currentMember.isInvite || currentMember.inviteId !== inviteId,
        ),
      )
      setMembersFeedback(`Convite para ${invite.email} revogado.`)
    } catch (error) {
      if (activeWorkspaceIdRef.current === workspaceId) {
        setMembersError(getInviteRevokeError(error))
      }
    } finally {
      if (activeWorkspaceIdRef.current === workspaceId) {
        setRevokingInviteId(null)
      }
    }
  }

  async function handleMemberRemove(memberId) {
    if (!canManageRoles) {
      setMembersError('Apenas Dono ou Admin podem remover membros.')
      return
    }

    if (!workspaceId) {
      setMembersError('Selecione um workspace para remover membros.')
      return
    }

    if (removingMemberId !== null) {
      return
    }

    const member = workspaceMembers.find((item) => item.id === memberId)

    if (!member || member.isInvite) {
      setMembersError('Não foi possível localizar o membro.')
      return
    }

    if (member.role === 'owner' || member.user_id === activeWorkspace.owner_id) {
      setMembersError('Não é possível remover o owner por esta ação.')
      return
    }

    const shouldRemove = window.confirm(
      `Remover ${member.name} deste workspace? A pessoa perderá acesso aos dados deste workspace.`,
    )

    if (!shouldRemove) {
      return
    }

    setRemovingMemberId(memberId)
    setMembersError('')
    setMembersFeedback('')

    try {
      await deleteWorkspaceMember(workspaceId, memberId)

      if (activeWorkspaceIdRef.current !== workspaceId) {
        return
      }

      setWorkspaceMembers((currentMembers) =>
        currentMembers.filter((currentMember) => currentMember.id !== memberId),
      )
      setMembersFeedback(`${member.name} foi removido do workspace.`)
    } catch (error) {
      if (activeWorkspaceIdRef.current === workspaceId) {
        setMembersError(getMemberRemoveError(error))
      }
    } finally {
      if (activeWorkspaceIdRef.current === workspaceId) {
        setRemovingMemberId(null)
      }
    }
  }

  function handleWorkspaceSelect(workspace) {
    if (!workspace) {
      return
    }

    selectWorkspace(workspace)
    closeWorkspaceMenu()
    setIsMembersOpen(false)
    setIsUserMenuOpen(false)
  }

  function handleWorkspaceKeyDown(event) {
    if (!workspaces.length) {
      return
    }

    if (event.key === 'Escape') {
      closeWorkspaceMenu()
      return
    }

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      openWorkspaceMenu()
      setWorkspaceMenuIndex((currentIndex) => {
        const direction = event.key === 'ArrowDown' ? 1 : -1

        return (
          (currentIndex + direction + workspaces.length) % workspaces.length
        )
      })
      return
    }

    if (event.key === 'Enter' && isWorkspaceMenuOpen) {
      event.preventDefault()
      handleWorkspaceSelect(workspaces[workspaceMenuIndex])
    }
  }

  function handleSearchResultSelect(result) {
    if (!result) {
      return
    }

    if (result.type === 'navigation') {
      onNavigate?.(result.page)
    }

    if (result.type === 'product') {
      onNavigate?.('stock', {
        productId: result.productId,
        type: 'product-detail',
        workspaceId,
      })
    }

    if (result.type === 'replenishment') {
      onNavigate?.('production', {
        requestId: result.replenishmentId,
        status: result.status,
        type: 'replenishment-focus',
        workspaceId,
      })
    }

    setSearchTerm('')
    setSearchResults(EMPTY_SEARCH_RESULTS)
    closeSearchPanel()
  }

  function handleSearchKeyDown(event) {
    if (event.key === 'Escape') {
      closeSearchPanel()
      return
    }

    if (!flatSearchResults.length) {
      return
    }

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      setIsSearchOpen(true)
      setActiveSearchIndex((currentIndex) => {
        const direction = event.key === 'ArrowDown' ? 1 : -1

        return (
          (currentIndex + direction + flatSearchResults.length) %
          flatSearchResults.length
        )
      })
      return
    }

    if (event.key === 'Enter' && isSearchOpen) {
      event.preventDefault()
      handleSearchResultSelect(activeSearchResult)
    }
  }

  return (
    <>
      <header className="topbar">
        <div
          className="workspace-switcher"
          ref={workspaceSwitcherRef}
          onKeyDown={handleWorkspaceKeyDown}
        >
          <button
            aria-activedescendant={
              isWorkspaceMenuOpen && workspaces[workspaceMenuIndex]
                ? `workspace-option-${workspaces[workspaceMenuIndex].id}`
                : undefined
            }
            aria-controls="workspace-switcher-menu"
            aria-expanded={isWorkspaceMenuOpen}
            aria-haspopup="listbox"
            aria-label="Selecionar workspace"
            className="workspace-switcher__button"
            type="button"
            onClick={() => {
              if (isWorkspaceMenuOpen) {
                closeWorkspaceMenu()
              } else {
                openWorkspaceMenu()
              }
            }}
          >
            <span>{activeWorkspace?.name ?? 'Selecionar workspace'}</span>
            <span className="select-chevron" aria-hidden="true"></span>
          </button>
          {isWorkspaceMenuMounted ? (
            <div
              className={`workspace-switcher__menu ${
                isWorkspaceMenuOpen ? 'is-open' : ''
              }`}
              id="workspace-switcher-menu"
              role="listbox"
            >
              {workspaces.map((workspace, index) => (
                <button
                  aria-selected={workspace.id === activeWorkspace?.id}
                  className={[
                    'workspace-switcher__option',
                    workspace.id === activeWorkspace?.id ? 'is-selected' : '',
                    workspaceMenuIndex === index ? 'is-active' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  id={`workspace-option-${workspace.id}`}
                  key={workspace.id}
                  role="option"
                  type="button"
                  onClick={() => handleWorkspaceSelect(workspace)}
                  onMouseEnter={() => setWorkspaceMenuIndex(index)}
                >
                  <span>{workspace.name}</span>
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div
          className={`search-field global-search ${
            isSearchOpen ? 'is-open' : ''
          }`}
          ref={searchContainerRef}
        >
          <input
            aria-activedescendant={
              isSearchOpen && activeSearchResult
                ? activeSearchResult.id
                : undefined
            }
            aria-controls="global-search-results"
            aria-expanded={isSearchOpen && canSearch}
            aria-haspopup="listbox"
            aria-label="Busca global"
            placeholder="Buscar no workspace"
            ref={searchInputRef}
            type="search"
            value={searchTerm}
            onChange={(event) => {
              setSearchTerm(event.target.value)
              setIsSearchOpen(true)
            }}
            onFocus={() => setIsSearchOpen(true)}
            onKeyDown={handleSearchKeyDown}
          />
          {isSearchOpen && canSearch ? (
            <div
              aria-label="Resultados da busca global"
              className="global-search__panel"
              id="global-search-results"
              role="listbox"
            >
              {isSearchLoading ? (
                <p className="global-search__state" role="status">
                  Buscando...
                </p>
              ) : null}
              {!isSearchLoading && searchError ? (
                <p className="global-search__state global-search__state--error">
                  {searchError}
                </p>
              ) : null}
              {!isSearchLoading &&
              !searchError &&
              !flatSearchResults.length ? (
                <p className="global-search__state">
                  Nenhum resultado encontrado.
                </p>
              ) : null}
              {!isSearchLoading && !searchError && flatSearchResults.length
                ? groupedSearchResults.map((group) => (
                    <div className="global-search__group" key={group.name}>
                      <span>{group.name}</span>
                      {group.items.map((item) => (
                        <button
                          aria-selected={activeSearchResult?.id === item.id}
                          className={
                            activeSearchResult?.id === item.id
                              ? 'is-active'
                              : ''
                          }
                          id={item.id}
                          key={item.id}
                          role="option"
                          type="button"
                          onClick={() => handleSearchResultSelect(item)}
                          onMouseEnter={() => {
                            const nextIndex = flatSearchResults.findIndex(
                              (result) => result.id === item.id,
                            )

                            if (nextIndex >= 0) {
                              setActiveSearchIndex(nextIndex)
                            }
                          }}
                        >
                          <strong>{item.label}</strong>
                          <small>{item.description}</small>
                        </button>
                      ))}
                    </div>
                  ))
                : null}
            </div>
          ) : null}
        </div>

        <div className="topbar__actions">
          <Button
            className="topbar__create"
            icon="+"
            onClick={() => setIsCreateWorkspaceOpen(true)}
          >
            Criar workspace
          </Button>

          {canManageRoles ? (
            <Button
              className="topbar__share"
              onClick={() => {
                setIsShareOpen(true)
                setIsMembersOpen(false)
                setIsUserMenuOpen(false)
              }}
              variant="secondary"
            >
              Compartilhar
            </Button>
          ) : null}

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
                currentMemberRole={currentMemberRole}
                error={membersError}
                feedback={membersFeedback}
                isLoading={isMembersLoading}
                members={workspaceMembers}
                onInviteRevoke={handleInviteRevoke}
                onMemberRemove={handleMemberRemove}
                onRoleChange={handleMemberRoleChange}
                currentUserId={user?.id}
                ownerUserId={activeWorkspace?.owner_id}
                removingMemberId={removingMemberId}
                revokingInviteId={revokingInviteId}
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
      {isShareOpen ? (
        <ShareWorkspaceModal
          currentMemberRole={currentMemberRole}
          onClose={() => setIsShareOpen(false)}
          onInviteCreated={loadMembers}
        />
      ) : null}
    </>
  )
}

export default Header
