// Cloudinary URLs get a transformation so the browser downloads a resized
// copy instead of the original photo. `fit: 'cover'` (thumbnails) crops to a
// square; `fit: 'contain'` (detail) only shrinks, keeping the whole photo.
export function productImageSrc(url, size, { fit = 'cover' } = {}) {
  if (!url || !url.includes('/image/upload/')) {
    return url
  }

  // Twice the CSS size for sharp images on high-density screens.
  const pixels = Math.round(size * 2)
  const transform =
    fit === 'contain'
      ? `c_limit,w_${pixels},h_${pixels},f_auto,q_auto`
      : `c_fill,g_auto,w_${pixels},h_${pixels},f_auto,q_auto`

  return url.replace('/image/upload/', `/image/upload/${transform}/`)
}
