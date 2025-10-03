import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    vuetify({
      autoImport: true,
      theme: {
        defaultTheme: 'dark'
      }
    })
  ],
  worker: {
    format: 'es'
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 3000,
    // Proxy API calls to the FastAPI backend during local development
    // This keeps cookies same-site and avoids CORS pitfalls
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  base: process.env.NODE_ENV === 'production' ? '/admin/' : '/',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: process.env.NODE_ENV !== 'production',
    target: 'es2020',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia'],
          vuetify: ['vuetify'],
          charts: ['chart.js', 'vue-chartjs'],
          icons: ['@mdi/js']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  },
  optimizeDeps: {
    include: [
      'monaco-editor',
      'vue',
      'vue-router',
      'pinia',
      'vuetify',
      'axios',
      '@mdi/js'
    ]
  },
  define: {
    // Monaco Editor needs these global variables
    global: 'globalThis',
    __VUE_OPTIONS_API__: false,
    __VUE_PROD_DEVTOOLS__: false
  },
  
  // Environment variable handling for production builds
  envPrefix: 'VITE_',
  
  // Performance optimizations
  esbuild: {
    target: 'es2020',
    drop: process.env.NODE_ENV === 'production' ? ['console', 'debugger'] : []
  }
})
