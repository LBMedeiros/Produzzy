import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Button from '../ui/Button'
import ModalPortal from '../ui/ModalPortal'
import { getInitials } from '../../lib/formatters'
import {
  createReplenishmentMessage,
  listReplenishmentMessages,
} from '../../services/replenishmentService'

export const REPLENISHMENT_MESSAGES_KEY = (workspaceId, requestId) => [
  'replenishment-messages',
  workspaceId,
  requestId,
]

function formatTime(value) {
  try {
    return new Intl.DateTimeFormat('pt-BR', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(new Date(value))
  } catch {
    return ''
  }
}

function ReplenishmentChatModal({
  canPost,
  currentUserId,
  onClose,
  productLabel,
  requestId,
  workspaceId,
}) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const listRef = useRef(null)

  const {
    data: messages = [],
    isError,
    isLoading,
  } = useQuery({
    queryKey: REPLENISHMENT_MESSAGES_KEY(workspaceId, requestId),
    queryFn: () => listReplenishmentMessages(workspaceId, requestId),
    enabled: Boolean(workspaceId && requestId),
  })

  const mutation = useMutation({
    mutationFn: (body) =>
      createReplenishmentMessage(workspaceId, requestId, body),
    onSuccess: (created) => {
      queryClient.setQueryData(
        REPLENISHMENT_MESSAGES_KEY(workspaceId, requestId),
        (current) => [...(current ?? []), created],
      )
      setDraft('')
      setError('')
    },
    onError: (mutationError) => {
      setError(mutationError?.message ?? 'Não foi possível enviar a mensagem.')
    },
  })

  // Keep the newest message in view as the thread grows.
  useEffect(() => {
    const node = listRef.current

    if (node) {
      node.scrollTop = node.scrollHeight
    }
  }, [messages])

  function handleSubmit(event) {
    event.preventDefault()

    const body = draft.trim()

    if (!body || mutation.isPending) {
      return
    }

    mutation.mutate(body)
  }

  return (
    <ModalPortal>
      <div className="modal-backdrop" role="presentation">
        <section
          aria-label={`Chat da reposição de ${productLabel}`}
          aria-modal="true"
          className="workspace-modal replenishment-chat-modal"
          role="dialog"
        >
          <div className="workspace-modal__header">
            <div>
              <span>Chat da reposição</span>
              <h2>{productLabel}</h2>
            </div>
            <button
              aria-label="Fechar chat"
              className="icon-button"
              onClick={onClose}
              type="button"
            >
              x
            </button>
          </div>

          <div className="replenishment-chat__list" ref={listRef}>
            {isLoading ? (
              <p className="replenishment-chat__state">Carregando mensagens...</p>
            ) : isError ? (
              <p className="replenishment-chat__state">
                Não foi possível carregar o chat.
              </p>
            ) : messages.length ? (
              messages.map((message) => (
                <div
                  className={`replenishment-chat__message ${
                    message.user_id === currentUserId ? 'is-mine' : ''
                  }`}
                  key={message.id}
                >
                  <span
                    className="replenishment-chat__avatar"
                    title={message.user_name ?? 'Usuário'}
                  >
                    {getInitials(message.user_name)}
                  </span>
                  <div className="replenishment-chat__bubble">
                    <div className="replenishment-chat__meta">
                      <strong>{message.user_name ?? 'Usuário'}</strong>
                      <span>{formatTime(message.created_at)}</span>
                    </div>
                    <p>{message.body}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="replenishment-chat__state">
                Nenhum recado ainda. Deixe aqui onde parou e o que ainda falta.
              </p>
            )}
          </div>

          {canPost ? (
            <form className="replenishment-chat__form" onSubmit={handleSubmit}>
              <textarea
                disabled={mutation.isPending}
                maxLength={1000}
                onChange={(event) => {
                  setDraft(event.target.value)
                  setError('')
                }}
                placeholder="Escreva um recado para os responsáveis..."
                rows={2}
                value={draft}
              />
              {error ? <p className="form-error">{error}</p> : null}
              <div className="replenishment-chat__form-actions">
                <Button
                  disabled={mutation.isPending || !draft.trim()}
                  type="submit"
                >
                  {mutation.isPending ? 'Enviando...' : 'Enviar'}
                </Button>
              </div>
            </form>
          ) : (
            <p className="replenishment-chat__hint">
              Apenas responsáveis por esta reposição podem comentar. Você pode
              acompanhar o histórico.
            </p>
          )}
        </section>
      </div>
    </ModalPortal>
  )
}

export default ReplenishmentChatModal
