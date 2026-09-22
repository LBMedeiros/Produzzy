import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import ActionMenu from '../components/ui/ActionMenu'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import DataTable from '../components/ui/DataTable'
import SelectMenu from '../components/ui/SelectMenu'
import { useWorkspace } from '../contexts/WorkspaceContext'

// The scanner pulls in the ZXing decoder, so it loads only when first opened.
const QrScannerModal = lazy(() => import('../components/labels/QrScannerModal'))

// QR-code glyph (three finder squares + modules) for the QR scan action.
function QrIcon() {
  return (
    <svg
      aria-hidden="true"
      fill="currentColor"
      fillRule="evenodd"
      height="16"
      viewBox="0 0 24 24"
      width="16"
    >
      <path d="M3 3h8v8H3V3zm2 2v4h4V5H5z" />
      <path d="M13 3h8v8h-8V3zm2 2v4h4V5h-4z" />
      <path d="M3 13h8v8H3v-8zm2 2v4h4v-4H5z" />
      <path d="M13 13h3v3h-3zM18 13h3v2h-3zM13 18h3v3h-3zM18 17h3v4h-2v-2h-1z" />
    </svg>
  )
}

// Vertical bars for the barcode scan action.
function BarcodeIcon() {
  return (
    <svg
      aria-hidden="true"
      fill="currentColor"
      height="16"
      viewBox="0 0 24 24"
      width="16"
    >
      <path d="M3 5h2v14H3zM7 5h1v14H7zM10 5h2v14h-2zM14 5h1v14h-1zM16 5h3v14h-3zM21 5h1v14h-1z" />
    </svg>
  )
}

// Line illustration: a phone reading the QR/barcode on a package.
function ScanIllustration() {
  return (
    <svg fill="none" role="img" viewBox="0 0 220 150" aria-hidden="true">
      <rect
        height="78"
        rx="8"
        stroke="currentColor"
        strokeWidth="2.5"
        width="80"
        x="26"
        y="46"
      />
      <path d="M26 70h80" opacity="0.6" stroke="currentColor" strokeWidth="2" />
      <path d="M66 46v24" opacity="0.6" stroke="currentColor" strokeWidth="2" />
      <g fill="var(--blue)">
        <rect height="11" rx="1.5" width="11" x="43" y="83" />
        <rect height="11" rx="1.5" width="11" x="58" y="83" />
        <rect height="11" rx="1.5" width="11" x="43" y="98" />
        <rect height="6" rx="1" width="6" x="61" y="100" />
        <rect height="6" rx="1" width="6" x="73" y="87" />
        <rect height="8" rx="1" width="8" x="73" y="99" />
      </g>
      <rect
        fill="var(--card)"
        height="104"
        rx="12"
        stroke="currentColor"
        strokeWidth="2.5"
        width="60"
        x="130"
        y="34"
      />
      <rect
        height="72"
        opacity="0.5"
        rx="6"
        stroke="currentColor"
        strokeWidth="1.5"
        width="44"
        x="138"
        y="46"
      />
      <g stroke="var(--blue)" strokeLinecap="round" strokeWidth="2.5">
        <path d="M147 62v-7h7" />
        <path d="M173 62v-7h-7" />
        <path d="M147 102v7h7" />
        <path d="M173 102v7h-7" />
      </g>
      <path
        d="M130 74 106 66M130 92 106 100"
        opacity="0.85"
        stroke="var(--blue)"
        strokeDasharray="4 5"
        strokeWidth="2"
      />
    </svg>
  )
}

// Line illustration: a printer producing a sheet of QR/label tags.
function PrintIllustration() {
  return (
    <svg fill="none" role="img" viewBox="0 0 220 150" aria-hidden="true">
      <rect
        fill="var(--card)"
        height="70"
        rx="6"
        stroke="currentColor"
        strokeWidth="2.5"
        width="88"
        x="66"
        y="18"
      />
      <g fill="var(--blue)">
        <rect height="14" rx="2" width="14" x="78" y="30" />
        <rect height="14" rx="2" width="14" x="103" y="30" />
        <rect height="14" rx="2" width="14" x="128" y="30" />
        <rect height="14" rx="2" width="14" x="78" y="54" />
        <rect height="14" rx="2" width="14" x="103" y="54" />
        <rect height="14" rx="2" width="14" x="128" y="54" />
      </g>
      <path
        d="M46 96h128a8 8 0 0 1 8 8v22a8 8 0 0 1-8 8H46a8 8 0 0 1-8-8v-22a8 8 0 0 1 8-8Z"
        fill="var(--card)"
        stroke="currentColor"
        strokeWidth="2.5"
      />
      <rect
        fill="var(--card)"
        height="10"
        rx="3"
        stroke="currentColor"
        strokeWidth="2"
        width="88"
        x="66"
        y="91"
      />
      <path
        d="M52 120h18"
        opacity="0.6"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="2"
      />
      <circle cx="162" cy="119" fill="var(--blue)" r="3.5" />
    </svg>
  )
}
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

/**
 * Turns a scanned value into a product reference. Handles both shapes the app
 * itself generates: the QR Code encodes the product's API URL
 * (`.../workspaces/{workspaceId}/products/{productId}`) and the barcode is the
 * Code128 of the zero-padded product id (e.g. `000000002`). Returns
 * `{ workspaceId, productId }` (workspaceId is `null` for barcodes, which carry
 * no workspace) or `null` when the value is not a Produzzy code.
 */
function parseScannedProductRef(rawValue) {
  const value = String(rawValue ?? '').trim()

  if (!value) {
    return null
  }

  const urlMatch = value.match(/workspaces\/(\d+)\/products\/(\d+)/i)

  if (urlMatch) {
    return {
      workspaceId: Number(urlMatch[1]),
      productId: Number(urlMatch[2]),
    }
  }

  const digitsMatch = value.match(/^0*(\d{1,9})$/)

  if (digitsMatch) {
    const productId = Number(digitsMatch[1])

    if (Number.isInteger(productId) && productId > 0) {
      return { workspaceId: null, productId }
    }
  }

  return null
}

function LabelsPage({ onNavigate }) {
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id
  const [scannerMode, setScannerMode] = useState(null)
  const [utilityTab, setUtilityTab] = useState('scan')
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

  const closeScanner = useCallback(() => {
    setScannerMode(null)
  }, [])

  const handleScanDetected = useCallback(
    (rawValue) => {
      const productRef = parseScannedProductRef(rawValue)

      if (!productRef) {
        return 'Código não reconhecido. Use um QR Code ou código de barras gerado pelo Produzzy.'
      }

      const numericWorkspaceId = getValidId(workspaceId)

      if (productRef.workspaceId && productRef.workspaceId !== numericWorkspaceId) {
        return 'Este código pertence a outro workspace.'
      }

      setScannerMode(null)
      setError('')
      setSuccessMessage('')
      onNavigate?.('stock', {
        type: 'product-movement',
        workspaceId: numericWorkspaceId,
        productId: productRef.productId,
      })

      return null
    },
    [onNavigate, workspaceId],
  )

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

      <section className="content-grid labels-top-grid">
        <Card
          className="labels-actions-card"
          title="Escanear e imprimir"
          eyebrow="Ações de código"
        >
          <div className="labels-actions">
            <div
              className="segmented-control"
              role="tablist"
              aria-label="Ação de código"
            >
              <button
                aria-selected={utilityTab === 'scan'}
                className={utilityTab === 'scan' ? 'is-active' : ''}
                role="tab"
                type="button"
                onClick={() => setUtilityTab('scan')}
              >
                Escanear
              </button>
              <button
                aria-selected={utilityTab === 'print'}
                className={utilityTab === 'print' ? 'is-active' : ''}
                role="tab"
                type="button"
                onClick={() => setUtilityTab('print')}
              >
                Imprimir
              </button>
            </div>

            <div className="labels-actions__art">
              {utilityTab === 'scan' ? (
                <ScanIllustration />
              ) : (
                <PrintIllustration />
              )}
            </div>

            {utilityTab === 'scan' ? (
              <div className="labels-actions__panel">
                <p>
                  Leia o código de um produto para movimentar o estoque
                  (entrada/saída) direto por aqui.
                </p>
                <div className="labels-actions__buttons">
                  <Button icon={<QrIcon />} onClick={() => setScannerMode('qr')}>
                    QR Code
                  </Button>
                  <Button
                    icon={<BarcodeIcon />}
                    onClick={() => setScannerMode('barcode')}
                  >
                    Código de barras
                  </Button>
                </div>
              </div>
            ) : (
              <div className="labels-actions__panel">
                <p>Gere arquivos de identificação para todos os produtos ativos.</p>
                <div className="labels-actions__buttons">
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
            )}
          </div>
        </Card>

        <Card className="label-generator-card" title="Gerador individual">
          <div className="label-preview-stack">
            <div className="stock-form stock-form--select">
              <span>Produto</span>
              <SelectMenu
                ariaLabel="Produto"
                disabled={isLoadingProducts || !products.length}
                onChange={handleSelectProduct}
                options={
                  products.length
                    ? products.map((product) => ({
                        label: product.name,
                        value: product.id,
                      }))
                    : [{ label: 'Nenhum produto ativo', value: '' }]
                }
                value={selectedProductId}
              />
            </div>

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
      </section>

      <Card
        className="label-products-card"
        title="Produtos ativos"
        eyebrow="Catálogo"
      >
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

      {scannerMode ? (
        <Suspense fallback={null}>
          <QrScannerModal
            mode={scannerMode}
            onClose={closeScanner}
            onDetect={handleScanDetected}
          />
        </Suspense>
      ) : null}
    </div>
  )
}

export default LabelsPage
