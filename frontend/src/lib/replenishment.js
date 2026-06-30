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

  return { label: 'Baixo estoque', tone: 'warning' }
}

export function getReplenishmentPriority(product) {
  if (product.quantity === 0) {
    return { label: 'Prioridade alta', tone: 'danger' }
  }

  return { label: 'Prioridade média', tone: 'warning' }
}
