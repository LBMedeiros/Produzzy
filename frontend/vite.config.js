import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          // React changes far less often than app code; keep it in its own
          // long-cached chunk so an app deploy doesn't re-download it.
          if (
            id.includes('node_modules/react-dom') ||
            id.includes('node_modules/react/') ||
            id.includes('node_modules/react-router') ||
            id.includes('node_modules/@tanstack') ||
            id.includes('node_modules/scheduler')
          ) {
            return 'vendor-react'
          }
        },
      },
    },
  },
})
