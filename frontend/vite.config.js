import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: '/static/',
  plugins: [
    vue({
      template: {
        transformAssetUrls: {
          // Don't transform absolute URLs starting with /static/
          includeAbsolute: false
        }
      }
    })
  ],
  build: {
    outDir: '../docutranslate/static',
    emptyOutDir: false,
    cssMinify: false
  }
})
