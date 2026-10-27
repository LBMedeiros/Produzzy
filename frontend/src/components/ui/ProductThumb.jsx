import { productImageSrc } from '../../lib/productImage'

// Product photo, or its initial when there is none.
function ProductThumb({ className = '', name, size = 40, src }) {
  const style = { height: size, width: size }

  if (src) {
    return (
      <img
        alt=""
        className={`product-thumb ${className}`.trim()}
        decoding="async"
        loading="lazy"
        src={productImageSrc(src, size)}
        style={style}
      />
    )
  }

  return (
    <span
      aria-hidden="true"
      className={`product-thumb product-thumb--empty ${className}`.trim()}
      style={{ ...style, fontSize: Math.round(size * 0.4) }}
    >
      {(name ?? '?').trim().charAt(0).toUpperCase() || '?'}
    </span>
  )
}

export default ProductThumb
