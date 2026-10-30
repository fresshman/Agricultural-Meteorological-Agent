import { describe, it, expect } from 'vitest'
import { renderMarkdown, markdownToText, escapeHtml } from './markdown.js'

describe('utils/markdown · 正常 markdown 渲染', () => {
  it('标题 / 粗体 / 斜体', () => {
    expect(renderMarkdown('# 标题')).toContain('<h1>标题</h1>')
    expect(renderMarkdown('**粗体**')).toContain('<strong>粗体</strong>')
    expect(renderMarkdown('*斜体*')).toContain('<em>斜体</em>')
  })

  it('列表与引用', () => {
    expect(renderMarkdown('- 甲\n- 乙')).toContain('<li>甲</li>')
    expect(renderMarkdown('> 引用')).toContain('<blockquote>')
  })

  it('链接自动补 target=_blank / rel=noopener noreferrer', () => {
    const html = renderMarkdown('[示例](https://example.com)')
    expect(html).toContain('href="https://example.com"')
    expect(html).toContain('target="_blank"')
    expect(html).toContain('rel="noopener noreferrer"')
  })

  it('表格外包 table-scroll 滚动容器（小屏不撑破卡片）', () => {
    const html = renderMarkdown('| a | b |\n| --- | --- |\n| 1 | 2 |')
    expect(html).toContain('<div class="table-scroll">')
    expect(html).toContain('<table>')
    expect(html).toContain('<th>a</th>')
    expect(html).toContain('<td>1</td>')
  })

  it('任务列表复选框：checked / disabled', () => {
    const html = renderMarkdown('- [x] 完成\n- [ ] 未完成')
    expect(html).toContain('type="checkbox"')
    expect(html).toContain('checked=""')
    expect(html).toContain('disabled="disabled"')
  })

  it('空输入返回空串', () => {
    expect(renderMarkdown(null)).toBe('')
    expect(renderMarkdown(undefined)).toBe('')
    expect(renderMarkdown('')).toBe('')
    expect(renderMarkdown('   \n  ')).toBe('')
  })
})

describe('utils/markdown · XSS 净化（安全回归）', () => {
  it('<script> 整体移除', () => {
    expect(renderMarkdown('<script>alert(1)</script>')).toBe('')
    expect(renderMarkdown('文本中 <script>alert(1)</script> 内联')).not.toContain('alert')
  })

  it('<img onerror> 事件属性被剥掉', () => {
    const html = renderMarkdown('<img src="x" onerror="alert(1)">')
    expect(html).toContain('<img src="x">')
    expect(html).not.toContain('onerror')
  })

  it('javascript: 协议 href 被移除', () => {
    const html = renderMarkdown('<a href="javascript:alert(1)">点击</a>')
    expect(html).not.toContain('javascript:')
  })

  it('style 属性与 on* 事件属性被剥掉', () => {
    expect(renderMarkdown('<div style="color:red" onmouseover="x()">t</div>')).toBe('<div>t</div>')
  })

  it('onclick 被剥掉，合法 href 保留', () => {
    const html = renderMarkdown('<a href="https://ok.com" onclick="steal()">ok</a>')
    expect(html).toContain('href="https://ok.com"')
    expect(html).not.toContain('onclick')
  })

  it('iframe / style / form / svg 等危险标签被移除', () => {
    expect(renderMarkdown('<iframe src="//evil"></iframe>')).toBe('')
    expect(renderMarkdown('<style>body{display:none}</style>')).toBe('')
    expect(renderMarkdown('<svg onload="alert(1)"><circle r="1"/></svg>')).not.toContain('onload')
    expect(renderMarkdown('<form action="/x"><input name="q"></form>')).not.toContain('name="q"')
  })

  it('data-* 属性不透传', () => {
    expect(renderMarkdown('<p data-secret="1">t</p>')).toBe('<p>t</p>')
  })

  it('普通行内 HTML 与 & 转义正常', () => {
    expect(renderMarkdown('普通文本 & <b>粗体</b>')).toBe('<p>普通文本 &amp; <b>粗体</b></p>\n')
  })
})

describe('utils/markdown · markdownToText / escapeHtml', () => {
  it('剥离常见 markdown 标记', () => {
    expect(markdownToText('# 标题')).toBe('标题')
    expect(markdownToText('**粗体**')).toBe('粗体')
    expect(markdownToText('`code`')).toBe('code')
    expect(markdownToText('[文字](https://x.com)')).toBe('文字')
    expect(markdownToText('![图](https://x.com/a.png)')).toBe('图')
    expect(markdownToText('> 引用')).toBe('引用')
    expect(markdownToText('- 列表项')).toBe('列表项')
    expect(markdownToText('---')).toBe('')
  })

  it('空值兜底', () => {
    expect(markdownToText('')).toBe('')
    expect(markdownToText(null)).toBe('')
    expect(markdownToText(undefined)).toBe('')
  })

  it('escapeHtml 转义五类字符', () => {
    expect(escapeHtml('<a href="x">&\'')).toBe('&lt;a href=&quot;x&quot;&gt;&amp;&#39;')
  })
})
