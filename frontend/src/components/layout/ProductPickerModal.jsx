import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { needsReplenishment } from '../../lib/replenishment'
import { listAllProducts } from '../../services/productService'
import ModalPortal from '../ui/ModalPortal'
import StockLevel from '../ui/StockLevel'

const MODES = {
  movement: {
    eyebrow: 'Movimentar estoque',
    title: 'Escolha o produto',
  },
  replenishment: {
    eyebrow: 'Nova reposição',
    title: 'Qual produto repor?',
  },
}

function normalize(value) {
  return (value ?? '')
    .toString()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
}

// First step of the "+" quick actions: pick an active product, then the page
// opens its existing movement / replenishment form for it. For replenishment,
// products below the minimum come first.
function ProductPickerModal({ mode, onClose, onPick }) {
  const { activeWorkspace } = useWorkspace()
  const workspaceId = activeWorkspace?.id
  const [search, setSearch] = useState('')
  const searchRef = useRef(null)
  const copy = MODES[mode] ?? MODES.movement

  // Same query key as the Reposição page, so the list is shared from cache.
  const productsQuery = useQuery({
    queryKey: ['products', workspaceId, 'active'],
    queryFn: () => listAllProducts(workspaceId, { status: 'active' }),
    enabled: Boolean(workspaceId),
  })

  useEffect(() => {
    searchRef.current?.focus()

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const visibleProducts = useMemo(() => {
    const term = normalize(search.trim())
    const products = (productsQuery.data ?? []).filter(
      (product) =>
        !term ||
        normalize(product.name).includes(term) ||
        normalize(product.category).includes(term) ||
        String(product.id) === term,
    )

    if (mode !== 'replenishment') {
      return products
    }

    return [...products].sort(
      (a, b) => Number(needsReplenishment(b)) - Number(needsReplenishment(a)),
    )
  }, [mode, productsQuery.data, search])

  return (
    <ModalPortal>
      <div
        className="modal-backdrop"
        role="presentation"
        onClick={(event) => {
          if (event.target === event.currentTarget) {
            onClose()
          }
        }}
      >
        <section
          aria-labelledby="product-picker-title"
          aria-modal="true"
          className="workspace-modal product-picker"
          role="dialog"
        >
          <div className="workspace-modal__header">
            <div>
              <span>{copy.eyebrow}</span>
              <h2 id="product-picker-title">{copy.title}</h2>
            </div>
            <button
              aria-label="Fechar"
              className="icon-button"
              type="button"
              onClick={onClose}
            >
              x
            </button>
          </div>

          <input
            aria-label="Buscar produto"
            className="product-picker__search"
            placeholder="Buscar por nome, categoria ou ID"
            ref={searchRef}
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />

          {productsQuery.isLoading ? (
            <p className="product-picker__state">Carregando produtos...</p>
          ) : productsQuery.error ? (
            <p className="form-error">Não foi possível carregar os produtos.</p>
          ) : visibleProducts.length ? (
            <ul className="product-picker__list">
              {visibleProducts.map((product) => (
                <li key={product.id}>
                  <button
                    className="product-picker__item"
                    type="button"
                    onClick={() => onPick(product)}
                  >
                    <span className="product-picker__name">
                      <strong>{product.name}</strong>
                      <span>{product.category}</span>
                    </span>
                    <StockLevel
                      minimum={product.minimum_quantity}
                      quantity={product.quantity}
                      showReplenish={mode === 'replenishment'}
                    />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="product-picker__state">
              {search.trim()
                ? 'Nenhum produto encontrado.'
                : 'Nenhum produto ativo neste workspace.'}
            </p>
          )}
        </section>
      </div>
    </ModalPortal>
  )
}

export default ProductPickerModal
