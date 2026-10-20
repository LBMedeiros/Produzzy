import { getFirstName, humanizeAuditAction } from './formatters'

const numberFormatter = new Intl.NumberFormat('pt-BR')

// Readable sentence for an audit-log entry (dashboard "Atividade recente"),
// e.g. "Ana deu entrada de +20 em Luva nitrílica P". Returned as segments so
// the view can style quantities and names: { kind: 'text' | 'strong' | 'in' |
// 'out', value }.
export function describeActivity(log, currentUserId) {
  const metadata = log.metadata ?? {}
  const actor =
    log.user_id && log.user_id === currentUserId
      ? 'Você'
      : getFirstName(log.user_name) || 'Alguém'
  const product = log.product_name ?? metadata.product_name ?? metadata.name
  const text = (value) => ({ kind: 'text', value })
  const strong = (value) => ({ kind: 'strong', value })

  let parts

  switch (log.action) {
    case 'stock.movement_created': {
      const quantity = numberFormatter.format(metadata.quantity ?? 0)
      const productName = product ?? 'um produto'

      if (metadata.movement_type === 'entrada') {
        parts = [text('deu entrada de'), { kind: 'in', value: `+${quantity}` }, text(`em ${productName}`)]
      } else if (metadata.movement_type === 'saida') {
        parts = [text('retirou'), { kind: 'out', value: `−${quantity}` }, text(`de ${productName}`)]
      } else {
        parts = [
          text(`ajustou o estoque de ${productName} para`),
          strong(numberFormatter.format(metadata.quantity_after ?? metadata.quantity ?? 0)),
        ]
      }
      break
    }
    case 'replenishment.created':
      parts = [text('abriu uma reposição de'), strong(product ?? 'um produto')]
      break
    case 'replenishment.updated':
      parts =
        metadata.status === 'in_progress'
          ? [text('iniciou a reposição de'), strong(product ?? 'um produto')]
          : [text('atualizou a reposição de'), strong(product ?? 'um produto')]
      break
    case 'replenishment.completed':
      parts = [text('marcou'), strong(product ?? 'uma reposição'), text('como pronta para estocar')]
      break
    case 'replenishment.stocked':
      parts = [text('estocou a reposição de'), strong(product ?? 'um produto')]
      break
    case 'replenishment.canceled':
      parts = [text('cancelou a reposição de'), strong(product ?? 'um produto')]
      break
    case 'replenishment.assignee_added':
      parts =
        metadata.assignee_user_id === log.user_id
          ? [text('assumiu a reposição de'), strong(product ?? 'um produto')]
          : [text('adicionou um responsável à reposição de'), strong(product ?? 'um produto')]
      break
    case 'replenishment.assignee_removed':
      parts =
        metadata.assignee_user_id === log.user_id
          ? [text('saiu da reposição de'), strong(product ?? 'um produto')]
          : [text('removeu um responsável da reposição de'), strong(product ?? 'um produto')]
      break
    case 'product.created':
      parts = [text('cadastrou o produto'), strong(product ?? '')]
      break
    case 'product.updated':
      parts = [text('editou o produto'), strong(product ?? '')]
      break
    case 'product.deleted':
      parts = [text('enviou para a lixeira o produto'), strong(product ?? '')]
      break
    case 'product.restored':
      parts = [text('restaurou o produto'), strong(product ?? '')]
      break
    case 'category.created':
      parts = [text('criou a categoria'), strong(metadata.name ?? metadata.category_name ?? '')]
      break
    case 'category.updated':
      parts = [text('editou a categoria'), strong(metadata.name ?? metadata.category_name ?? '')]
      break
    case 'category.deleted':
      parts = [text('removeu a categoria'), strong(metadata.category_name ?? metadata.name ?? '')]
      break
    case 'category.restored':
      parts = [text('restaurou a categoria'), strong(metadata.name ?? metadata.category_name ?? '')]
      break
    case 'invite.created':
      parts = metadata.email
        ? [text('convidou'), strong(metadata.email), text('para o workspace')]
        : [text('enviou um convite para o workspace')]
      break
    case 'invite.link_created':
    case 'invite_link.created':
      parts = [text('criou um link de convite')]
      break
    case 'invite.accepted':
    case 'invite_link.accepted':
      parts = [text('entrou no workspace')]
      break
    case 'workspace.updated':
      parts = metadata.new_name
        ? [text('renomeou o workspace para'), strong(metadata.new_name)]
        : [text('atualizou o workspace')]
      break
    default:
      parts = [text(`· ${humanizeAuditAction(log.action)}`)]
  }

  return { actor, parts: parts.filter((part) => part.value !== '') }
}

// "há 10 min", "há 2 h", "ontem, 17:42", "12/10, 09:30".
export function formatRelativeTime(value, now = new Date()) {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  const minutes = Math.floor((now - date) / 60000)

  if (minutes < 1) {
    return 'agora'
  }

  if (minutes < 60) {
    return `há ${minutes} min`
  }

  if (minutes < 6 * 60) {
    return `há ${Math.floor(minutes / 60)} h`
  }

  const time = new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
  const startOfToday = new Date(now)
  startOfToday.setHours(0, 0, 0, 0)
  const startOfYesterday = new Date(startOfToday)
  startOfYesterday.setDate(startOfYesterday.getDate() - 1)

  if (date >= startOfToday) {
    return `hoje, ${time}`
  }

  if (date >= startOfYesterday) {
    return `ontem, ${time}`
  }

  const day = new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
  }).format(date)

  return `${day}, ${time}`
}

// Whole days elapsed since `value` ("há 4 dias").
export function daysSince(value, now = new Date()) {
  if (!value) {
    return 0
  }

  return Math.max(0, Math.floor((now - new Date(value)) / 86400000))
}
