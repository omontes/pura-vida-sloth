import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      onwarn(warning, warn) {
        // Suppress vis-network source map warnings
        if (warning.code === 'SOURCEMAP_ERROR' && warning.message.includes('vis-network')) {
          return;
        }
        warn(warning);
      },
    },
  },
  // Disable CSS source maps to suppress vis-network warnings in dev
  css: {
    devSourcemap: false,
  },
})
