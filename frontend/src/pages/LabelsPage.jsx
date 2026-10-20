import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Button from '../components/ui/Button'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { usePagination } from '../lib/pagination'
import { getPrintSheet } from '../services/labelService'
import { listAllProducts } from '../services/productService'

// The scanner pulls in the ZXing decoder, so it loads only when first opened.
const QrScannerModal = lazy(() => import('../components/labels/QrScannerModal'))

// Product picker shows at most this many rows per page.
const LABEL_PRODUCTS_PAGE_SIZE = 10
const MAX_LABELS = 120
const MAX_COPIES = 20
const PREVIEW_DEBOUNCE_MS = 350

function normalize(value) {
  return (value ?? '')
    .toString()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
}

function getFriendlyError(error) {
  if (error?.status === 403) {
    return 'Você não tem permissão para gerar etiquetas neste workspace.'
  }

  if (error?.status === 0) {
    return 'Não foi possível conectar ao servidor.'
  }

  return error?.message ?? 'Não foi possível gerar as etiquetas.'
}

function pluralize(count, singular, plural) {
  return `${count} ${count === 1 ? singular : plural}`
}

function getValidId(value) {
  const numericId = Number(value)

  return Number.isInteger(numericId) && numericId > 0 ? numericId : null
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
// Prints the real sheet PNG: pages are A4 stacked, so at 210mm wide the
// browser breaks pages exactly at each 297mm.
function printSheetImage(url) {
  const iframe = document.createElement('iframe')
  iframe.setAttribute('aria-hidden', 'true')
  iframe.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0'
  iframe.srcdoc = `<!doctype html><html><head><title>Etiquetas Produzzy</title><style>@page{size:A4;margin:0}html,body{margin:0}img{display:block;width:210mm}</style></head><body><img src="${url}" alt=""></body></html>`
  iframe.onload = () => {
    const image = iframe.contentDocument?.querySelector('img')
    const run = () => {
      iframe.contentWindow?.focus()
      iframe.contentWindow?.print()
      window.setTimeout(() => iframe.remove(), 60000)
    }

    if (image && !image.complete) {
      image.onload = run
    } else {
      run()
    }
  }
  document.body.appendChild(iframe)
}

function ScanIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3" />
      <path d="M7 12h10" />
    </svg>
  )
}

function SearchIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  )
}

function LabelsPage({ onNavigate }) {
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id
  const [products, setProducts] = useState([])
  const [isLoadingProducts, setIsLoadingProducts] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState([])
  const [copies, setCopies] = useState(1)
  const [preview, setPreview] = useState({ pages: 0, url: '' })
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [scannerOpen, setScannerOpen] = useState(false)
  const [error, setError] = useState('')
  const previewUrlRef = useRef('')
  const listRef = useRef(null)

  const loadProducts = useCallback(async () => {
    const numericWorkspaceId = getValidId(workspaceId)

    if (!numericWorkspaceId) {
      setProducts([])
      setIsLoadingProducts(false)
      return
    }

    setIsLoadingProducts(true)
    setError('')

    try {
      const activeProducts = await listAllProducts(numericWorkspaceId, { status: 'active' })
      setProducts(activeProducts)
      setSelectedIds((current) =>
        current.filter((id) => activeProducts.some((product) => product.id === id)),
      )
    } catch (loadError) {
      setError(getFriendlyError(loadError))
    } finally {
      setIsLoadingProducts(false)
    }
  }, [workspaceId])

  useEffect(() => {
    const timeoutId = window.setTimeout(loadProducts, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadProducts])

  const visibleProducts = useMemo(() => {
    const term = normalize(search.trim())

    return term
      ? products.filter(
          (product) =>
            normalize(product.name).includes(term) ||
            normalize(product.category).includes(term) ||
            String(product.id) === term,
        )
      : products
  }, [products, search])

  const pagination = usePagination(
    visibleProducts,
    LABEL_PRODUCTS_PAGE_SIZE,
    `${workspaceId}-${search.trim()}`,
    listRef,
  )

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds])
  // Sheet keeps the order of the product list, not the click order.
  const orderedSelection = useMemo(
    () => products.filter((product) => selectedSet.has(product.id)).map((product) => product.id),
    [products, selectedSet],
  )
  const labelCount = orderedSelection.length * copies
  const isOverLimit = labelCount > MAX_LABELS
  const allVisibleSelected =
    visibleProducts.length > 0 && visibleProducts.every((product) => selectedSet.has(product.id))

  // Live preview: the real sheet from the API (QR Code with the logo + barcode).
  useEffect(() => {
    const numericWorkspaceId = getValidId(workspaceId)

    // Nothing to generate: the view hides the (stale) preview on its own.
    if (!numericWorkspaceId || !orderedSelection.length || isOverLimit) {
      return undefined
    }

    let cancelled = false
    const timeoutId = window.setTimeout(async () => {
      setIsLoadingPreview(true)
      setError('')

      try {
        const blob = await getPrintSheet(numericWorkspaceId, {
          copies,
          productIds: orderedSelection,
        })
        if (cancelled) {
          return
        }

        const url = URL.createObjectURL(blob)
        const image = new Image()
        image.onload = () => {
          if (cancelled) {
            URL.revokeObjectURL(url)
            return
          }

          if (previewUrlRef.current) {
            URL.revokeObjectURL(previewUrlRef.current)
          }
          previewUrlRef.current = url
          setPreview({
            pages: Math.max(1, Math.round(image.naturalHeight / (image.naturalWidth * (297 / 210)))),
            url,
          })
          setIsLoadingPreview(false)
        }
        image.src = url
      } catch (previewError) {
        if (!cancelled) {
          setError(getFriendlyError(previewError))
          setIsLoadingPreview(false)
        }
      }
    }, PREVIEW_DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
    }
  }, [copies, isOverLimit, orderedSelection, workspaceId])

  useEffect(
    () => () => {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current)
      }
    },
    [],
  )

  function toggleProduct(productId) {
    setSelectedIds((current) =>
      current.includes(productId)
        ? current.filter((id) => id !== productId)
        : [...current, productId],
    )
  }

  function toggleAllVisible() {
    const visibleIds = visibleProducts.map((product) => product.id)

    setSelectedIds((current) =>
      allVisibleSelected
        ? current.filter((id) => !visibleIds.includes(id))
        : [...new Set([...current, ...visibleIds])],
    )
  }

  async function handleDownloadPdf() {
    const numericWorkspaceId = getValidId(workspaceId)

    if (!numericWorkspaceId || !orderedSelection.length || isOverLimit) {
      return
    }

    setIsDownloading(true)
    setError('')

    try {
      const blob = await getPrintSheet(numericWorkspaceId, {
        copies,
        format: 'pdf',
        productIds: orderedSelection,
      })
      downloadBlob(blob, 'etiquetas-produzzy.pdf')
    } catch (downloadError) {
      setError(getFriendlyError(downloadError))
    } finally {
      setIsDownloading(false)
    }
  }

  const closeScanner = useCallback(() => setScannerOpen(false), [])

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

      setScannerOpen(false)
      onNavigate?.('stock', {
        type: 'product-movement',
        workspaceId: numericWorkspaceId,
        productId: productRef.productId,
      })

      return null
    },
    [onNavigate, workspaceId],
  )

  const canPrint = Boolean(orderedSelection.length) && !isOverLimit
  const printLabel = canPrint ? `Imprimir ${pluralize(labelCount, 'etiqueta', 'etiquetas')}` : 'Imprimir'

  return (
    <div className="page-stack">
      <PageHeader
        actions={
          <>
            <Button
              disabled={!canPrint || isDownloading}
              onClick={handleDownloadPdf}
              variant="secondary"
            >
              {isDownloading ? 'Gerando PDF...' : 'Baixar PDF'}
            </Button>
            <Button
              disabled={!canPrint || !preview.url || isLoadingPreview}
              onClick={() => printSheetImage(preview.url)}
            >
              {printLabel}
            </Button>
          </>
        }
        subtitle="Etiquetas com QR Code e código de barras para imprimir e escanear"
        title="Etiquetas"
      />

      <button className="scan-button" onClick={() => setScannerOpen(true)} type="button">
        <span className="scan-button__icon">
          <ScanIcon />
        </span>
        <span className="scan-button__text">
          <strong>Escanear etiqueta</strong>
          <span>Movimente um produto pela câmera</span>
        </span>
        <span aria-hidden="true" className="scan-button__go">
          ›
        </span>
      </button>

      {error ? <p className="stock-feedback stock-feedback--error">{error}</p> : null}

      <div className="labels-layout">
        <section aria-labelledby="labels-products-title" className="dashboard-panel">
          <div className="dashboard-panel__head">
            <h2 id="labels-products-title">
              Produtos
              <span className="dashboard-panel__count">
                {pluralize(orderedSelection.length, 'selecionado', 'selecionados')}
              </span>
            </h2>
            {visibleProducts.length ? (
              <button className="dashboard-panel__link" onClick={toggleAllVisible} type="button">
                {allVisibleSelected ? 'Limpar seleção' : 'Selecionar todos'}
              </button>
            ) : null}
          </div>

          <label className="labels-search">
            <SearchIcon />
            <input
              aria-label="Buscar produto"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar produto"
              type="search"
              value={search}
            />
          </label>

          {isLoadingProducts ? (
            <p className="labels-state">Carregando produtos...</p>
          ) : visibleProducts.length ? (
            <>
              <ul className="label-pick" ref={listRef}>
                {pagination.pageItems.map((product) => {
                  const isSelected = selectedSet.has(product.id)

                  return (
                    <li key={product.id}>
                      <button
                        aria-checked={isSelected}
                        className={`label-pick__item${isSelected ? ' is-selected' : ''}`}
                        onClick={() => toggleProduct(product.id)}
                        role="checkbox"
                        type="button"
                      >
                        <span aria-hidden="true" className="label-pick__check">
                          {isSelected ? '✓' : ''}
                        </span>
                        <span className="label-pick__name">
                          <strong>{product.name}</strong>
                          <span>
                            {product.category} · ID {product.id}
                          </span>
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
              <div className="labels-pagination">
                <Pagination
                  itemLabel="produtos"
                  onPageChange={(page) => pagination.setPage(page, { scroll: false })}
                  page={pagination.page}
                  pageSize={pagination.pageSize}
                  totalItems={pagination.totalItems}
                />
              </div>
            </>
          ) : (
            <p className="labels-state">
              {search.trim()
                ? 'Nenhum produto encontrado.'
                : 'Cadastre produtos ativos no Estoque para gerar etiquetas.'}
            </p>
          )}

        </section>

        <section aria-labelledby="labels-preview-title" className="dashboard-panel">
          <div className="dashboard-panel__head">
            <h2 id="labels-preview-title">Prévia da folha</h2>
            <span className="dashboard-panel__count">A4 · 21 por folha</span>
          </div>
          <div aria-label="Opções da etiqueta" className="label-options">
            <span className="label-options__hint">QR Code e código de barras na mesma etiqueta</span>
            <span className="label-copies">
              <button
                aria-label="Menos cópias"
                disabled={copies <= 1}
                onClick={() => setCopies((value) => Math.max(1, value - 1))}
                type="button"
              >
                −
              </button>
              <span aria-live="polite">{pluralize(copies, 'cópia', 'cópias')}</span>
              <button
                aria-label="Mais cópias"
                disabled={copies >= MAX_COPIES}
                onClick={() => setCopies((value) => Math.min(MAX_COPIES, value + 1))}
                type="button"
              >
                +
              </button>
            </span>
          </div>
          <div className="sheet-preview">
            {isOverLimit ? (
              <p className="labels-state">
                São {labelCount} etiquetas — o máximo por vez é {MAX_LABELS}. Selecione menos
                produtos ou cópias.
              </p>
            ) : !orderedSelection.length ? (
              <p className="labels-state">
                Selecione produtos ao lado para ver a folha que será impressa.
              </p>
            ) : preview.url ? (
              <>
                <div className={`sheet-preview__paper${isLoadingPreview ? ' is-loading' : ''}`}>
                  <img alt="Prévia real da folha de etiquetas" src={preview.url} />
                </div>
                <div className="sheet-preview__meta">
                  <span>
                    {pluralize(labelCount, 'etiqueta', 'etiquetas')} ·{' '}
                    {pluralize(preview.pages, 'folha', 'folhas')}
                  </span>
                  <span>Escaneie para movimentar</span>
                </div>
              </>
            ) : (
              <p className="labels-state">Gerando prévia...</p>
            )}
          </div>
        </section>
      </div>

      {scannerOpen ? (
        <Suspense fallback={null}>
          <QrScannerModal mode="both" onClose={closeScanner} onDetect={handleScanDetected} />
        </Suspense>
      ) : null}
    </div>
  )
}

export default LabelsPage
