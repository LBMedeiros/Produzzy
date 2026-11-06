import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Button from './Button'
import ModalPortal from './ModalPortal'
import { getInitials } from '../../lib/formatters'

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

// Conversation thread in a modal (replenishment handoff chat, stock request
// conversation). The caller supplies how to load/send messages and the copy.
function ChatModal({
  canPost,
  closeLabel = 'Fechar chat',
  currentUserId,
  emptyText,
  eyebrow,
  loadMessages,
  onClose,
  placeholder,
  queryKey,
  readOnlyHint,
  sendMessage,
  title,
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
    queryKey,
    queryFn: loadMessages,
  })

  const mutation = useMutation({
    mutationFn: sendMessage,
    onSuccess: (created) => {
      queryClient.setQueryData(queryKey, (current) => [...(current ?? []), created])
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
          aria-label={`${eyebrow}: ${title}`}
          aria-modal="true"
          className="workspace-modal replenishment-chat-modal"
          role="dialog"
        >
          <div className="workspace-modal__header">
            <div>
              <span>{eyebrow}</span>
              <h2>{title}</h2>
            </div>
            <button
              aria-label={closeLabel}
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
                Não foi possível carregar a conversa.
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
              <p className="replenishment-chat__state">{emptyText}</p>
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
                placeholder={placeholder}
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
          ) : readOnlyHint ? (
            <p className="replenishment-chat__hint">{readOnlyHint}</p>
          ) : null}
        </section>
      </div>
    </ModalPortal>
  )
}

export default ChatModal
