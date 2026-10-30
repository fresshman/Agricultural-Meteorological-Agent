import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// 1) Element Plus 基础样式
import 'element-plus/dist/index.css'
// 2) Element Plus 官方深色变量（依赖 html.dark 类）
import 'element-plus/theme-chalk/dark/css-vars.css'
// 3) 本项目设计 Token + reset
import './assets/styles/main.css'
// 4) Element Plus 变量桥接 + 组件级外观覆盖
import './assets/styles/theme.css'
// 5) Markdown 渲染样式
import './assets/styles/markdown.css'

import App from './App.vue'
import router from './router'
import { useThemeStore } from '@/stores/theme'
import { migrateIfNeeded } from '@/utils/storage'

const app = createApp(App)

// 全量注册 Element Plus 图标，业务组件可直接用 <Sunny /> 等
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

// 存储结构迁移必须早于任何 store 读取 localStorage
migrateIfNeeded()

// 主题必须在挂载前初始化，避免首帧闪白 / 闪黑
useThemeStore().init()

app.mount('#app')
