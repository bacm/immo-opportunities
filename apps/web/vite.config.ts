import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    exclude: ['maplibre-gl'],
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:18000',
      '/tiles/v1/parcels': {
        target: 'http://127.0.0.1:13000',
        rewrite: (path) => path.replace('/tiles/v1/parcels', '/parcels').replace('.mvt', ''),
      },
      '/tiles/v1/buildings': {
        target: 'http://127.0.0.1:13000',
        rewrite: (path) => path.replace('/tiles/v1/buildings', '/buildings').replace('.mvt', ''),
      },
      '/tiles/v1/opportunities': {
        target: 'http://127.0.0.1:13000',
        rewrite: (path) => path.replace('/tiles/v1/opportunities', '/opportunities').replace('.mvt', ''),
      },
    },
  },
})
