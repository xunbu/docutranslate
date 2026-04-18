import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import legacy from '@vitejs/plugin-legacy'

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
    }),
    legacy({
      targets: ['Chrome >= 60', 'Safari >= 11', 'Firefox >= 60', 'Edge >= 79'],
      additionalLegacyPolyfills: ['regenerator-runtime/runtime']
    })
  ],
  build: {
    outDir: '../docutranslate/static',
    emptyOutDir: false,
    cssMinify: false
  }
})
