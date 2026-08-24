export function needsReplenishment(product) {
  return product.quantity === 0 || product.quantity < product.minimum_quantity
}

export function getReplenishmentQuantity(product) {
  return Math.max(product.minimum_quantity - product.quantity, 0)
}

export function getReplenishmentStatus(product) {
  if (product.quantity === 0) {
    return { label: 'Sem estoque', tone: 'danger' }
  }

  if (product.quantity < product.minimum_quantity) {
    return { label: 'Baixo estoque', tone: 'warning' }
  }

  return { label: 'Em estoque', tone: 'success' }
}

export function getReplenishmentPriority(product) {
  if (product.quantity === 0) {
    return { label: 'Prioridade alta', tone: 'danger' }
  }

  if (product.quantity < product.minimum_quantity) {
    return { label: 'Prioridade média', tone: 'warning' }
  }

  return { label: 'Sem prioridade', tone: 'neutral' }
}
