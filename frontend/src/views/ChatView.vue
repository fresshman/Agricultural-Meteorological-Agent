<template>
  <div class="chat-view">
    <!-- 移动端会话抽屉 -->
    <transition name="drawer">
      <aside v-if="drawerOpen" class="chat-view__drawer">
        <SessionList
          :sessions="chat.sessions"
          :current-id="chat.currentSessionId"
          @select="onSelect"
          @new="onNew"
          @rename="onRename"
          @remove="onRemove"
        />
      </aside>
    </transition>
    <transition name="fade">
      <div v-if="drawerOpen" class="chat-view__scrim" @click="drawerOpen = false"></div>
    </transition>

    <!-- 桌面侧栏 -->
    <aside class="chat-view__aside">
      <SessionList
        :sessions="chat.sessions"
        :current-id="chat.currentSessionId"
        @select="onSelect"
        @new="onNew"
        @rename="onRename"
        @remove="onRemove"
      />
    </aside>

    <section class="chat-view__main">
      <!-- 顶部条 -->
      <header class="chat-view__top">
        <button
          v-if="isNarrow"
          type="button"
          class="chat-view__menu"
          aria-label="打开会话列表"
          @click="drawerOpen = true"
        >
          <el-icon :size="20"><Menu /></el-icon>
        </button>
        <div class="chat-view__heading">
          <h1 class="chat-view__title">{{ currentTitle }}</h1>
          <p class="chat-view__sub">
            <el-icon class="chat-view__pin"><Location /></el-icon>
            <span class="truncate">{{ location.summary }}</span>
            <span class="chat-view__dot">·</span>
            <span>采纳率 {{ acceptanceText }}</span>
          </p>
        </div>
        <el-button class="chat-view__new" type="primary" plain size="small" @click="onNew">
          <el-icon><Plus /></el-icon>
          <span>新会话</span>
        </el-button>
      </header>

      <!-- 消息区 -->
      <div ref="scrollEl" class="chat-view__scroll" @scroll="onScroll">
        <EmptyState
          v-if="!messages.length"
          icon="ChatDotSquare"
          title="开始你的农事咨询"
          description="左侧可新建多个会话，连续追问会保留上下文。试试下面的示例问题。"
          size="lg"
        >
          <template #extra>
            <div class="chat-view__examples">
              <button
                v-for="q in exampleQuestions"
                :key="q"
                type="button"
                class="chat-view__example"
                @click="onSend(q)"
              >
                {{ q }}
              </button>
            </div>
          </template>
        </EmptyState>

        <template v-else>
          <article
            v-for="m in messages"
            :key="m.id"
            class="msg"
            :class="m.role === 'user' ? 'msg--user' : 'msg--bot'"
          >
            <div class="msg__avatar" :class="`msg__avatar--${m.role}`" aria-hidden="true">
              <el-icon v-if="m.role === 'user'" :size="16"><User /></el-icon>
              <el-icon v-else :size="16"><Sunny /></el-icon>
            </div>
            <div class="msg__body">
              <div
                class="msg__bubble"
                :class="{ 'msg__bubble--error': m.status === 'error', 'msg__bubble--aborted': m.status === 'aborted' }"
              >
                <template v-if="m.role === 'user'">
                  <p class="msg__text">{{ m.content }}</p>
                </template>
                <template v-else>
                  <MarkdownRenderer :content="m.content" :streaming="isStreaming(m)" />
                  <NowcastBanner
                    v-if="m.meta?.nowcast_alert"
                    class="msg__nowcast"
                    :text="m.meta.nowcast_alert"
                    closable
                  />
                  <AnswerMetaPanel v-if="m.meta && !isStreaming(m)" :meta="m.meta" />
                  <FeedbackBar
                    v-if="!isStreaming(m)"
                    class="msg__feedback"
                    :value="m.feedback"
                    :stats="chat.feedbackStats"
                    :show-acceptance="false"
                    @feedback="(rating) => onFeedback(m, rating)"
                    @copy="onCopy(m)"
                    @regenerate="onRegenerate(m)"
                  />
                  <p v-if="m.status === 'error'" class="msg__err">
                    <el-icon><WarningFilled /></el-icon>
                    {{ m.errorMsg || '生成失败，请重试' }}
                  </p>
                </template>
              </div>
              <div class="msg__meta num">
                <span v-if="m.latencyMs">{{ formatDuration(m.latencyMs) }}</span>
                <span v-if="m.latencyMs && m.ts">·</span>
                <span v-if="m.ts">{{ formatTime(m.ts) }}</span>
              </div>
            </div>
          </article>
        </template>

        <!-- 回到最新 -->
        <transition name="fade">
          <button v-if="!atBottom && messages.length" type="button" class="chat-view__totop" @click="scrollToBottom(true)">
            <el-icon><ArrowDown /></el-icon>
            <span>回到最新</span>
          </button>
        </transition>
      </div>

      <!-- 输入区 -->
      <div class="chat-view__composer">
        <ChatComposer :chips="quickChips" @send="onSend" @stop="onStop" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import SessionList from '@/components/SessionList.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import AnswerMetaPanel from '@/components/AnswerMetaPanel.vue'
import FeedbackBar from '@/components/FeedbackBar.vue'
import NowcastBanner from '@/components/NowcastBanner.vue'
import ChatComposer from '@/components/ChatComposer.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useChatStore } from '@/stores/chat'
import { useLocationStore } from '@/stores/location'
import { useWeatherStore } from '@/stores/weather'
import { copyText, formatDuration, formatTime } from '@/utils/format'

const chat = useChatStore()
const location = useLocationStore()
const weather = useWeatherStore()
const route = useRoute()

const drawerOpen = ref(false)
const isNarrow = ref(typeof window === 'undefined' ? false : window.innerWidth < 992)
const scrollEl = ref(null)
const atBottom = ref(true)

const messages = computed(() => chat.messages)

const currentTitle = computed(() => chat.currentSession?.title || '智能问答')

const acceptanceText = computed(() => {
  const rate = Number(chat.feedbackStats?.acceptance_rate)
  if (!Number.isFinite(rate) || !chat.feedbackStats?.total) return '--'
  return `${Math.round(rate > 1 ? rate : rate * 100)}%`
})

const quickChips = ['未来三天适合打药吗？', '帮我看下玉米长势', '明天能灌溉吗？', '近期有灾害风险吗？']

const exampleQuestions = [
  '未来三天玉米适合打药吗？',
  '帮我分析这块地的长势和土壤墒情',
  '明后两天适合灌溉吗？',
  '近期有什么气象灾害或病虫害风险？'
]

// ---------------------------------------------------------------- 行为
function isStreaming(m) {
  return Boolean(chat.streaming && chat.streamingId === m.id)
}

function onSelect(id) {
  chat.switchSession(id)
  drawerOpen.value = false
}
function onNew() {
  chat.newSession()
  drawerOpen.value = false
}
function onRename(id, title) {
  chat.renameSession(id, title)
}
function onRemove(id) {
  chat.removeSession(id)
}

async function onSend(text) {
  if (chat.streaming) return
  const ok = await chat.ask(text)
  if (!ok && chat.error) ElMessage.error(chat.error)
  nextTick(() => scrollToBottom(true))
}
function onStop() {
  chat.stopStream()
}

async function onFeedback(m, rating) {
  try {
    await chat.submitFeedback(m.id, rating)
    ElMessage.success('已记录你的反馈')
  } catch (err) {
    ElMessage.error(err?.message || '反馈提交失败')
  }
}
async function onCopy(m) {
  const ok = await copyText(m.content)
  ElMessage[ok ? 'success' : 'error'](ok ? '已复制答案' : '复制失败')
}
function onRegenerate(m) {
  chat.regenerate(m.id)
}

// ---------------------------------------------------------------- 滚动吸底
function nearBottom() {
  const el = scrollEl.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight < 80
}
function scrollToBottom(force = false) {
  const el = scrollEl.value
  if (!el) return
  if (!force && !atBottom.value) return
  el.scrollTop = el.scrollHeight
  atBottom.value = true
}
function onScroll() {
  atBottom.value = nearBottom()
}

watch(
  () => messages.value.length,
  () => nextTick(() => scrollToBottom())
)
watch(
  () => chat.streamingId,
  () => nextTick(() => scrollToBottom())
)
// 流式内容逐字增长时持续吸底
watch(
  () => chat.currentSession?.messages?.reduce((s, m) => s + (m.content?.length || 0), 0),
  () => nextTick(() => scrollToBottom())
)

function onResize() {
  const w = window.innerWidth
  isNarrow.value = w < 992
  if (w >= 992) drawerOpen.value = false
}

onMounted(() => {
  chat.hydrate()
  chat.loadFeedbackStats()
  if (!weather.available && !weather.loading) weather.loadWeather(168)
  window.addEventListener('resize', onResize)
  nextTick(() => scrollToBottom(true))
  // 支持从首页快捷入口带语境进入（/chat?q=...）
  const q = route.query?.q
  if (q) nextTick(() => onSend(String(q)))
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.chat-view {
  display: flex;
  height: 100%;
  min-height: 0;
  width: 100%;
}

.chat-view__aside {
  flex: 0 0 260px;
  width: 260px;
  border-right: 1px solid var(--border-light);
  min-height: 0;
  background: var(--bg-card);
}

.chat-view__main {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-view__top {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-5);
  border-bottom: 1px solid var(--border-light);
  background: color-mix(in srgb, var(--bg-card) 80%, transparent);
  backdrop-filter: blur(8px);
}

.chat-view__menu {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-body);
  cursor: pointer;
}

.chat-view__heading {
  flex: 1 1 auto;
  min-width: 0;
}

.chat-view__title {
  margin: 0;
  font-size: var(--fs-h3);
  font-weight: 600;
  color: var(--text-title);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-view__sub {
  display: flex;
  align-items: center;
  gap: 4px;
  margin: 2px 0 0;
  font-size: var(--fs-caption);
  color: var(--text-secondary);
}

.chat-view__pin {
  color: var(--brand-500);
}

.chat-view__dot {
  color: var(--text-disabled);
}

.chat-view__new {
  flex: 0 0 auto;
}

.chat-view__scroll {
  position: relative;
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: var(--sp-5);
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
}

.chat-view__examples {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  justify-content: center;
  margin-top: var(--sp-3);
}

.chat-view__example {
  padding: 6px var(--sp-4);
  font-size: var(--fs-sm);
  color: var(--brand-700);
  background: var(--brand-50);
  border: 1px solid var(--brand-200);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}

html.dark .chat-view__example {
  color: var(--brand-300);
  background: color-mix(in srgb, var(--brand-500) 14%, transparent);
  border-color: color-mix(in srgb, var(--brand-500) 30%, transparent);
}

.chat-view__example:hover {
  border-color: var(--brand-400);
  background: var(--brand-100);
}

/* 消息气泡 */
.msg {
  display: flex;
  gap: var(--sp-3);
  max-width: 860px;
  width: 100%;
  align-self: center;
}

.msg--user {
  flex-direction: row-reverse;
}

.msg__avatar {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: #fff;
}

.msg__avatar--user {
  background: var(--brand-500);
}

.msg__avatar--assistant {
  background: linear-gradient(135deg, var(--state-info), var(--brand-500));
}

.msg__body {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.msg--user .msg__body {
  align-items: flex-end;
}

.msg__bubble {
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  max-width: 100%;
}

.msg--user .msg__bubble {
  background: var(--brand-500);
  border-color: var(--brand-500);
  color: #fff;
}

.msg__bubble--error {
  border-color: color-mix(in srgb, var(--state-danger) 40%, transparent);
  background: color-mix(in srgb, var(--state-danger) 8%, var(--bg-card));
}

.msg__bubble--aborted {
  opacity: 0.75;
}

.msg__text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: var(--fs-body);
  line-height: var(--lh-body);
}

.msg__nowcast {
  margin-top: var(--sp-3);
}

.msg__feedback {
  margin-top: 0;
}

.msg__err {
  display: flex;
  align-items: center;
  gap: 4px;
  margin: var(--sp-2) 0 0;
  font-size: var(--fs-caption);
  color: var(--state-danger);
}

.msg__meta {
  font-size: var(--fs-caption);
  color: var(--text-disabled);
  padding: 0 var(--sp-1);
}

.chat-view__totop {
  position: absolute;
  bottom: var(--sp-4);
  left: 50%;
  transform: translateX(-50%);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px var(--sp-3);
  font-size: var(--fs-caption);
  color: var(--brand-700);
  background: var(--bg-card);
  border: 1px solid var(--brand-300);
  border-radius: var(--radius-full);
  cursor: pointer;
  box-shadow: var(--shadow-2);
  z-index: 2;
}

html.dark .chat-view__totop {
  color: var(--brand-300);
}

.chat-view__composer {
  flex: 0 0 auto;
  padding: var(--sp-4) var(--sp-5) var(--sp-5);
  border-top: 1px solid var(--border-light);
  background: var(--bg-card);
}

/* 移动端抽屉 */
.chat-view__drawer {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 280px;
  max-width: 82vw;
  z-index: 60;
  border-right: 1px solid var(--border-light);
  background: var(--bg-card);
  box-shadow: var(--shadow-2);
}

.chat-view__scrim {
  position: fixed;
  inset: 0;
  z-index: 55;
  background: rgba(0, 0, 0, 0.4);
}

/* 窄屏隐藏侧栏，改用抽屉 */
@media (max-width: 991px) {
  .chat-view__aside {
    display: none;
  }
}

@media (min-width: 992px) {
  .chat-view__drawer,
  .chat-view__scrim {
    display: none !important;
  }
}

@media (max-width: 767px) {
  .chat-view__top {
    padding: var(--sp-3) var(--sp-4);
  }
  .chat-view__scroll {
    padding: var(--sp-4);
  }
  .chat-view__composer {
    padding: var(--sp-3) var(--sp-4) var(--sp-4);
  }
  .msg {
    gap: var(--sp-2);
  }
}
</style>
