import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The API proxy target is configurable so the same config works locally
// (backend on localhost:8000) and inside Docker (backend service on the compose network).
const apiTarget = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Listen on all interfaces so the dev server is reachable from outside the container.
    host: true,
    port: 5173,
    // File-change events do not cross the Windows/macOS -> Docker bind mount; poll instead.
    watch: process.env.CHOKIDAR_USEPOLLING === 'true' ? { usePolling: true } : undefined,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
