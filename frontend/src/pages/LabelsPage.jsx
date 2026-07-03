import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import { useWorkspace } from '../contexts/WorkspaceContext'
import {
  getLabelsSheet,
  getProductLabel,
  getProductQrCode,
  getQrCodesSheet,
} from '../services/labelService'
import { listProducts } from '../services/productService'

function getFriendlyError(error) {
  if (error?.status === 400 || error?.status === 422) {
    return 'Selecione um produto válido antes de gerar QR Code ou etiqueta.'
  }

  if (error?.status === 403) {
    return 'Você não tem permissão para gerar etiquetas neste workspace.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível concluir a ação.'
}

function sanitizeFileName(value) {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}

function downloadBlob(blob, fileName) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function getValidId(value) {
  const numericId = Number(value)

  return Number.isInteger(numericId) && numericId > 0 ? numericId : null
}

function formatProductCode(productId) {
  const numericProductId = getValidId(productId)

  return numericProductId ? String(numericProductId).padStart(9, '0') : '—'
}

function LabelsPage() {
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id
  const [products, setProducts] = useState([])
  const [selectedProductId, setSelectedProductId] = useState('')
  const [qrBlob, setQrBlob] = useState(null)
  const [labelBlob, setLabelBlob] = useState(null)
  const [qrPreviewUrl, setQrPreviewUrl] = useState('')
  const [labelPreviewUrl, setLabelPreviewUrl] = useState('')
  const [isLoadingProducts, setIsLoadingProducts] = useState(true)
  const [isLoadingQr, setIsLoadingQr] = useState(false)
  const [isLoadingLabel, setIsLoadingLabel] = useState(false)
  const [isLoadingLabelsSheet, setIsLoadingLabelsSheet] = useState(false)
  const [isLoadingQrCodesSheet, setIsLoadingQrCodesSheet] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const qrPreviewUrlRef = useRef('')
  const labelPreviewUrlRef = useRef('')

  const clearPreviews = useCallback(() => {
    if (qrPreviewUrlRef.current) {
      URL.revokeObjectURL(qrPreviewUrlRef.current)
      qrPreviewUrlRef.current = ''
    }

    if (labelPreviewUrlRef.current) {
      URL.revokeObjectURL(labelPreviewUrlRef.current)
      labelPreviewUrlRef.current = ''
    }

    setQrPreviewUrl('')
    setLabelPreviewUrl('')
    setQrBlob(null)
    setLabelBlob(null)
  }, [])

  const selectedProduct = useMemo(() => {
    const numericProductId = getValidId(selectedProductId)

    if (!numericProductId) {
      return null
    }

    return products.find((product) => product.id === numericProductId) ?? null
  }, [products, selectedProductId])

  const loadProducts = useCallback(async () => {
    const numericWorkspaceId = getValidId(workspaceId)

    if (!numericWorkspaceId) {
      setProducts([])
      setSelectedProductId('')
      setIsLoadingProducts(false)
      return
    }

    clearPreviews()
    setIsLoadingProducts(true)
    setError('')

    try {
      const activeProducts = await listProducts(numericWorkspaceId, {
        limit: 100,
        status: 'active',
      })
      setProducts(activeProducts)
      setSelectedProductId((currentProductId) => {
        if (
          currentProductId &&
          activeProducts.some(
            (product) => String(product.id) === String(currentProductId),
          )
        ) {
          return currentProductId
        }

        return activeProducts[0]?.id ? String(activeProducts[0].id) : ''
      })
    } catch (loadError) {
      setError(getFriendlyError(loadError))
    } finally {
      setIsLoadingProducts(false)
    }
  }, [clearPreviews, workspaceId])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadProducts()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadProducts])

  useEffect(() => {
    return () => {
      if (qrPreviewUrlRef.current) {
        URL.revokeObjectURL(qrPreviewUrlRef.current)
      }

      if (labelPreviewUrlRef.current) {
        URL.revokeObjectURL(labelPreviewUrlRef.current)
      }
    }
  }, [])

  function requireSelectedProduct(product = selectedProduct) {
    const productId = getValidId(product?.id)

    if (!product || !productId) {
      setError('Selecione um produto válido antes de gerar QR Code ou etiqueta.')
      return false
    }

    return true
  }

  function setQrPreview(blob) {
    if (qrPreviewUrlRef.current) {
      URL.revokeObjectURL(qrPreviewUrlRef.current)
    }

    const previewUrl = URL.createObjectURL(blob)
    qrPreviewUrlRef.current = previewUrl
    setQrBlob(blob)
    setQrPreviewUrl(previewUrl)
  }

  function setLabelPreview(blob) {
    if (labelPreviewUrlRef.current) {
      URL.revokeObjectURL(labelPreviewUrlRef.current)
    }

    const previewUrl = URL.createObjectURL(blob)
    labelPreviewUrlRef.current = previewUrl
    setLabelBlob(blob)
    setLabelPreviewUrl(previewUrl)
  }

  async function handleGenerateQrCode(product = selectedProduct) {
    const numericWorkspaceId = getValidId(workspaceId)

    if (!numericWorkspaceId || !requireSelectedProduct(product)) {
      return null
    }

    const productId = getValidId(product.id)

    if (!productId) {
      setError('Selecione um produto válido antes de gerar QR Code ou etiqueta.')
      return null
    }

    if (String(productId) !== String(selectedProductId)) {
      clearPreviews()
    }
    setSelectedProductId(String(productId))
    setIsLoadingQr(true)
    setError('')
    setSuccessMessage('')

    try {
      const blob = await getProductQrCode(numericWorkspaceId, productId)
      setQrPreview(blob)
      setSuccessMessage('QR Code gerado com sucesso.')

      return blob
    } catch (generateError) {
      setError(getFriendlyError(generateError))
      return null
    } finally {
      setIsLoadingQr(false)
    }
  }

  async function handleGenerateLabel(product = selectedProduct) {
    const numericWorkspaceId = getValidId(workspaceId)

    if (!numericWorkspaceId || !requireSelectedProduct(product)) {
      return null
    }

    const productId = getValidId(product.id)

    if (!productId) {
      setError('Selecione um produto válido antes de gerar QR Code ou etiqueta.')
      return null
    }

    if (String(productId) !== String(selectedProductId)) {
      clearPreviews()
    }
    setSelectedProductId(String(productId))
    setIsLoadingLabel(true)
    setError('')
    setSuccessMessage('')

    try {
      const blob = await getProductLabel(numericWorkspaceId, productId)
      setLabelPreview(blob)
      setSuccessMessage('Etiqueta gerada com sucesso.')

      return blob
    } catch (generateError) {
      setError(getFriendlyError(generateError))
      return null
    } finally {
      setIsLoadingLabel(false)
    }
  }

  async function handleDownloadQrCode() {
    const blob = qrBlob ?? (await handleGenerateQrCode())

    if (blob && selectedProduct) {
      downloadBlob(
        blob,
        `qrcode-${sanitizeFileName(selectedProduct.name)}-${selectedProduct.id}.png`,
      )
    }
  }

  async function handleDownloadLabel() {
    const blob = labelBlob ?? (await handleGenerateLabel())

    if (blob && selectedProduct) {
      downloadBlob(
        blob,
        `etiqueta-${sanitizeFileName(selectedProduct.name)}-${selectedProduct.id}.png`,
      )
    }
  }

  async function handleDownloadLabelsSheet() {
    const numericWorkspaceId = getValidId(workspaceId)

    if (!numericWorkspaceId) {
      return
    }

    setIsLoadingLabelsSheet(true)
    setError('')
    setSuccessMessage('')

    try {
      const blob = await getLabelsSheet(numericWorkspaceId)
      downloadBlob(blob, `etiquetas-workspace-${numericWorkspaceId}.png`)
      setSuccessMessage('Etiquetas para impressão baixadas com sucesso.')
    } catch (downloadError) {
      setError(getFriendlyError(downloadError))
    } finally {
      setIsLoadingLabelsSheet(false)
    }
  }

  async function handleDownloadQrCodesSheet() {
    const numericWorkspaceId = getValidId(workspaceId)

    if (!numericWorkspaceId) {
      return
    }

    setIsLoadingQrCodesSheet(true)
    setError('')
    setSuccessMessage('')

    try {
      const blob = await getQrCodesSheet(numericWorkspaceId)
      downloadBlob(blob, `qrcodes-workspace-${numericWorkspaceId}.png`)
      setSuccessMessage('QR Codes para impressão baixados com sucesso.')
    } catch (downloadError) {
      setError(getFriendlyError(downloadError))
    } finally {
      setIsLoadingQrCodesSheet(false)
    }
  }

  function handleSelectProduct(productId) {
    const numericProductId = getValidId(productId)

    setSelectedProductId(numericProductId ? String(numericProductId) : '')
    setError('')
    setSuccessMessage('')
    clearPreviews()
  }

  const columns = [
    { key: 'name', label: 'Produto' },
    { key: 'category', label: 'Categoria' },
    { key: 'id', label: 'ID' },
    {
      key: 'actions',
      label: 'Ações',
      render: (product) => (
        <div className="table-actions">
          <button type="button" onClick={() => handleSelectProduct(product.id)}>
            Selecionar
          </button>
          <button type="button" onClick={() => handleGenerateQrCode(product)}>
            QR Code
          </button>
          <button type="button" onClick={() => handleGenerateLabel(product)}>
            Etiqueta
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>Etiquetas e QR Codes</h1>
          <p>Gere etiquetas e códigos para os produtos ativos do workspace</p>
        </div>
      </div>

      {error ? <p className="stock-feedback stock-feedback--error">{error}</p> : null}
      {successMessage ? (
        <p className="stock-feedback stock-feedback--success">{successMessage}</p>
      ) : null}

      <section className="feature-grid feature-grid--four">
        <Card title="QR Code individual" eyebrow="Backend real">
          <p>Acesse o detalhe do produto a partir da etiqueta física.</p>
        </Card>
        <Card title="Etiqueta individual" eyebrow="Imagem PNG">
          <p>Combine a marca, o QR Code e o código de barras do produto.</p>
        </Card>
        <Card title="Impressão em lote" eyebrow="Para impressão">
          <p>Organize vários itens em uma folha para economizar papel.</p>
        </Card>
        <Card title="Produto selecionado" eyebrow="Catálogo">
          <p>{selectedProduct ? selectedProduct.name : 'Selecione um produto.'}</p>
          {selectedProduct ? (
            <small className="product-code">
              Código: {formatProductCode(selectedProduct.id)}
            </small>
          ) : null}
        </Card>
      </section>

      <Card title="Impressão em lote" eyebrow="Folhas para impressão">
        <p className="batch-printing__intro">
          Escolha entre QR Codes identificados ou etiquetas completas para os
          produtos ativos do workspace.
        </p>
        <div className="batch-printing">
          <article className="batch-printing__option">
            <div>
              <h3>QR Codes para impressão</h3>
              <p>
                Gere uma folha com QR Codes identificados pelo nome do produto.
              </p>
            </div>
            <Button
              disabled={isLoadingQrCodesSheet || !products.length}
              onClick={handleDownloadQrCodesSheet}
              variant="secondary"
            >
              {isLoadingQrCodesSheet ? 'Baixando...' : 'Baixar QR Codes'}
            </Button>
          </article>
          <article className="batch-printing__option">
            <div>
              <h3>Etiquetas para impressão</h3>
              <p>
                Gere uma folha com etiquetas completas, QR Code e código de
                barras.
              </p>
            </div>
            <Button
              disabled={isLoadingLabelsSheet || !products.length}
              onClick={handleDownloadLabelsSheet}
              variant="secondary"
            >
              {isLoadingLabelsSheet ? 'Baixando...' : 'Baixar etiquetas'}
            </Button>
          </article>
        </div>
      </Card>

      <section className="content-grid content-grid--label">
        <Card title="Prévia real" eyebrow="Preview">
          <div className="label-preview-stack">
            <label className="stock-form">
              Produto
              <select
                disabled={isLoadingProducts || !products.length}
                onChange={(event) => handleSelectProduct(event.target.value)}
                value={selectedProductId}
              >
                {products.length ? null : (
                  <option value="">Nenhum produto ativo</option>
                )}
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
            </label>

            <div className="label-actions">
              <Button
                disabled={isLoadingQr || !selectedProduct}
                onClick={() => handleGenerateQrCode()}
                variant="secondary"
              >
                {isLoadingQr ? 'Gerando...' : 'Gerar QR Code'}
              </Button>
              <Button
                disabled={isLoadingLabel || !selectedProduct}
                onClick={() => handleGenerateLabel()}
                variant="secondary"
              >
                {isLoadingLabel ? 'Gerando...' : 'Gerar etiqueta'}
              </Button>
            </div>

            <div className="real-preview-grid">
              <div className="real-preview-card real-preview-card--qr">
                <h3>
                  QR Code - {selectedProduct?.name ?? 'Selecione um produto'}
                </h3>
                {qrPreviewUrl ? (
                  <img alt="QR Code real do produto" src={qrPreviewUrl} />
                ) : (
                  <div className="real-preview-placeholder">Gerar QR Code</div>
                )}
                <button
                  disabled={!selectedProduct || isLoadingQr}
                  type="button"
                  onClick={handleDownloadQrCode}
                >
                  Baixar QR Code
                </button>
              </div>
              <div className="real-preview-card real-preview-card--label">
                <h3>
                  Etiqueta - {selectedProduct?.name ?? 'Selecione um produto'}
                </h3>
                {labelPreviewUrl ? (
                  <img alt="Etiqueta real do produto" src={labelPreviewUrl} />
                ) : (
                  <div className="real-preview-placeholder">Gerar etiqueta</div>
                )}
                <button
                  disabled={!selectedProduct || isLoadingLabel}
                  type="button"
                  onClick={handleDownloadLabel}
                >
                  Baixar etiqueta
                </button>
                {selectedProduct ? (
                  <small className="real-preview-card__code">
                    Código: {formatProductCode(selectedProduct.id)}
                  </small>
                ) : null}
              </div>
            </div>
          </div>
        </Card>
        <Card title="Produtos para etiqueta" eyebrow="Catálogo real">
          {isLoadingProducts ? (
            <div className="stock-loading">Carregando produtos...</div>
          ) : products.length ? (
            <DataTable columns={columns} rows={products} />
          ) : (
            <div className="stock-empty">
              <h2>Nenhum produto ativo</h2>
              <p>Cadastre produtos ativos no Estoque para gerar etiquetas.</p>
            </div>
          )}
        </Card>
      </section>
    </div>
  )
}

export default LabelsPage
