function IconBase({ children }) {
  return (
    <svg
      aria-hidden="true"
      className="sidebar-icon"
      fill="none"
      focusable="false"
      viewBox="0 0 24 24"
    >
      {children}
    </svg>
  )
}

export function DashboardIcon() {
  return (
    <IconBase>
      <path d="M4 5h7v6H4zM13 5h7v4h-7zM4 13h7v6H4zM13 11h7v8h-7z" />
    </IconBase>
  )
}

export function StockIcon() {
  return (
    <IconBase>
      <path d="M4 8l8-4 8 4-8 4z" />
      <path d="M4 8v8l8 4 8-4V8" />
      <path d="M12 12v8" />
    </IconBase>
  )
}

export function ProductionIcon() {
  return (
    <IconBase>
      <path d="M5 5h4v14H5zM11 5h4v9h-4zM17 5h2v11h-2z" />
    </IconBase>
  )
}

export function LabelsIcon() {
  return (
    <IconBase>
      <path d="M5 5h5v5H5zM14 5h5v5h-5zM5 14h5v5H5z" />
      <path d="M14 14h2v2h-2zM17 17h2v2h-2zM18 14h1v1h-1zM14 18h1v1h-1z" />
    </IconBase>
  )
}

export function SettingsIcon() {
  return (
    <IconBase>
      <path d="M12 8.5a3.5 3.5 0 100 7 3.5 3.5 0 000-7z" />
      <path d="M12 3v3M12 18v3M4.2 7.5l2.6 1.5M17.2 15l2.6 1.5M19.8 7.5l-2.6 1.5M6.8 15l-2.6 1.5" />
    </IconBase>
  )
}

export function ChevronIcon({ direction }) {
  return (
    <svg
      aria-hidden="true"
      className={`chevron-icon chevron-icon--${direction}`}
      fill="none"
      focusable="false"
      viewBox="0 0 24 24"
    >
      <path d="M14.5 6.5L9 12l5.5 5.5" />
    </svg>
  )
}
