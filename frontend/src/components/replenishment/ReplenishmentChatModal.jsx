import ChatModal from '../ui/ChatModal'
import {
  createReplenishmentMessage,
  listReplenishmentMessages,
} from '../../services/replenishmentService'

export const REPLENISHMENT_MESSAGES_KEY = (workspaceId, requestId) => [
  'replenishment-messages',
  workspaceId,
  requestId,
]

function ReplenishmentChatModal({
  canPost,
  currentUserId,
  onClose,
  productLabel,
  requestId,
  workspaceId,
}) {
  return (
    <ChatModal
      canPost={canPost}
      currentUserId={currentUserId}
      emptyText="Nenhum recado ainda. Deixe aqui onde parou e o que ainda falta."
      eyebrow="Chat da reposição"
      loadMessages={() => listReplenishmentMessages(workspaceId, requestId)}
      onClose={onClose}
      placeholder="Escreva um recado para os responsáveis..."
      queryKey={REPLENISHMENT_MESSAGES_KEY(workspaceId, requestId)}
      readOnlyHint="Apenas responsáveis por esta reposição ou quem a abriu podem comentar. Você pode acompanhar o histórico."
      sendMessage={(body) => createReplenishmentMessage(workspaceId, requestId, body)}
      title={productLabel}
    />
  )
}

export default ReplenishmentChatModal
