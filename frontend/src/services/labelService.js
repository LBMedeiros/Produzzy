import { ApiError, requestBlob } from '../lib/api'

function withQuery(path, params = {}) {
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, value)
    }
  })

  const queryString = query.toString()

  return queryString ? `${path}?${queryString}` : path
}

function parseId(value, label) {
  const numericId = Number(value)

  if (!Number.isInteger(numericId) || numericId <= 0) {
    throw new ApiError(`${label} inválido.`, {
      status: 400,
    })
  }

  return numericId
}

export function getProductQrCode(workspaceId, productId) {
  const validWorkspaceId = parseId(workspaceId, 'Workspace')
  const validProductId = parseId(productId, 'Produto')

  return requestBlob(
    `/workspaces/${validWorkspaceId}/products/${validProductId}/qrcode`,
  )
}

export function getProductLabel(workspaceId, productId) {
  const validWorkspaceId = parseId(workspaceId, 'Workspace')
  const validProductId = parseId(productId, 'Produto')

  return requestBlob(
    `/workspaces/${validWorkspaceId}/products/${validProductId}/label`,
  )
}

export function getProductBarcode(workspaceId, productId) {
  const validWorkspaceId = parseId(workspaceId, 'Workspace')
  const validProductId = parseId(productId, 'Produto')

  return requestBlob(
    `/workspaces/${validWorkspaceId}/products/${validProductId}/barcode`,
  )
}

export function getLabelsSheet(workspaceId, params = {}) {
  const validWorkspaceId = parseId(workspaceId, 'Workspace')

  return requestBlob(
    withQuery(`/workspaces/${validWorkspaceId}/products/labels-sheet`, params),
  )
}
