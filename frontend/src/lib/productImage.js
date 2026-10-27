// Cloudinary URLs get a transformation so lists download a small square
// instead of the original photo.
export function productImageSrc(url, size) {
  if (!url || !url.includes('/image/upload/')) {
    return url
  }

  // Twice the CSS size for sharp thumbnails on high-density screens.
  const pixels = Math.round(size * 2)

  return url.replace(
    '/image/upload/',
    `/image/upload/c_fill,g_auto,w_${pixels},h_${pixels},f_auto,q_auto/`,
  )
}
