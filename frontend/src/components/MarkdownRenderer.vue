<template>
  <div
    ref="rootRef"
    class="markdown-renderer"
    :class="{ 'markdown-renderer--plain': streaming }"
  >
    <!-- 流式过程中渲染纯文本 + 光标，避免半截 Markdown 抖动（架构 R9） -->
    <template v-if="streaming">
      <span class="markdown-renderer__text">{{ content }}</span>
      <span class="markdown-renderer__caret" aria-hidden="true"></span>
    </template>

    <!-- 全站唯一的 v-html 使用点：内容已由 utils/markdown.js 净化 -->
    <div v-else class="markdown-body" v-html="html"></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { renderMarkdown } from '@/utils/markdown'
import { copyText } from '@/utils/format'

const props = defineProps({
  /** Markdown 原文 */
  content: { type: String, default: '' },
  /** 是否处于流式输出中 */
  streaming: { type: Boolean, default: false }
})

const rootRef = ref(null)

/** 先净化再渲染，绝不做字符串拼接后二次 v-html */
const html = computed(() => (props.streaming ? '' : renderMarkdown(props.content)))

/**
 * 给代码块补一个复制按钮（不引入 highlight.js，仅等宽字体 + 复制）。
 * 直接操作 DOM 而不拼接 HTML，避免破坏净化结果。
 */
function enhanceCodeBlocks() {
  const root = rootRef.value
  if (!root) return
  root.querySelectorAll('pre').forEach((pre) => {
    if (pre.querySelector('.md-copy')) return
    const btn = document.createElement('button')
    btn.type = 'button'
    btn.className = 'md-copy'
    btn.setAttribute('aria-label', '复制代码')
    btn.textContent = '复制'
    btn.addEventListener('click', async () => {
      const code = pre.querySelector('code')
      const ok = await copyText(code ? code.textContent : pre.textContent)
      btn.textContent = ok ? '已复制' : '失败'
      window.setTimeout(() => {
        btn.textContent = '复制'
      }, 1600)
    })
    pre.appendChild(btn)
  })
}

watch(
  () => html.value,
  () => {
    if (props.streaming) return
    nextTick(enhanceCodeBlocks)
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  const root = rootRef.value
  if (!root) return
  root.querySelectorAll('.md-copy').forEach((btn) => btn.remove())
})
</script>

<style scoped>
.markdown-renderer {
  width: 100%;
  min-width: 0;
}

.markdown-renderer__text {
  white-space: pre-wrap;
  font-size: var(--fs-body-lg);
  line-height: var(--lh-body-lg);
  color: var(--text-body);
}

.markdown-renderer__caret {
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 2px;
  vertical-align: text-bottom;
  background: var(--brand-500);
  animation: caret-blink 1s steps(2, start) infinite;
}

@keyframes caret-blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .markdown-renderer__caret {
    animation: none;
  }
}

/* 代码块复制按钮 */
.markdown-renderer :deep(pre) {
  position: relative;
}

.markdown-renderer :deep(.md-copy) {
  position: absolute;
  top: var(--sp-2);
  right: var(--sp-2);
  padding: 2px var(--sp-2);
  font-size: var(--fs-caption);
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xs);
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease);
}

.markdown-renderer :deep(pre:hover .md-copy),
.markdown-renderer :deep(.md-copy:focus-visible) {
  opacity: 1;
}

.markdown-renderer :deep(.md-copy:hover) {
  color: var(--brand-500);
}
</style>
