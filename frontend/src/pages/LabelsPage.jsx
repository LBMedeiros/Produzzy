import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ActionMenu from '../components/ui/ActionMenu'
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
  const [selectedOutputType, setSelectedOutputType] = useState('qr')
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
    setSelectedOutputType('qr')
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
    setSelectedOutputType('label')
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

  async function handleGenerateSelected() {
    if (selectedOutputType === 'label') {
      return handleGenerateLabel()
    }

    return handleGenerateQrCode()
  }

  async function handleDownloadSelected() {
    if (selectedOutputType === 'label') {
      return handleDownloadLabel()
    }

    return handleDownloadQrCode()
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

  function handleSelectProductForPreview(product) {
    handleSelectProduct(product.id)
  }

  function getProductActionItems(product) {
    return [
      {
        id: 'qr',
        label: 'Gerar QR Code',
        onClick: () => handleGenerateQrCode(product),
      },
      {
        id: 'label',
        label: 'Gerar etiqueta',
        onClick: () => handleGenerateLabel(product),
      },
    ]
  }

  const activePreviewUrl =
    selectedOutputType === 'label' ? labelPreviewUrl : qrPreviewUrl
  const activePreviewAlt =
    selectedOutputType === 'label'
      ? 'Etiqueta real do produto'
      : 'QR Code real do produto'
  const activePreviewTitle =
    selectedOutputType === 'label' ? 'Etiqueta' : 'QR Code'
  const hasActivePreview = Boolean(activePreviewUrl)
  const isGeneratingSelected =
    selectedOutputType === 'label' ? isLoadingLabel : isLoadingQr
  const activeDownloadLabel =
    selectedOutputType === 'label' ? 'Baixar etiqueta' : 'Baixar QR Code'

  const columns = [
    {
      key: 'name',
      label: 'Produto',
      render: (product) => (
        <button
          className="product-cell product-cell--button"
          type="button"
          onClick={() => handleSelectProductForPreview(product)}
        >
          <strong>{product.name}</strong>
          <span>Código: {formatProductCode(product.id)}</span>
        </button>
      ),
    },
    { key: 'category', label: 'Categoria' },
    {
      key: 'actions',
      label: 'Ações',
      render: (product) => (
        <div className="label-product-actions">
          <ActionMenu
            items={getProductActionItems(product)}
            label={`Ações de ${product.name}`}
          />
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

      <Card
        className="batch-export-card"
        title="Exportação em lote"
        eyebrow="Para impressão"
      >
        <div className="batch-export">
          <p>
            Gere arquivos de identificação para todos os produtos ativos.
          </p>
          <div className="batch-export__actions">
            <Button
              disabled={isLoadingQrCodesSheet || !products.length}
              onClick={handleDownloadQrCodesSheet}
              variant="secondary"
            >
              {isLoadingQrCodesSheet ? 'Baixando...' : 'Baixar QR Codes'}
            </Button>
            <Button
              disabled={isLoadingLabelsSheet || !products.length}
              onClick={handleDownloadLabelsSheet}
              variant="secondary"
            >
              {isLoadingLabelsSheet ? 'Baixando...' : 'Baixar etiquetas'}
            </Button>
          </div>
        </div>
      </Card>

      <section className="content-grid content-grid--label">
        <Card className="label-generator-card" title="Gerador individual">
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

            <div className="label-type-field">
              <span>Tipo</span>
              <div className="segmented-control" role="tablist" aria-label="Tipo de arquivo">
                <button
                  aria-selected={selectedOutputType === 'qr'}
                  className={selectedOutputType === 'qr' ? 'is-active' : ''}
                  role="tab"
                  type="button"
                  onClick={() => setSelectedOutputType('qr')}
                >
                  QR Code
                </button>
                <button
                  aria-selected={selectedOutputType === 'label'}
                  className={selectedOutputType === 'label' ? 'is-active' : ''}
                  role="tab"
                  type="button"
                  onClick={() => setSelectedOutputType('label')}
                >
                  Etiqueta
                </button>
              </div>
            </div>

            <Button
              className="label-generate-button"
              disabled={isGeneratingSelected || !selectedProduct}
              onClick={handleGenerateSelected}
              variant="secondary"
            >
              {isGeneratingSelected ? 'Gerando...' : 'Gerar'}
            </Button>

            <p className="label-preview-title">Prévia</p>

            <div className="real-preview-single">
              <div
                className={`real-preview-card ${
                  selectedOutputType === 'label'
                    ? 'real-preview-card--label'
                    : 'real-preview-card--qr'
                } ${hasActivePreview ? '' : 'real-preview-card--empty'}`}
              >
                <h3>
                  {activePreviewTitle} -{' '}
                  {selectedProduct?.name ?? 'Selecione um produto'}
                </h3>
                {hasActivePreview ? (
                  <img alt={activePreviewAlt} src={activePreviewUrl} />
                ) : (
                  <div className="real-preview-placeholder">
                    <strong>Nenhuma prévia ainda</strong>
                    <span>Gere um QR Code ou etiqueta para visualizar.</span>
                  </div>
                )}
                {hasActivePreview && selectedProduct ? (
                  <small className="real-preview-card__code">
                    Código: {formatProductCode(selectedProduct.id)}
                  </small>
                ) : null}
                {hasActivePreview ? (
                  <button
                    disabled={!selectedProduct || isGeneratingSelected}
                    type="button"
                    onClick={handleDownloadSelected}
                  >
                    {activeDownloadLabel}
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        </Card>
        <Card className="label-products-card" title="Produtos ativos" eyebrow="Catálogo">
          {isLoadingProducts ? (
            <div className="stock-loading">Carregando produtos...</div>
          ) : products.length ? (
            <div className="labels-product-table">
              <DataTable columns={columns} rows={products} />
            </div>
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
