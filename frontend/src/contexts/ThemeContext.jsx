/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'

const ThemeContext = createContext(null)
const THEME_STORAGE_KEY = 'produzzy_theme_preference'
const THEME_OPTIONS = new Set(['system', 'light', 'dark'])

function getStoredTheme() {
  const storedTheme = localStorage.getItem(THEME_STORAGE_KEY)

  return THEME_OPTIONS.has(storedTheme) ? storedTheme : 'system'
}

function getSystemTheme() {
  if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }

  return 'light'
}

export function ThemeProvider({ children }) {
  const [themePreference, setThemePreference] = useState(getStoredTheme)
  const [systemTheme, setSystemTheme] = useState(getSystemTheme)
  const resolvedTheme =
    themePreference === 'system' ? systemTheme : themePreference

  useEffect(() => {
    const mediaQuery = window.matchMedia?.('(prefers-color-scheme: dark)')

    if (!mediaQuery) {
      return undefined
    }

    function handleSystemThemeChange(event) {
      setSystemTheme(event.matches ? 'dark' : 'light')
    }

    mediaQuery.addEventListener('change', handleSystemThemeChange)

    return () => {
      mediaQuery.removeEventListener('change', handleSystemThemeChange)
    }
  }, [])

  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, themePreference)
  }, [themePreference])

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme
    document.documentElement.style.colorScheme = resolvedTheme
  }, [resolvedTheme])

  const value = useMemo(
    () => ({
      resolvedTheme,
      setThemePreference,
      themePreference,
    }),
    [resolvedTheme, themePreference],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)

  if (!context) {
    throw new Error('useTheme deve ser usado dentro de ThemeProvider.')
  }

  return context
}
