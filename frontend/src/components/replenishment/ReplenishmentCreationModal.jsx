import { useMemo, useState } from 'react'
import { getReplenishmentQuantity } from '../../lib/replenishment'
import Button from '../ui/Button'

function formatNumber(value) {
  return new Intl.NumberFormat('pt-BR').format(value ?? 0)
}

function getSuggestedQuantity(product) {
  return Math.max(getReplenishmentQuantity(product), 1)
}

function ReplenishmentCreationModal({
  error = '',
  isSaving = false,
  onClose,
  onSubmit,
  product,
}) {
  const suggestedQuantity = useMemo(
    () => getSuggestedQuantity(product),
    [product],
  )
  const [replenishmentType, setReplenishmentType] = useState('purchase')
  const [quantityNeeded, setQuantityNeeded] = useState(
    String(suggestedQuantity),
  )
  const [notes, setNotes] = useState('')
  const [validationError, setValidationError] = useState('')

  function handleSubmit(event) {
    event.preventDefault()

    const parsedQuantity = Number(quantityNeeded)

    if (!Number.isInteger(parsedQuantity) || parsedQuantity <= 0) {
      setValidationError('Informe uma quantidade prevista maior que zero.')
      return
    }

    setValidationError('')
    onSubmit({
      notes: notes.trim() || null,
      quantity_needed: parsedQuantity,
      type: replenishmentType,
    })
  }

  const suggestionLabel =
    product.quantity < product.minimum_quantity
      ? 'Necessário repor'
      : 'Sugestão inicial'

  return (
    <div className="modal-backdrop" role="presentation">
      <section
        aria-modal="true"
        className="workspace-modal stock-modal"
        role="dialog"
      >
        <div className="workspace-modal__header">
          <div>
            <span>Reposição</span>
            <h2>Criar necessidade de reposição</h2>
          </div>
          <button
            aria-label="Fechar modal"
            className="icon-button"
            disabled={isSaving}
            onClick={onClose}
            type="button"
          >
            x
          </button>
        </div>

        <div className="replenishment-modal__summary">
          <span>Produto selecionado</span>
          <strong>{product.name}</strong>
          <div className="replenishment-modal__metrics">
            <div>
              <span>Categoria</span>
              <strong>{product.category}</strong>
            </div>
            <div>
              <span>Estoque atual</span>
              <strong>{formatNumber(product.quantity)}</strong>
            </div>
            <div>
              <span>Mínimo cadastrado</span>
              <strong>{formatNumber(product.minimum_quantity)}</strong>
            </div>
            <div>
              <span>{suggestionLabel}</span>
              <strong>{formatNumber(suggestedQuantity)} un.</strong>
            </div>
          </div>
        </div>

        <form className="stock-form" onSubmit={handleSubmit}>
          <label>
            Tipo de reposição
            <select
              disabled={isSaving}
              onChange={(event) => setReplenishmentType(event.target.value)}
              value={replenishmentType}
            >
              <option value="purchase">Compra</option>
              <option value="production">Produção</option>
            </select>
          </label>
          <label>
            Quantidade prevista
            <input
              disabled={isSaving}
              min="1"
              onChange={(event) => setQuantityNeeded(event.target.value)}
              required
              type="number"
              value={quantityNeeded}
            />
          </label>
          <p className="stock-form__hint">
            Essa quantidade é apenas uma previsão e não altera o estoque
            automaticamente.
          </p>

          <label>
            Observação (opcional)
            <textarea
              disabled={isSaving}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Prazo, fornecedor ou orientação para a produção"
              value={notes}
            />
          </label>

          {validationError || error ? (
            <p className="form-error">{validationError || error}</p>
          ) : null}

          <div className="workspace-form__actions">
            <Button disabled={isSaving} type="submit">
              {isSaving ? 'Criando...' : 'Confirmar'}
            </Button>
            <Button
              disabled={isSaving}
              onClick={onClose}
              variant="secondary"
            >
              Voltar
            </Button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default ReplenishmentCreationModal
