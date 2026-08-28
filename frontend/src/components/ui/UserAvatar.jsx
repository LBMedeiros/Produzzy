import { getInitials } from '../../lib/formatters'

function UserAvatar({
  alt = '',
  className = '',
  fallback = 'US',
  name,
  src,
}) {
  return (
    <span className={`avatar ${className}`.trim()}>
      {src ? <img alt={alt} src={src} /> : getInitials(name, fallback)}
    </span>
  )
}

export default UserAvatar
