import {
  getReplenishmentQuantity,
  getReplenishmentStatus,
} from '../../lib/replenishment'

const numberFormatter = new Intl.NumberFormat('pt-BR')

// Bar colour per stock status (the rule itself lives in lib/replenishment):
// zerado → bad, abaixo do mínimo → warn, igual/acima → ok.
const BAR_TONES = {
  danger: 'bad',
  success: 'ok',
  warning: 'warn',
}

// "<b>8</b> de 30" plus a thin bar filled to min(100%, quantity / minimum).
// `showReplenish` adds "repor N" on the right when the item is below minimum.
function StockLevel({ className = '', minimum, quantity, showReplenish = false }) {
  const product = { minimum_quantity: minimum, quantity }
  const tone = BAR_TONES[getReplenishmentStatus(product).tone]
  const isEmpty = quantity === 0
  const ratio = minimum > 0 ? quantity / minimum : quantity > 0 ? 1 : 0
  const fillPercent = Math.min(Math.max(ratio, 0), 1) * 100
  const toReplenish = getReplenishmentQuantity(product)

  return (
    <div className={`stock-level ${className}`.trim()}>
      <div className="stock-level__text">
        <span>
          <b>{numberFormatter.format(quantity)}</b> de{' '}
          {numberFormatter.format(minimum)}
        </span>
        {showReplenish && toReplenish > 0 ? (
          <span>repor {numberFormatter.format(toReplenish)}</span>
        ) : null}
      </div>
      <div
        aria-hidden="true"
        className={`stock-level__bar stock-level__bar--${tone}${
          isEmpty ? ' stock-level__bar--empty' : ''
        }`}
      >
        <i style={{ width: `${fillPercent}%` }} />
      </div>
    </div>
  )
}

export default StockLevel
