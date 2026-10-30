# 农业气象智能体 · AgriMet Agent

[![ModelScope](https://img.shields.io/badge/ModelScope-在线体验-6C4BF6)](https://www.modelscope.cn/studios/ennmmmmm/Agricultural-Meteorological-Agent)
[![Vue](https://img.shields.io/badge/Vue-3.4-42b883)](https://vuejs.org)
[![Element Plus](https://img.shields.io/badge/Element%20Plus-2.6-409eff)](https://element-plus.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

**看天种地，有问必答** — 一个结合气象数据与农业知识的智能农事决策助手。前端为产品级 SPA（设计系统 + 深色模式 + 响应式），后端为 FastAPI 提供 REST / SSE 能力。

> **在线体验（魔搭创空间）**：https://www.modelscope.cn/studios/ennmmmmm/Agricultural-Meteorological-Agent
>
> 使用魔搭账号登录后，对话、地块与农事记录会保存到你的账户目录下。

> 创空间部署：**单容器 Docker，监听 `7860` 端口**（nginx 静态托管前端 + 反代后端 uvicorn）。

---

## 功能概览（5 个页面）

| 路由 | 页面 | 核心能力 |
|------|------|----------|
| `/dashboard` | 总览 | 位置气象概览、温/湿/适宜度/地块指标卡、7 天预报图、今日待办、最新预警、快捷提问 |
| `/chat` | 智能问答 | 多轮对话、SSE 流式输出、会话管理、即时天气（`nowcast`）、回答依据与置信度、点赞/点踩反馈、语音输入、按用户类型与作物个性化 |
| `/farm` | 我的农场 | 地块 CRUD、基于近 72h 气象 + 灌溉记录的**田间指标推演**（健康/水分/生长）、农事操作（灌溉/施肥/收获）、详情抽屉与 72h 气象曲线 |
| `/warning` | 预警中心 | 灾害 / 病虫害预警分析与按日期维度（今天/明天/未来 7 天）筛选、防御/应急/防治措施、自动刷新、内嵌预报图 |
| `/calendar` | 农事日历 | 7 类农事操作 × 7 天**适宜度矩阵**（四色分级），单元格可点开查看「前端按日推演」与「后端 72h 综合评估」对比，一键生成方案 |

通用能力：深浅主题（自动/浅/深三态，记忆偏好）、375 / 768 / 1024 / 1440 四档响应式、空状态 / 骨架屏、统一 Toast、`404` 兜底页。

---

## 技术架构

```
┌──────────────────────────────────────────────────────────────┐
│  前端 (Vue 3.4 + Vite 5 + Element Plus 2.6 + Pinia + ECharts) │
│  SPA，构建产物由 nginx 静态托管（:7860）                       │
│  ├─ 设计系统：main.css (Token) + theme.css (EP 桥接/深色镜像)  │
│  ├─ 流式：fetch + ReadableStream 消费 SSE（非 EventSource）    │
│  └─ Markdown：marked ^12 + dompurify ^3（v-html 必经净化）     │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP / SSE  (nginx 反代 /api → :8000)
┌───────────────────────────┴──────────────────────────────────┐
│  后端 (FastAPI + Uvicorn :8000)                                │
│  ├─ /api/chat(SSE)  智能问答（nowcast/token/done/error 事件）  │
│  ├─ /api/chat/feedback(+stats)  回答反馈与统计                │
│  ├─ /api/weather     气象数据                                 │
│  ├─ /api/location    地理编码 + 行政区划                      │
│  ├─ /api/farm        农场 / 地块 / 农事操作 / 预警            │
│  └─ /api/warning     灾害 / 病虫害 / 适宜度                   │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────┴──────────────────────────────────┐
│  业务层 (backend/src 或 src/)                                  │
│  ├─ agents/    智能体编排 (AgriculturalWeatherAgent)          │
│  ├─ core/      规则引擎 + 记忆管理                            │
│  ├─ data/      气象处理 + 向量库 (FAISS)                      │
│  ├─ models/    Pydantic 数据模型                              │
│  ├─ tools/     35+ 工具类                                     │
│  └─ utils/     LLM/Embedding 客户端 + 地图                    │
└──────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端框架 | Vue 3.4 + Vite 5 | 组合式 API，`<script setup>` |
| UI 组件 | Element Plus 2.6 + @element-plus/icons-vue | 主色桥接为「耕作绿」`#2E8B5B` |
| 状态管理 | Pinia 2 | `theme / weather / location / chat / farm / warning` 六大 store |
| 图表 | ECharts 5 + vue-echarts 6 | 预报图、气象曲线（深色模式 `dispose`+重绘，无白底残留） |
| 路由 | vue-router 4 | `createWebHistory`，5 路由 + `*` → 404 |
| Markdown | marked 12 + DOMPurify 3 | 回答渲染，HTML 必经 `sanitize()` |
| 流式 | fetch + ReadableStream | SSE 消费，支持 `AbortController` 中止 |
| 后端 | FastAPI + Uvicorn | 异步 REST / SSE |
| LLM | Qwen/Qwen3.8-27B（ModelScope 免费推理） | 大语言模型 |
| Embedding | bge-small-zh-v1.5 | 文本向量化（知识检索） |
| 向量库 | FAISS | 农业知识检索 |
| 气象 / 地理 | 中科天机 / 高德地图 | 实时气象 + 行政区划 |
| 部署 | Docker + nginx | 单容器，监听 `7860` |

---

## 目录结构（前端）

```
modelscope_space/
├── Dockerfile                 # 多阶段构建（前端 build + 后端运行）
├── docker-compose.yml         # 容器编排（暴露 7860）
├── start.sh                   # 启动脚本（nginx + uvicorn）
├── .env.example               # 环境变量模板
├── backend/                   # FastAPI 后端
│   └── app/
│       ├── main.py            # 入口
│       ├── routers/           # chat/weather/location/farm/warning/health
│       └── schemas/           # 请求/响应模型
└── frontend/                  # Vue 3 前端
    ├── index.html             # 含防闪白/闪黑内联脚本
    ├── package.json
    ├── vite.config.js
    ├── nginx.conf             # 监听 7860，proxy_buffering off（SSE）
    └── src/
        ├── main.js            # 注册 EP 全部图标 + 主题预初始化
        ├── App.vue            # 应用外壳（Header / Drawer / TabBar）
        ├── api/               # axios 封装 + 各模块 API
        ├── assets/styles/     # main.css(Token) / theme.css(EP桥接) / markdown.css
        ├── composables/       # useChart / useSpeech / useAutoRefresh
        ├── router/            # 路由 + NAV_ITEMS 单一来源
        ├── stores/            # theme/weather/location/chat/farm/warning
        ├── utils/             # sse / markdown / risk / storage / format / suitability
        ├── components/        # 通用组件（20+）
        │   ├── AppHeader / AppNavDrawer / AppTabBar / ThemeToggle / LocationSelector
        │   ├── ChatComposer / SessionList / MarkdownRenderer / AnswerMetaPanel / FeedbackBar / NowcastBanner
        │   ├── Dashboard: MetricCard / StatPill / RiskBadge / WeatherPanel / WeatherChart / ForecastChart / PageHeader / EmptyState / SkeletonCard
        │   └── Farm/Calendar: FieldCard / FieldDetailDrawer / SuitabilityBar / SuitabilityMatrix
        └── views/             # DashboardView / ChatView / FarmView / WarningView / CalendarView / NotFoundView
```

---

## API 接口

> 以下路径均为相对前缀 `/api`（`frontend/src/api` 中 `baseURL: '/api'`）。

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 健康 | GET | `/api/health` | 健康检查 |
| 问答 | POST | `/api/chat` | 智能问答（完整返回，SSE 失败时的降级出口） |
| 问答 | POST | `/api/chat/stream` | **SSE 流式问答**（事件：`nowcast` / `token` / `done(meta)` / `error`） |
| 反馈 | POST | `/api/chat/feedback` | 提交回答反馈（点赞/点踩 + 原因） |
| 反馈 | GET | `/api/chat/feedback/stats` | 回答反馈统计（接受率等） |
| 气象 | GET | `/api/weather` | 实时气象 + 未来 7 天预报 |
| 地理 | POST | `/api/location/coordinates` | 地址 → 经纬度 |
| 地理 | GET | `/api/location/provinces` | 省份列表 |
| 地理 | GET | `/api/location/cities` | 城市列表 |
| 地理 | GET | `/api/location/districts` | 区县列表 |
| 农场 | GET / POST | `/api/farm/fields` | 地块列表 / 创建 |
| 农场 | GET / DELETE | `/api/farm/fields/{id}` | 地块详情 / 删除 |
| 农场 | POST | `/api/farm/fields/{id}/water` | 灌溉操作 |
| 农场 | POST | `/api/farm/fields/{id}/fertilize` | 施肥操作 |
| 农场 | POST | `/api/farm/fields/{id}/harvest` | 收获操作 |
| 农场 | GET | `/api/farm/alerts` | 地块相关预警 |
| 预警 | POST | `/api/warning/disaster` | 灾害预警分析 |
| 预警 | POST | `/api/warning/pest` | 病虫害预警分析 |
| 预警 | POST | `/api/warning/suitability` | 农事适宜度综合评估（72h） |

---

## 本地开发

### 前后端分别启动

```bash
# 后端（:8000）
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端（:5173，Vite 自动反代 /api → :8000）
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # 产物输出至 dist/（零错误零警告，除 chunk 体积提示）
npm run preview      # 本地预览构建产物
```

前端仅依赖运行时的 `/api` 反代，本地开发无需手动配置跨域。

### Docker 一键启动

```bash
cp .env.example .env   # 填入 API Key
docker-compose up --build
# 访问 http://localhost:7860
```

---

## 环境变量

部署前需配置以下环境变量。**所有 Key 请填写你自己的**（在对应平台申请），切勿使用他人泄露的 Key，以免产生盗用费用：

| 变量 | 用途 | 申请渠道 |
|------|------|----------|
| `LLM_API_KEY` | 大模型推理密钥 | 魔搭社区 ModelScope「模型服务 / API」页申请 |
| `LLM_API_URL` | LLM API 地址 | 默认 `https://api-inference.modelscope.cn/v1` |
| `LLM_MODEL` | LLM 模型 | 默认 `Qwen/Qwen3.8-27B`（ModelScope 免费推理，已本地 curl 实测可用） |
| `EMBEDDING_MODEL` | Embedding 模型 | 默认 `bge-small-zh-v1.5` |
| `WEATHER_API_KEY` | 实时气象 API 密钥 | 中科天机气象开放平台申请 |
| `WEATHER_SUBSCRIPTION_ID` | 气象数据订阅 ID | 同上（订阅气象产品后获得） |
| `AMAP_API_KEY` | 地理编码 / 行政区划 | 高德开放平台申请 |

配置方式（二选一）：

1. **本地开发**：复制 `.env.example` 为 `.env`，逐项填入你的 Key（`.env` 已被 `.gitignore` 排除，不会提交）；
2. **魔搭创空间部署**：在创空间「设置 → 环境变量」中逐项填写同名变量。

> ⚠️ 安全提醒：`KEY` 属于敏感信息，请勿写入代码、README 或任何会公开的文件。

---

## 设计系统要点

- **主色（耕作绿）**：`--brand-500: #2E8B5B`，配 50–900 色阶；Element Plus 主色已桥接为该绿。
- **深色模式**：`html.dark` 作用域内做 Token 镜像（页面底 `#0E1A14`、卡片 `#16261d` 等），文本对比度 ≥ 4.5:1；图表 `dispose`+重绘避免白底残留。
- **统一规范**：卡片圆角 16px、输入框/下拉 10px、按钮/Tag 8px；四档间距（4px 基准）；统一阴影与动效曲线。
- **响应式断点**：≥1200 / 992–1199 / 768–991 / <768（移动端切换底部 TabBar + 抽屉导航）。

---

## 部署到 ModelScope 创空间

线上地址：https://www.modelscope.cn/studios/ennmmmmm/Agricultural-Meteorological-Agent

1. 将 `modelscope_space/` 内容上传至魔搭创空间仓库。
2. 创空间类型选择 **Docker**。
3. 容器自动监听 **`7860` 端口**（nginx 反代 uvicorn）。
4. 在创空间设置中配置环境变量（API Key 等）。

---

## 许可证

Apache License 2.0 — 详见 [LICENSE](LICENSE)
