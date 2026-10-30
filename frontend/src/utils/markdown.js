/**
 * Markdown 渲染管线（全站唯一）
 * --------------------------------------------------------------------------
 * 规则：
 * 1. 业务代码一律 `import { renderMarkdown } from '@/utils/markdown'`，
 *    禁止直接 import marked / dompurify；
 * 2. 输出必定已经过 DOMPurify 白名单净化，可直接安全用于 v-html；
 * 3. 全站 `v-html` 只允许出现在 MarkdownRenderer.vue 一处。
 */
import { marked } from 'marked'
import DOMPurify from 'dompurify'

/** 允许的标签白名单 */
const ALLOWED_TAGS = [
  'p', 'br', 'hr', 'span', 'div',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'strong', 'em', 'b', 'i', 'u', 'del', 's', 'sup', 'sub',
  'ul', 'ol', 'li',
  'blockquote', 'pre', 'code',
  'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
  'a', 'img', 'input'
]

/** 允许保留的属性白名单（显式排除 style / on* 事件属性） */
const ALLOWED_ATTR = [
  'href', 'title', 'target', 'rel',
  'src', 'alt', 'width', 'height',
  'colspan', 'rowspan', 'align', 'class',
  'type', 'checked', 'disabled'
]

marked.setOptions({ gfm: true, breaks: true })

// 自定义渲染器：表格外层包滚动容器（小屏横向滚动且不撑破卡片）
const renderer = {
  table(header, body) {
    const tbody = body ? `<tbody>${body}</tbody>` : ''
    return (
      '<div class="table-scroll">\n<table>\n<thead>\n' +
      header +
      '</thead>\n' +
      tbody +
      '</table>\n</div>\n'
    )
  },
  link(href, title, text) {
    const safeTitle = title ? ` title="${title}"` : ''
    return `<a href="${href}"${safeTitle} target="_blank" rel="noopener noreferrer">${text}</a>`
  }
}

marked.use({ renderer })

// 净化阶段统一给外链补 target/rel，并拦掉 javascript: 等危险协议
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
  if (node.tagName === 'INPUT') {
    // 仅允许 marked 生成的禁用复选框（任务列表）
    node.setAttribute('disabled', 'disabled')
    node.removeAttribute('onchange')
  }
})

/**
 * Markdown 原文 → 已净化的 HTML 字符串（唯一出口）。
 * @param {string} raw Markdown 原文
 * @returns {string} 安全 HTML；输入为空时返回空串
 */
export function renderMarkdown(raw) {
  if (raw === null || raw === undefined) return ''
  const text = String(raw)
  if (!text.trim()) return ''
  let dirty = ''
  try {
    dirty = marked.parse(text)
  } catch (err) {
    console.warn('[markdown] 解析失败，已降级为纯文本', err)
    dirty = escapeHtml(text).replace(/\n/g, '<br>')
  }
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    FORBID_TAGS: ['script', 'style', 'iframe', 'form', 'textarea', 'object', 'embed', 'link', 'meta'],
    FORBID_ATTR: ['style', 'onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'srcset'],
    ALLOW_DATA_ATTR: false,
    ALLOW_ARIA_ATTR: false
  })
}

/**
 * 剥离 Markdown 标记，得到纯文本（用于复制、摘要、搜索）。
 * @param {string} raw
 * @returns {string}
 */
export function markdownToText(raw) {
  if (!raw) return ''
  return String(raw)
    .replace(/```[\s\S]*?```/g, (m) => m.replace(/```/g, ''))
    .replace(/`([^`]+)`/g, '$1')
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^\s{0,3}#{1,6}\s+/gm, '')
    .replace(/^\s{0,3}>\s?/gm, '')
    .replace(/[*_~]{1,3}/g, '')
    .replace(/^\s{0,3}([-*+]|\d+\.)\s+/gm, '')
    .replace(/^\s{0,3}(-{3,}|\*{3,})\s*$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

/**
 * HTML 转义（解析失败时的兜底）。
 * @param {string} text
 * @returns {string}
 */
export function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
