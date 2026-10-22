import { ApiError, requestBlob } from '../lib/api'

function parseId(value, label) {
  const numericId = Number(value)

  if (!Number.isInteger(numericId) || numericId <= 0) {
    throw new ApiError(`${label} inválido.`, {
      status: 400,
    })
  }

  return numericId
}

// A4 sheet (3 columns) for the selected products: `code` is 'qr' (QR Codes
// with the Produzzy logo) or 'barcode', `copies` per product, and `format`
// 'png' (preview) or 'pdf' (download). Max 120 labels per request.
export function getPrintSheet(workspaceId, options = {}) {
  const validWorkspaceId = parseId(workspaceId, 'Workspace')
  const { copies = 1, format = 'png', productIds = [] } = options
  const query = new URLSearchParams({ copies: String(copies), format })

  productIds.forEach((productId) => {
    query.append('product_ids', String(parseId(productId, 'Produto')))
  })

  return requestBlob(
    `/workspaces/${validWorkspaceId}/products/print-sheet?${query.toString()}`,
  )
}
