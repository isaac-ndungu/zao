import { defineConfig } from 'vite'
import path from 'path'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@shared': path.resolve(__dirname, 'src/shared'),
      '@admin': path.resolve(__dirname, 'src/admin'),
      '@farmer': path.resolve(__dirname, 'src/farmer'),
      '@manager': path.resolve(__dirname, 'src/manager'),
      '@grader': path.resolve(__dirname, 'src/grader'),
      '@accountant': path.resolve(__dirname, 'src/accountant'),
      '@auditor': path.resolve(__dirname, 'src/auditor'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': process.env.VITE_API_PROXY || 'http://localhost:8000',
    },
    watch: {
      usePolling: true,
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: 'index.html',
        farmer: 'farmer/index.html',
      },
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'vendor-react'
            }
            if (id.includes('leaflet') || id.includes('leaflet-routing-machine')) {
              return 'vendor-leaflet'
            }
            if (id.includes('recharts') || id.includes('d3')) {
              return 'vendor-recharts'
            }
            if (id.includes('@tanstack')) {
              return 'vendor-query'
            }
            if (id.includes('date-fns') || id.includes('dayjs') || id.includes('moment')) {
              return 'vendor-date'
            }
            return 'vendor-misc'
          }
        },
      },
    },
    chunkSizeWarningLimit: 500,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.js'],
    include: ['src/**/*.{test,spec}.{js,jsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'xml', 'html'],
      include: ['src/**/*.{js,jsx}'],
      exclude: ['src/main.jsx', 'src/index.css', 'src/assets/**', '**/*.test.*', '**/*.spec.*'],
    },
  },
})
