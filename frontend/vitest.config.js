import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 测试专用配置：与 vite.config.js 共享 '@' alias，但独立于生产构建。
// 仅开发 / CI 使用；vitest + jsdom 是 devDependencies，不进生产 bundle，
// Docker 构建阶段 npm install 会装上，但最终镜像只拷贝 dist/，运行时不携带。
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
    // 顺序 + 单线程执行：小体量套件下更稳定，也兼容并行 worker 临时目录受限的运行环境
    fileParallelism: false,
    poolOptions: { threads: { singleThread: true } }
  }
})
