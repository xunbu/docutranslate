import { defineConfig } from 'vite'

export default defineConfig({
  base: '/static/',
  build: {
    outDir: '../docutranslate/static',
    emptyOutDir: false,
    cssMinify: false
  }
})
