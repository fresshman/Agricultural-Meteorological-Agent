# -*- coding: utf-8 -*-
"""
文本清洗模块 (书籍/论文增强版)

功能：
1. 智能提取文献标题（书名/论文题目）
2. 增强目录识别（基于内容特征，非仅标题）
3. 清理前言、序言、编委会、版权页等
4. 清理PDF转换产生的特殊标签
5. 清理LaTeX公式残留
6. 清理页眉页脚、页码
7. 规范化空白字符
"""

import re
from typing import List, Tuple, Set, Optional, Dict
from dataclasses import dataclass, field


@dataclass
class CleanResult:
    """清洗结果"""
    text: str                              # 清洗后的文本
    title: str = ""                        # 提取的标题
    removed_sections: List[str] = field(default_factory=list)  # 移除的部分名称
    original_length: int = 0               # 原始长度
    cleaned_length: int = 0                # 清洗后长度
    metadata: Dict = field(default_factory=dict)  # 额外元数据（如作者、出版信息等）


class TextCleaner:
    """
    文本清洗器 (书籍/论文增强版)
    
    使用示例:
    ---------
    cleaner = TextCleaner()
    result = cleaner.clean(text)
    print(f"标题: {result.title}")
    print(f"正文: {result.text[:500]}...")
    """
    
    # ==================== 前言/序言识别 ====================
    FRONTMATTER_TITLES = [
        r'编辑委员会', r'编委会', r'编辑说明', r'编写说明',
        r'前\s*言', r'序\s*言', r'序\s*$', r'序\s*一', r'序\s*二',
        r'致\s*谢', r'致\s*辞', r'献\s*词',
        r'出版说明', r'出版者?的话', r'编者的话', r'编者按',
        r'凡\s*例', r'使用说明', r'阅读指南', r'导\s*读',
        r'作者简介', r'作者介绍', r'关于作者', r'著?者简介',
        r'译者?序', r'译者的话', r'翻译说明',
        r'再版说明', r'修订说明', r'第.版说明',
        r'版权声明', r'版权页', r'版权信息',
        r'内容简介', r'内容提要',
        # 注意：摘要(abstract)对于论文是重要内容，不移除
        r'主\s*编', r'副主编', r'责任编辑', r'特约编辑',
        r'鸣\s*谢', r'acknowledgment',
    ]
    
    TOC_TITLES = [
        r'目\s*录', r'目\s*次', r'简要目录', r'详细目录',
        r'contents?', r'table\s+of\s+contents?',
        r'章节目录', r'总目录', r'分目录',
    ]
    
    APPENDIX_TITLES = [
        r'附\s*录', r'附\s*表', r'附\s*图', r'附\s*件',
        r'参考文献', r'参考资料', r'引用文献', r'references?',
        r'bibliography', r'引用书目',
        r'索\s*引', r'关键词索引', r'人名索引', r'主题索引',
        r'术语表', r'词汇表', r'glossary',
    ]
    
    # ==================== 版权页/出版信息特征 ====================
    COPYRIGHT_PATTERNS = [
        r'ISBN[\s:：]*[\d\-X]+',
        r'CIP[\s\(（].*?[\)）]',
        r'图书在版编目',
        r'中国版本图书馆',
        r'出\s*版\s*社', r'出\s*版\s*发\s*行',
        r'印\s*刷\s*厂', r'印\s*刷\s*者',
        r'开\s*本[：:\s]*\d+',
        r'印\s*张[：:\s]*[\d\.]+',
        r'字\s*数[：:\s]*[\d\.]+\s*[千万]?字?',
        r'版\s*次[：:\s]*\d+',
        r'印\s*次[：:\s]*\d+',
        r'印\s*数[：:\s]*[\d\-]+',
        r'定\s*价[：:\s]*[\d\.]+\s*元',
        r'书\s*号[：:\s]*[\d\-]+',
        r'统一书号',
        r'邮\s*编[：:\s]*\d{6}',
        r'电\s*话[：:\s]*[\d\-]+',
        r'网\s*址[：:\s]*',
        r'版权所有', r'侵权必究', r'翻印必究',
        r'All [Rr]ights [Rr]eserved',
        r'©|Copyright',
    ]
    
    # ==================== 目录内容特征（非标题） ====================
    # 用于识别目录的具体内容行
    TOC_LINE_PATTERNS = [
        # 1. 经典带省略号/点的目录： "第一章 绑定......12" 或 "绪论 .... 1"
        r'^.+?[\.。…·\s]{3,}\s*\d+\s*$',
        
        # 2. 【新增】用户自定义宽泛规则：去除两边空格后，结尾为数字，且中间含有空格或点
        # 逻辑：^ 匹配开头，.*[ \.] 匹配中间包含空格或点，\d+$ 匹配结尾数字
        # 这会匹配 "2.1.1中国 8" (含空格) 和 "2.1.1" (含点)，依靠连续行阈值(默认5)过滤掉单独的章节号
        r'^\s*.*[ \.].*\d+\s*$',

        # 3. 中文章节编号： "一、绑定......12"
        r'^\s*[一二三四五六七八九十]+[、\.]\s*.+?[\.。…·\s]{3,}\s*\d+\s*$',
    ]
    
    # ==================== 编委会/作者列表特征 ====================
    COMMITTEE_PATTERNS = [
        r'主\s*编[：:\s]+',
        r'副\s*主\s*编[：:\s]+',
        r'编\s*委[：:\s]+',
        r'编写人员[：:\s]+',
        r'参编人员[：:\s]+',
        r'编著者?[：:\s]+',
        r'审\s*校[：:\s]+',
    ]
    
    # ==================== LaTeX 清洗模式 ====================
    LATEX_PATTERNS = [
        # 保留内容的命令
        (r'\\mathrm\{([^}]+)\}', r'\1'),
        (r'\\textbf\{([^}]+)\}', r'\1'),
        (r'\\textit\{([^}]+)\}', r'\1'),
        (r'\\text\{([^}]+)\}', r'\1'),
        (r'\\mathbf\{([^}]+)\}', r'\1'),
        (r'\\mathit\{([^}]+)\}', r'\1'),
        (r'\\emph\{([^}]+)\}', r'\1'),
        (r'\\underline\{([^}]+)\}', r'\1'),
        (r'\\texttt\{([^}]+)\}', r'\1'),
        (r'\\textrm\{([^}]+)\}', r'\1'),
        # 数学运算符 -> Unicode符号
        (r'\\sim(?![a-zA-Z])', '~'),
        (r'\\approx(?![a-zA-Z])', '≈'),
        (r'\\leq(?![a-zA-Z])', '≤'),
        (r'\\geq(?![a-zA-Z])', '≥'),
        (r'\\le(?![a-zA-Z])', '≤'),
        (r'\\ge(?![a-zA-Z])', '≥'),
        (r'\\times(?![a-zA-Z])', '×'),
        (r'\\cdot(?![a-zA-Z])', '·'),
        (r'\\pm(?![a-zA-Z])', '±'),
        (r'\\mp(?![a-zA-Z])', '∓'),
        (r'\\infty(?![a-zA-Z])', '∞'),
        (r'\\neq(?![a-zA-Z])', '≠'),
        (r'\\equiv(?![a-zA-Z])', '≡'),
        (r'\\propto(?![a-zA-Z])', '∝'),
        (r'\\rightarrow(?![a-zA-Z])', '→'),
        (r'\\leftarrow(?![a-zA-Z])', '←'),
        (r'\\Rightarrow(?![a-zA-Z])', '⇒'),
        (r'\\Leftarrow(?![a-zA-Z])', '⇐'),
        (r'\\subset(?![a-zA-Z])', '⊂'),
        (r'\\supset(?![a-zA-Z])', '⊃'),
        (r'\\in(?![a-zA-Z])', '∈'),
        (r'\\forall(?![a-zA-Z])', '∀'),
        (r'\\exists(?![a-zA-Z])', '∃'),
        (r'\\sum(?![a-zA-Z])', 'Σ'),
        (r'\\prod(?![a-zA-Z])', 'Π'),
        (r'\\int(?![a-zA-Z])', '∫'),
        (r'\\partial(?![a-zA-Z])', '∂'),
        (r'\\nabla(?![a-zA-Z])', '∇'),
        # 希腊字母
        (r'\\alpha(?![a-zA-Z])', 'α'),
        (r'\\beta(?![a-zA-Z])', 'β'),
        (r'\\gamma(?![a-zA-Z])', 'γ'),
        (r'\\delta(?![a-zA-Z])', 'δ'),
        (r'\\epsilon(?![a-zA-Z])', 'ε'),
        (r'\\zeta(?![a-zA-Z])', 'ζ'),
        (r'\\eta(?![a-zA-Z])', 'η'),
        (r'\\theta(?![a-zA-Z])', 'θ'),
        (r'\\iota(?![a-zA-Z])', 'ι'),
        (r'\\kappa(?![a-zA-Z])', 'κ'),
        (r'\\lambda(?![a-zA-Z])', 'λ'),
        (r'\\mu(?![a-zA-Z])', 'μ'),
        (r'\\nu(?![a-zA-Z])', 'ν'),
        (r'\\xi(?![a-zA-Z])', 'ξ'),
        (r'\\pi(?![a-zA-Z])', 'π'),
        (r'\\rho(?![a-zA-Z])', 'ρ'),
        (r'\\sigma(?![a-zA-Z])', 'σ'),
        (r'\\tau(?![a-zA-Z])', 'τ'),
        (r'\\upsilon(?![a-zA-Z])', 'υ'),
        (r'\\phi(?![a-zA-Z])', 'φ'),
        (r'\\chi(?![a-zA-Z])', 'χ'),
        (r'\\psi(?![a-zA-Z])', 'ψ'),
        (r'\\omega(?![a-zA-Z])', 'ω'),
        # 大写希腊字母
        (r'\\Gamma(?![a-zA-Z])', 'Γ'),
        (r'\\Delta(?![a-zA-Z])', 'Δ'),
        (r'\\Theta(?![a-zA-Z])', 'Θ'),
        (r'\\Lambda(?![a-zA-Z])', 'Λ'),
        (r'\\Xi(?![a-zA-Z])', 'Ξ'),
        (r'\\Pi(?![a-zA-Z])', 'Π'),
        (r'\\Sigma(?![a-zA-Z])', 'Σ'),
        (r'\\Phi(?![a-zA-Z])', 'Φ'),
        (r'\\Psi(?![a-zA-Z])', 'Ψ'),
        (r'\\Omega(?![a-zA-Z])', 'Ω'),
        # 移除其他未知LaTeX命令（放在最后）
        (r'\\[a-zA-Z]+\*?\{[^}]*\}', ''),  # \cmd{...} 或 \cmd*{...}
        (r'\\[a-zA-Z]+\*?(?![a-zA-Z])', ''),  # \cmd
        # 处理行内公式（保留内容）
        (r'\$([^$]+)\$', r'\1'),
        # 处理块级公式
        (r'\$\$([^$]+)\$\$', r'\1'),
        # 处理 \( \) 行内公式
        (r'\\\(([^)]+)\\\)', r'\1'),
        # 处理 \[ \] 块级公式
        (r'\\\[([^\]]+)\\\]', r'\1'),
    ]
    
    # ==================== PDF/Markdown 转换残留 ====================
    PDF_PATTERNS = [
        # Markdown 图片
        (r'!\[.*?\]\(.*?\)', ''),
        # Markdown 链接 -> 保留文本
        (r'\[([^\]]*)\]\([^\)]+\)', r'\1'),
        # 裸露的 URL
        (r'https?://\S+', ''),
        # HTML 标签
        (r'<[^>]+>', ''),
        # 表格分隔线
        (r'\|[-:]+\|', ''),
        (r'^\s*\|.*\|\s*$', '', re.MULTILINE),
        # 乱码/特殊字符修复
        (r'\x0c', '\n'),           # 分页符
        (r'\uf0b7', '•'),          # 项目符号
        (r'[\ue000-\uf8ff]', ''),  # 私用区字符
        (r'ﬁ', 'fi'),
        (r'ﬂ', 'fl'),
        (r'ﬀ', 'ff'),
        (r'ﬃ', 'ffi'),
        (r'ﬄ', 'ffl'),
        # 多余的Markdown格式
        (r'\*\*([^*]+)\*\*', r'\1'),  # **bold** -> bold
        (r'\*([^*]+)\*', r'\1'),      # *italic* -> italic
        (r'__([^_]+)__', r'\1'),
        (r'_([^_]+)_', r'\1'),
    ]
    
    # ==================== PDF工具噪音 ====================
    TOOL_NOISE_PATTERNS = [
        r'openxlab', r'mineru', r'internlm',
        r'model_center', r'modelscope',
        r'paddleocr', r'pdfplumber',
    ]
    
    # ==================== 图表标识模式（新增） ====================
    # 用于移除穿插在正文中的图表标识
    FIGURE_TABLE_PATTERNS = [
        # 中文图表标识
        r'^\s*图\s*[\d\.\-]+\s*[：:\s]?.*$',           # 图1 xxx / 图1.1 xxx / 图 1-1: xxx
        r'^\s*表\s*[\d\.\-]+\s*[：:\s]?.*$',           # 表1 xxx / 表1.1 xxx
        r'^\s*图\s*[\d\.\-]+\s*$',                     # 单独的 "图1"
        r'^\s*表\s*[\d\.\-]+\s*$',                     # 单独的 "表1"
        r'^\s*附图\s*[\d\.\-]+\s*[：:\s]?.*$',         # 附图1 xxx
        r'^\s*附表\s*[\d\.\-]+\s*[：:\s]?.*$',         # 附表1 xxx
        
        # 英文图表标识
        r'^\s*[Ff]ig(?:ure)?\.?\s*[\d\.\-]+\s*[：:\.\s]?.*$',   # Figure 1 / Fig. 1 / Fig 1.1
        r'^\s*[Tt]able\.?\s*[\d\.\-]+\s*[：:\.\s]?.*$',          # Table 1 / Table 1.1
        r'^\s*[Ff]ig(?:ure)?\.?\s*[\d\.\-]+\s*$',                # 单独的 Figure 1
        r'^\s*[Tt]able\.?\s*[\d\.\-]+\s*$',                      # 单独的 Table 1
        
        # 图表来源说明
        r'^\s*(?:资料)?来源[：:]\s*.{0,50}$',         # 来源: xxx（图表下方常见）
        r'^\s*[Ss]ource[：:\s].{0,50}$',              # Source: xxx
        r'^\s*注[：:]\s*.{0,100}$',                   # 注: xxx（图表注释，限制长度避免误删正文）
        r'^\s*[Nn]ote[s]?[：:\s].{0,100}$',           # Note: xxx
        
        # 图表内的单元格残留（通常是很短的数字或标签）
        r'^\s*[\d\.\,\%\-\+]+\s*$',                   # 纯数字行（如 "12.5" "100%"）
        r'^\s*[a-zA-Z]\s*$',                          # 单字母行（如表格的 a, b, c 标签）
        
        # 图片占位符（PDF转换残留）
        r'^\s*\[图\s*[\d\.\-]*\]\s*$',                # [图1] 占位符
        r'^\s*\[表\s*[\d\.\-]*\]\s*$',                # [表1] 占位符
        r'^\s*\[image\].*$',                          # [image] 标记
        r'^\s*\[figure\].*$',                         # [figure] 标记
    ]
    
    # ==================== 页眉页脚模式 ====================
    HEADER_FOOTER_PATTERNS = [
        # 年鉴/报告页眉
        r'^\s*\d{4}\s*年?\s*[中国统计年鉴农业报告]+.*$',
        # 英文页眉 "Chapter 1"
        r'^\s*Chapter\s+\d+\s*$',
        # 中文章节页眉
        r'^\s*第[一二三四五六七八九十百\d]+[章节篇部编]\s*$',
        # 页码格式 "- 12 -" 或 "— 12 —"
        r'^\s*[-—]\s*\d+\s*[-—]\s*$',
        # 纯页码
        r'^\s*\d{1,4}\s*$',
        # "Page 12" 或 "P.12"
        r'^\s*[Pp](?:age)?\.?\s*\d+\s*$',
        # 书名+页码 (常见页眉格式)
        r'^\s*[\u4e00-\u9fa5]{2,20}\s+\d{1,4}\s*$',
    ]
    
    # ==================== 标题排除模式 ====================
    # 这些内容不应被识别为标题
    TITLE_EXCLUDE_PATTERNS = [
        r'^[\s\d\-—\.·…]+$',           # 纯数字/符号
        r'^第?[一二三四五六七八九十\d]+[章节篇部]',  # 章节标题
        r'^\s*[#]+\s*$',               # 纯Markdown标记
        r'ISBN', r'CIP',               # 版权信息
        r'出版社', r'印刷',
        r'主编', r'编著',
        r'目\s*录', r'目\s*次',
        r'前\s*言', r'序\s*言',
        r'^\s*$',                      # 空行
    ]
    
    def __init__(self,
                 extract_title: bool = True,
                 remove_frontmatter: bool = True,
                 remove_toc: bool = True,
                 remove_appendix: bool = False,
                 remove_copyright: bool = True,
                 remove_headers: bool = True,
                 clean_pdf_artifacts: bool = True,
                 remove_figure_table: bool = True,
                 merge_broken_paragraphs: bool = True,
                 min_line_length: int = 2,
                 toc_detect_threshold: int = 5):
        """
        初始化清洗器
        
        Args:
            extract_title: 是否提取标题
            remove_frontmatter: 是否移除前言/序言等
            remove_toc: 是否移除目录
            remove_appendix: 是否移除附录/参考文献
            remove_copyright: 是否移除版权页信息
            remove_headers: 是否移除页眉页脚
            clean_pdf_artifacts: 是否清理PDF转换残留
            remove_figure_table: 是否移除图表标识（新增）
            merge_broken_paragraphs: 是否合并PDF分页断行（新增）
            min_line_length: 最小行长度（过滤噪音短行）
            toc_detect_threshold: 目录检测阈值（连续N行符合目录特征则判定为目录）
        """
        self.extract_title = extract_title
        self.remove_frontmatter = remove_frontmatter
        self.remove_toc = remove_toc
        self.remove_appendix = remove_appendix
        self.remove_copyright = remove_copyright
        self.remove_headers = remove_headers
        self.clean_pdf_artifacts = clean_pdf_artifacts
        self.remove_figure_table = remove_figure_table
        self.merge_broken_paragraphs = merge_broken_paragraphs
        self.min_line_length = min_line_length
        self.toc_detect_threshold = toc_detect_threshold
        
        self._compile_patterns()
    
    def _compile_patterns(self):
        """预编译所有正则表达式"""
        # 标题模式
        self.frontmatter_title_re = re.compile(
            r'^#{0,3}\s*(' + '|'.join(self.FRONTMATTER_TITLES) + r')\s*$',
            re.IGNORECASE | re.MULTILINE
        )
        self.toc_title_re = re.compile(
            r'^#{0,3}\s*(' + '|'.join(self.TOC_TITLES) + r')\s*$',
            re.IGNORECASE | re.MULTILINE
        )
        self.appendix_title_re = re.compile(
            r'^#{0,3}\s*(' + '|'.join(self.APPENDIX_TITLES) + r')\s*$',
            re.IGNORECASE | re.MULTILINE
        )
        
        # 目录内容行模式
        self.toc_line_patterns = [
            re.compile(p, re.MULTILINE) for p in self.TOC_LINE_PATTERNS
        ]
        
        # 版权信息模式
        self.copyright_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.COPYRIGHT_PATTERNS
        ]
        
        # 编委会模式
        self.committee_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.COMMITTEE_PATTERNS
        ]
        
        # 页眉页脚
        self.header_footer_re = [
            re.compile(p, re.MULTILINE | re.IGNORECASE) 
            for p in self.HEADER_FOOTER_PATTERNS
        ]
        
        # 标题排除
        self.title_exclude_re = [
            re.compile(p, re.IGNORECASE) for p in self.TITLE_EXCLUDE_PATTERNS
        ]
        
        # LaTeX和PDF清洗模式
        self.latex_patterns = []
        for p, r in self.LATEX_PATTERNS:
            self.latex_patterns.append((re.compile(p), r))
        
        self.pdf_patterns = []
        for item in self.PDF_PATTERNS:
            if len(item) == 2:
                p, r = item
                self.pdf_patterns.append((re.compile(p), r))
            else:
                p, r, flags = item
                self.pdf_patterns.append((re.compile(p, flags), r))
        
        # 工具噪音
        self.tool_noise_re = re.compile(
            r'\b(' + '|'.join(self.TOOL_NOISE_PATTERNS) + r')\b',
            re.IGNORECASE
        )
        
        # 图表标识模式（新增）
        self.figure_table_patterns = [
            re.compile(p, re.MULTILINE | re.IGNORECASE) 
            for p in self.FIGURE_TABLE_PATTERNS
        ]
        
        # PDF断行合并相关模式（新增）
        # 句末标点（中英文）
        self.sentence_end_punct = re.compile(r'[。！？.!?…）\)」』"\']+\s*$')
        # 新段落开始特征
        self.new_para_start = re.compile(
            r'^('
            r'#{1,6}\s+'                           # Markdown标题
            r'|第[一二三四五六七八九十\d]+[章节篇部]'  # 中文章节
            r'|\d+[\.\、]\s*'                       # 编号 (1. 1、)
            r'|[一二三四五六七八九十]+[、\.]\s*'     # 中文编号
            r'|[-\*\+•]\s+'                         # 列表项
            r'|[（\(]\d+[）\)]'                     # (1) 编号
            r'|摘\s*要|关键词|Abstract|Keywords'    # 论文特殊段落
            r'|图\s*\d|表\s*\d|Figure|Table'        # 图表标题
            r')'
        )
    
    def clean(self, text: str, source: str = "", show_progress: bool = False) -> CleanResult:
        """
        执行清洗
        
        Args:
            text: 原始文本
            source: 来源文件名（可选，用于辅助标题提取）
            show_progress: 是否显示进度
            
        Returns:
            CleanResult 对象
        """
        original_length = len(text)
        removed_sections = []
        metadata = {}
        
        if show_progress:
            print("  📝 文本清洗...")
        
        # 0. 【最先】提取标题（从原始文本，在任何清洗之前）
        title = ""
        if self.extract_title:
            title = self._extract_title(text, source)
            if show_progress and title:
                print(f"    → 提取标题: {title[:50]}{'...' if len(title) > 50 else ''}")
        
        # 1. 合并PDF分页断行
        if self.merge_broken_paragraphs:
            text, merge_count = self._merge_broken_paragraphs(text)
            if show_progress and merge_count > 0:
                print(f"    → 合并断行: {merge_count} 处")
        
        # 2. 移除版权页
        if self.remove_copyright:
            text, removed = self._remove_copyright_pages(text)
            if removed:
                removed_sections.append("版权页")
        
        # 3. 移除前言/序言/编委会
        if self.remove_frontmatter:
            text, removed = self._remove_frontmatter(text)
            if removed:
                removed_sections.extend(removed)
        
        # 4. 移除目录（增强版：基于内容特征）
        if self.remove_toc:
            text, removed = self._remove_toc_enhanced(text)
            if removed:
                removed_sections.append("目录")
        
        # 5. 移除附录/参考文献
        if self.remove_appendix:
            text, removed = self._remove_appendix(text)
            if removed:
                removed_sections.append("附录/参考文献")
        
        # 6. 清理PDF/LaTeX残留
        if self.clean_pdf_artifacts:
            text = self._clean_artifacts(text)
        
        # 7. 【新增】移除图表标识
        if self.remove_figure_table:
            text, fig_count = self._remove_figure_table_markers(text)
            if show_progress and fig_count > 0:
                print(f"    → 移除图表标识: {fig_count} 处")
        
        # 8. 移除页眉页脚
        if self.remove_headers:
            text = self._remove_headers_footers(text)
        
        # 9. 规范化空白
        text = self._normalize_whitespace(text)
        
        # 10. 过滤短行
        if self.min_line_length > 0:
            text = self._filter_short_lines(text)
        
        if show_progress:
            reduction = (1 - len(text) / original_length) * 100 if original_length > 0 else 0
            print(f"    → 清洗完成: {original_length:,} → {len(text):,} 字符 (减少 {reduction:.1f}%)")
            if removed_sections:
                print(f"    → 移除部分: {', '.join(removed_sections)}")
        
        return CleanResult(
            text=text,
            title=title,
            removed_sections=removed_sections,
            original_length=original_length,
            cleaned_length=len(text),
            metadata=metadata
        )
    
    # ==================== 标题提取 ====================
    
    def _extract_title(self, text: str, source: str = "") -> str:
        """
        提取文档标题
        
        策略：
        1. 从原始文本中找第一个 # 标题（排除前言/目录/章节编号标题）
        2. 没找到则从文件名提取
        """
        for line in text.split('\n'):
            line_stripped = line.strip()
            
            # 匹配 # 标题
            m = re.match(r'^(#{1,3})\s+(.+)', line_stripped)
            if not m:
                continue
            
            title_text = m.group(2).strip()
            
            # 跳过空标题或过短
            if not title_text or len(title_text) < 2:
                continue
            
            # 跳过版权/元数据类标题
            if any(p.search(title_text) for p in self.title_exclude_re):
                continue
            
            # 跳过前言/序言/目录类标题
            if self.frontmatter_title_re.search(line_stripped):
                continue
            if self.toc_title_re.search(line_stripped):
                continue
            
            return self._clean_title(title_text)
        
        # 没找到 # 标题，从文件名提取
        if source:
            return self._extract_title_from_filename(source)
        
        return ""
    
    def _looks_like_title(self, line: str) -> bool:
        """判断一行文本是否像标题"""
        # 长度适中
        if len(line) < 3 or len(line) > 80:
            return False
        
        # 不以数字或特殊符号开头
        if re.match(r'^[\d\.\-\*\+]', line):
            return False
        
        # 不是章节标题格式
        if re.match(r'^第?[一二三四五六七八九十\d]+[章节篇部]', line):
            return False
        
        # 不是摘要/关键词行
        if re.match(r'^(摘\s*要|关键词|abstract|keywords?)[：:\s]', line, re.IGNORECASE):
            return False
        
        # 不以句子结束（标题通常不带句号）
        if line.endswith('。') or line.endswith('.'):
            # 但如果很短可能是标题加了句号
            if len(line) > 30:
                return False
        
        return True
    
    def _is_copyright_line(self, line: str) -> bool:
        """判断是否是版权页内容行"""
        return any(p.search(line) for p in self.copyright_patterns)
    
    def _is_valid_title_candidate(self, line: str) -> bool:
        """判断是否是有效的标题候选"""
        # 长度检查：标题通常在3-100字符
        if len(line) < 3 or len(line) > 100:
            return False
        
        # 排除模式检查
        if any(p.search(line) for p in self.title_exclude_re):
            return False
        
        # 排除目录行
        if any(p.match(line) for p in self.toc_line_patterns):
            return False
        
        # 【新增】排除图表标识
        if any(p.match(line) for p in self.figure_table_patterns):
            return False
        
        # 【新增】排除以"图"、"表"、"Figure"、"Table"开头的行
        if re.match(r'^(图|表|附图|附表|[Ff]ig(?:ure)?|[Tt]able)\s*[\d\.\-]', line):
            return False
        
        # 排除以数字开头的行（通常是章节或列表）
        if re.match(r'^\d+[\.\、]', line):
            return False
        
        # 排除明显的页眉页脚
        if any(p.match(line) for p in self.header_footer_re):
            return False
        
        return True
    
    def _score_title_candidate(self, line: str, position: int, in_copyright_zone: bool = False) -> float:
        """
        对标题候选打分
        
        考虑因素：
        - 位置（越靠前越好，但要跳过版权页）
        - 长度（适中长度得分高）
        - 格式（Markdown标题格式加分）
        - 内容特征（包含书籍/论文常见词加分）
        """
        score = 100.0
        
        # 如果在版权区内，大幅降分
        if in_copyright_zone:
            score -= 50
        
        # 位置分（5-30行位置最佳）
        if position < 5:
            score += 10  # 非常靠前的非版权内容可能是标题
        elif position <= 30:
            score += 20  # 最佳位置
        elif position <= 50:
            score += 5
        else:
            score -= (position - 50) * 0.5  # 太靠后扣分
        
        # 长度分（10-50字符最佳）
        length = len(line)
        if 10 <= length <= 50:
            score += 20
        elif length < 5:
            score -= 20
        elif length > 80:
            score -= 10
        
        # Markdown标题格式加分
        if re.match(r'^#{1,2}\s+', line):
            score += 30
        
        # 包含书籍/论文特征词加分
        title_keywords = ['学', '论', '研究', '分析', '教程', '指南', '手册', 
                         '基础', '原理', '技术', '方法', '应用', '导论',
                         '概论', '通论', '新编', '实用', '现代', '当代']
        for kw in title_keywords:
            if kw in line:
                score += 5
        
        # 纯中文标题加分（书名通常是中文）
        chinese_ratio = len(re.findall(r'[\u4e00-\u9fa5]', line)) / max(len(line), 1)
        if chinese_ratio > 0.8:
            score += 10
        
        # 包含副标题符号（——、：）可能是标题
        if '——' in line or '：' in line or ':' in line:
            score += 5
        
        return score
    
    def _clean_title(self, title: str) -> str:
        """清理标题格式"""
        # 移除Markdown标题标记
        title = re.sub(r'^#{1,6}\s*', '', title)
        # 移除首尾空白
        title = title.strip()
        # 移除首尾标点
        title = re.sub(r'^[《「【\[]+', '', title)
        title = re.sub(r'[》」】\]]+$', '', title)
        return title
    
    def _extract_title_from_filename(self, filename: str) -> str:
        """从文件名提取标题（备选方案）"""
        import os
        name = os.path.splitext(os.path.basename(filename))[0]
        # 移除常见后缀
        name = re.sub(r'[-_]?(完整版|精校版|扫描版|PDF|epub|mobi)$', '', name, flags=re.IGNORECASE)
        return name
    
    # ==================== 版权页移除 ====================
    
    def _remove_copyright_pages(self, text: str) -> Tuple[str, bool]:
        """
        移除版权页内容
        
        版权页通常在文档最前面，包含ISBN、出版社、印次等信息
        策略：
        1. 扫描前200行
        2. 标记版权相关行
        3. 找到版权区域的结束边界
        """
        lines = text.split('\n')
        
        # 扫描前200行，标记哪些是版权行
        scan_limit = min(200, len(lines))
        copyright_lines = set()
        
        for i, line in enumerate(lines[:scan_limit]):
            if self._is_copyright_line(line.strip()):
                copyright_lines.add(i)
        
        if not copyright_lines:
            return text, False
        
        # 找到连续版权区域的结束位置
        # 策略：从最后一个版权行往后找，直到遇到正文内容
        last_copyright_idx = max(copyright_lines)
        copyright_end = last_copyright_idx + 1
        
        # 继续扫描，跳过空行和短行，直到遇到正文
        consecutive_content = 0
        for i in range(last_copyright_idx + 1, min(last_copyright_idx + 20, len(lines))):
            line = lines[i].strip()
            if not line:
                continue
            if self._is_copyright_line(line):
                copyright_end = i + 1
                consecutive_content = 0
            elif len(line) > 20 and not self._is_copyright_line(line):
                # 遇到较长的非版权内容
                consecutive_content += 1
                if consecutive_content >= 2:
                    break
        
        # 只有当版权行足够多时才移除
        if len(copyright_lines) >= 2:
            # 保留版权区域之后的内容
            text = '\n'.join(lines[copyright_end:])
            return text, True
        
        return text, False
    
    # ==================== 前言/序言移除 ====================
    
    def _remove_frontmatter(self, text: str) -> Tuple[str, List[str]]:
        """
        移除前言、序言、编委会等
        
        策略：
        1. 基于标题匹配
        2. 基于内容特征（编委会的人名列表等）
        """
        removed = []
        
        # 标题匹配移除
        matches = list(self.frontmatter_title_re.finditer(text))
        for match in reversed(matches):
            start = match.start()
            section_name = match.group(1).strip()
            
            # 找到下一个章节标题
            remaining = text[match.end():]
            next_title = re.search(
                r'\n#{1,3}\s+(?!' + '|'.join(self.FRONTMATTER_TITLES) + r')[^\n]+',
                remaining,
                re.IGNORECASE
            )
            
            if next_title:
                end = match.end() + next_title.start()
            else:
                # 如果没找到下一个标题，限制最多移除5000字符
                end = min(match.end() + 5000, len(text))
            
            text = text[:start] + text[end:]
            removed.append(section_name)
        
        # 编委会内容特征移除（大量人名列表）
        text, committee_removed = self._remove_committee_by_content(text)
        if committee_removed:
            removed.append("编委会")
        
        return text, removed
    
    def _remove_committee_by_content(self, text: str) -> Tuple[str, bool]:
        """基于内容特征移除编委会（人名列表）"""
        lines = text.split('\n')
        result_lines = []
        skip_mode = False
        skip_count = 0
        name_list_count = 0  # 连续人名列表行数
        removed = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 检测编委会开始标志
            if any(p.search(line_stripped) for p in self.committee_patterns):
                skip_mode = True
                skip_count = 0
                name_list_count = 0
                removed = True
                continue
            
            if skip_mode:
                # 空行：继续跳过但增加计数
                if not line_stripped:
                    skip_count += 1
                    if skip_count >= 3:
                        # 连续3个空行，退出跳过模式
                        skip_mode = False
                        result_lines.append(line)
                    continue
                
                # 检测是否还在人名列表区域
                if self._is_name_list_line(line_stripped):
                    name_list_count += 1
                    skip_count = 0
                    continue
                
                # 检测是否遇到章节标题或正文
                # 章节标题格式：第X章、1.1、## 等
                is_chapter = bool(re.match(
                    r'^(第?[一二三四五六七八九十\d]+[章节篇部]|'
                    r'\d+[\.\-]\d*\s|'
                    r'#{1,3}\s)',
                    line_stripped
                ))
                
                # 正文特征：较长的句子
                is_body_text = len(line_stripped) > 30 and not self._is_name_list_line(line_stripped)
                
                if is_chapter or is_body_text:
                    # 遇到章节或正文，退出跳过模式
                    skip_mode = False
                    result_lines.append(line)
                    continue
                
                # 其他短行：可能还是编委会相关内容
                skip_count += 1
                if skip_count >= 5:
                    # 连续5行非人名，退出跳过模式
                    skip_mode = False
                    result_lines.append(line)
            else:
                result_lines.append(line)
        
        return '\n'.join(result_lines), removed
    
    def _is_name_list_line(self, line: str) -> bool:
        """判断是否是人名列表行"""
        line = line.strip()
        if not line:
            return True  # 空行在人名列表中很常见
        
        # 长度检查（人名列表通常是短行）
        if len(line) > 40:
            return False
        
        # 排除章节标题格式
        if re.match(r'^第?[一二三四五六七八九十\d]+[章节篇部]', line):
            return False
        
        # 排除目录行（含页码）
        if re.search(r'[\.。…·]{3,}\s*\d+\s*$', line):
            return False
        
        # 排除正文句子（有句号且较长）
        if '。' in line and len(line) > 20:
            return False
        
        # 典型人名列表格式
        # 格式1: 多个人名用空格或逗号分隔
        name_pattern = r'[\u4e00-\u9fa5]{2,4}'
        names = re.findall(name_pattern, line)
        separators = len(re.findall(r'[,，\s、]+', line))
        if len(names) >= 2 and separators >= 1:
            # 但要排除正常句子
            if not re.search(r'[。！？，、].*[。！？，、]', line):  # 没有多重标点
                return True
        
        # 格式2: 职称+人名
        if re.match(r'^(教授|博士|主任|院长|所长|编辑|研究员|院士|副?主编?)[：:\s]*[\u4e00-\u9fa5]{2,4}$', line):
            return True
        
        # 格式3: 单位+人名列表  
        if re.match(r'^[\u4e00-\u9fa5]+[：:]\s*[\u4e00-\u9fa5\s,，、]+$', line) and len(line) <= 30:
            return True
        
        return False
    
    # ==================== 目录移除（增强版） ====================
    
    def _remove_toc_enhanced(self, text: str) -> Tuple[str, bool]:
        """
        增强版目录移除
        
        策略：
        1. 首先尝试标题匹配
        2. 然后基于内容特征检测目录行
        """
        removed = False
        
        # 方法1：标题匹配
        match = self.toc_title_re.search(text)
        if match:
            start = match.start()
            remaining = text[match.end():]
            
            # 找到下一个正文章节
            next_chapter = re.search(
                r'\n#{1,3}\s*第?[一二三四五六七八九十\d]+[章节篇]\s+[^\n]+',
                remaining,
                re.IGNORECASE
            )
            
            if next_chapter:
                end = match.end() + next_chapter.start()
            else:
                end = match.end() + self._find_toc_end_by_content(remaining)
            
            text = text[:start] + text[end:]
            removed = True
        
        # 方法2：内容特征检测（无标题的目录）
        text, content_removed = self._remove_toc_by_content(text)
        if content_removed:
            removed = True
        
        return text, removed
    
    def _find_toc_end_by_content(self, text: str) -> int:
        """基于内容特征找到目录结束位置"""
        lines = text.split('\n')
        toc_line_count = 0
        last_toc_line = 0
        
        for i, line in enumerate(lines):
            if any(p.match(line.strip()) for p in self.toc_line_patterns):
                toc_line_count += 1
                last_toc_line = i
            elif line.strip() and toc_line_count > 0:
                # 遇到非目录行
                non_toc_count = i - last_toc_line
                if non_toc_count > 5:
                    # 连续5行非目录，认为目录结束
                    break
        
        if toc_line_count >= self.toc_detect_threshold:
            return sum(len(l) + 1 for l in lines[:last_toc_line + 1])
        return 0
    
    def _remove_toc_by_content(self, text: str) -> Tuple[str, bool]:
        """基于内容特征移除目录（无标题情况）"""
        lines = text.split('\n')
        result_lines = []
        toc_buffer = []
        in_potential_toc = False
        
        for line in lines:
            is_toc_line = any(p.match(line.strip()) for p in self.toc_line_patterns)
            
            if is_toc_line:
                toc_buffer.append(line)
                in_potential_toc = True
            else:
                if in_potential_toc:
                    # 检查缓冲区是否达到目录阈值
                    if len(toc_buffer) >= self.toc_detect_threshold:
                        # 确认是目录，丢弃缓冲区
                        toc_buffer = []
                    else:
                        # 不是目录，恢复缓冲区内容
                        result_lines.extend(toc_buffer)
                        toc_buffer = []
                    in_potential_toc = False
                
                result_lines.append(line)
        
        # 处理末尾的缓冲区
        if toc_buffer and len(toc_buffer) < self.toc_detect_threshold:
            result_lines.extend(toc_buffer)
        
        removed = len(result_lines) < len(lines)
        return '\n'.join(result_lines), removed
    
    # ==================== 附录移除 ====================
    
    def _remove_appendix(self, text: str) -> Tuple[str, bool]:
        """移除附录、参考文献等"""
        match = self.appendix_title_re.search(text)
        if match:
            # 从附录标题开始，移除到文档末尾
            text = text[:match.start()]
            return text, True
        return text, False
    
    # ==================== PDF分页断行合并（新增） ====================
    
    def _merge_broken_paragraphs(self, text: str) -> Tuple[str, int]:
        """
        合并因PDF分页而断开的段落
        
        检测逻辑：
        1. 当前行不以句末标点结尾
        2. 下一行不是新段落的开始（如标题、编号、图表等）
        3. 当前行长度足够（避免误合并短行如标题）
        
        Returns:
            (处理后的文本, 合并次数)
        """
        lines = text.split('\n')
        if len(lines) <= 1:
            return text, 0
        
        result_lines = []
        merge_count = 0
        i = 0
        
        while i < len(lines):
            current_line = lines[i].strip()
            
            # 空行直接保留
            if not current_line:
                result_lines.append('')
                i += 1
                continue
            
            # 检查是否需要与下一行合并
            should_merge = False
            
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                
                # 条件判断
                if next_line and self._should_merge_lines(current_line, next_line):
                    should_merge = True
            
            if should_merge:
                # 合并当前行和下一行
                # 处理中英文连接：中文不加空格，英文加空格
                merged = self._merge_two_lines(current_line, next_line)
                
                # 继续检查是否需要与更多行合并
                i += 2
                while i < len(lines):
                    next_next_line = lines[i].strip()
                    if next_next_line and self._should_merge_lines(merged, next_next_line):
                        merged = self._merge_two_lines(merged, next_next_line)
                        merge_count += 1
                        i += 1
                    else:
                        break
                
                result_lines.append(merged)
                merge_count += 1
            else:
                result_lines.append(current_line)
                i += 1
        
        return '\n'.join(result_lines), merge_count
    
    def _should_merge_lines(self, current: str, next_line: str) -> bool:
        """
        判断两行是否应该合并
        
        Returns:
            True 如果应该合并
        """
        # 1. 当前行以句末标点结尾 → 不合并
        if self.sentence_end_punct.search(current):
            return False
        
        # 2. 当前行太短（可能是标题）→ 不合并
        if len(current) < 10:
            return False
        
        # 3. 下一行是新段落开始 → 不合并
        if self.new_para_start.match(next_line):
            return False
        
        # 4. 下一行是空行 → 不合并
        if not next_line:
            return False
        
        # 5. 当前行是标题格式 → 不合并
        if current.startswith('#') or re.match(r'^第[一二三四五六七八九十\d]+[章节篇部]', current):
            return False
        
        # 【新增】6. 当前行或下一行是图表标识 → 不合并
        fig_pattern = r'^(图|表|附图|附表|[Ff]ig(?:ure)?\.?|[Tt]able\.?)\s*[\d\.\-]'
        if re.match(fig_pattern, current) or re.match(fig_pattern, next_line):
            return False
        
        # 【新增】7. 当前行或下一行是来源/注释 → 不合并
        source_pattern = r'^(来源|资料来源|注|[Ss]ource|[Nn]ote)[：:\s]'
        if re.match(source_pattern, current) or re.match(source_pattern, next_line):
            return False
        
        # 8. 下一行以小写字母开头（英文句子中间断开）→ 合并
        if re.match(r'^[a-z]', next_line):
            return True
        
        # 9. 当前行以连字符结尾（英文单词断开）→ 合并
        if current.endswith('-'):
            return True
        
        # 10. 当前行以中文字符结尾，下一行以中文字符开头 → 可能需要合并
        current_ends_chinese = bool(re.search(r'[\u4e00-\u9fa5]$', current))
        next_starts_chinese = bool(re.match(r'^[\u4e00-\u9fa5]', next_line))
        
        if current_ends_chinese and next_starts_chinese:
            # 未完成的句子：不以句号结尾
            return True
        
        # 【新增】11. 当前行以逗号结尾，下一行是中文 → 合并（明显是句子中断）
        if re.search(r'[，,]$', current) and next_starts_chinese:
            return True
        
        # 11. 当前行以英文字母/数字结尾，下一行以英文开头 → 可能需要合并
        current_ends_alnum = bool(re.search(r'[a-zA-Z0-9]$', current))
        next_starts_alpha = bool(re.match(r'^[a-zA-Z]', next_line))
        
        if current_ends_alnum and next_starts_alpha:
            return True
        
        return False
    
    def _merge_two_lines(self, line1: str, line2: str) -> str:
        """
        合并两行文本，智能处理空格
        
        - 中文之间：不加空格
        - 英文之间：加空格
        - 中英混合：根据情况决定
        - 连字符断词：移除连字符直接连接
        """
        # 处理连字符断词
        if line1.endswith('-'):
            # 检查是否是英文单词断开
            if re.search(r'[a-zA-Z]-$', line1):
                return line1[:-1] + line2
        
        # 判断连接处是否需要空格
        line1_end = line1[-1] if line1 else ''
        line2_start = line2[0] if line2 else ''
        
        # 中文与中文之间不加空格
        is_chinese_end = bool(re.match(r'[\u4e00-\u9fa5]', line1_end))
        is_chinese_start = bool(re.match(r'[\u4e00-\u9fa5]', line2_start))
        
        if is_chinese_end and is_chinese_start:
            return line1 + line2
        
        # 英文与英文之间加空格
        is_alpha_end = bool(re.match(r'[a-zA-Z0-9]', line1_end))
        is_alpha_start = bool(re.match(r'[a-zA-Z]', line2_start))
        
        if is_alpha_end and is_alpha_start:
            return line1 + ' ' + line2
        
        # 其他情况：中英混合，通常不加空格
        return line1 + line2
    
    # ==================== 图表标识移除（新增） ====================
    
    def _remove_figure_table_markers(self, text: str) -> Tuple[str, int]:
        """
        移除穿插在正文中的图表标识
        
        包括：
        - 图1 xxx / 表1 xxx / Figure 1 / Table 1
        - 来源: xxx / 注: xxx
        - 图表内残留的纯数字行
        - 图片占位符 [图1] 等
        
        Returns:
            (处理后的文本, 移除行数)
        """
        lines = text.split('\n')
        result_lines = []
        removed_count = 0
        
        # 用于检测连续的图表相关行（如图表标题+来源+注释）
        consecutive_fig_lines = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 空行保留
            if not line_stripped:
                result_lines.append(line)
                consecutive_fig_lines = 0
                continue
            
            # 检查是否匹配图表标识模式
            is_figure_table = False
            for pattern in self.figure_table_patterns:
                if pattern.match(line_stripped):
                    is_figure_table = True
                    break
            
            # 额外检查：上下文判断
            if not is_figure_table:
                # 检查是否是图表附近的短行（可能是表格单元格残留）
                is_figure_table = self._is_table_cell_residue(line_stripped, lines, i)
            
            if is_figure_table:
                removed_count += 1
                consecutive_fig_lines += 1
                
                # 如果移除了很多连续行，可能误删了正文，发出警告
                if consecutive_fig_lines > 10:
                    # 回退：可能不是图表区域
                    # 这里选择保守策略，继续移除
                    pass
            else:
                result_lines.append(line)
                consecutive_fig_lines = 0
        
        return '\n'.join(result_lines), removed_count
    
    def _is_table_cell_residue(self, line: str, all_lines: List[str], current_idx: int) -> bool:
        """
        判断是否是表格单元格残留
        
        表格残留特征：
        - 很短的行（<10字符）
        - 主要是数字或简短词汇
        - 周围有其他类似的短行
        """
        # 行太长，不是表格残留
        if len(line) > 15:
            return False
        
        # 检查是否主要是数字
        digit_ratio = len(re.findall(r'[\d\.\,\%]', line)) / max(len(line), 1)
        if digit_ratio > 0.6 and len(line) < 10:
            # 检查上下文是否也是短行（表格特征）
            short_neighbors = 0
            for offset in [-2, -1, 1, 2]:
                neighbor_idx = current_idx + offset
                if 0 <= neighbor_idx < len(all_lines):
                    neighbor = all_lines[neighbor_idx].strip()
                    if neighbor and len(neighbor) < 15:
                        short_neighbors += 1
            
            # 如果周围有多个短行，可能是表格区域
            if short_neighbors >= 2:
                return True
        
        return False
    
    # ==================== 清理PDF/LaTeX残留 ====================
    
    def _clean_artifacts(self, text: str) -> str:
        """清理PDF转换和LaTeX残留"""
        # LaTeX清洗
        for pattern, replacement in self.latex_patterns:
            text = pattern.sub(replacement, text)
        
        # PDF残留清洗
        for pattern, replacement in self.pdf_patterns:
            text = pattern.sub(replacement, text)
        
        # 工具噪音
        text = self.tool_noise_re.sub('', text)
        
        return text
    
    # ==================== 页眉页脚移除 ====================
    
    def _remove_headers_footers(self, text: str) -> str:
        """移除页眉页脚"""
        lines = text.split('\n')
        result = []
        
        for line in lines:
            # 检查是否匹配页眉页脚模式
            is_header_footer = any(p.match(line) for p in self.header_footer_re)
            
            if not is_header_footer:
                result.append(line)
        
        return '\n'.join(result)
    
    # ==================== 空白规范化 ====================
    
    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 移除行首尾空白
        lines = [line.strip() for line in text.split('\n')]
        
        # 合并连续空行
        result = []
        prev_empty = False
        for line in lines:
            if not line:
                if not prev_empty:
                    result.append('')
                prev_empty = True
            else:
                result.append(line)
                prev_empty = False
        
        # 移除首尾空行
        while result and not result[0]:
            result.pop(0)
        while result and not result[-1]:
            result.pop()
        
        return '\n'.join(result)
    
    # ==================== 短行过滤 ====================
    
    def _filter_short_lines(self, text: str) -> str:
        """过滤噪音短行"""
        lines = text.split('\n')
        result = []
        
        for line in lines:
            stripped = line.strip()
            
            # 保留空行（段落分隔）
            if not stripped:
                result.append(line)
                continue
            
            # 保留标题行
            if stripped.startswith('#'):
                result.append(line)
                continue
            
            # 保留足够长的行
            if len(stripped) >= self.min_line_length:
                result.append(line)
        
        return '\n'.join(result)


# ==================== 便捷函数 ====================

def clean_text(text: str, **kwargs) -> str:
    """清洗文本（返回纯文本）"""
    cleaner = TextCleaner(**kwargs)
    return cleaner.clean(text).text


def clean_document(text: str, source: str = "", show_progress: bool = False, **kwargs) -> CleanResult:
    """清洗文档（返回完整结果，含标题）"""
    cleaner = TextCleaner(**kwargs)
    return cleaner.clean(text, source=source, show_progress=show_progress)


def extract_title(text: str, source: str = "") -> str:
    """仅提取标题"""
    cleaner = TextCleaner(
        extract_title=True,
        remove_frontmatter=False,
        remove_toc=False,
        remove_copyright=False,
        remove_headers=False,
        clean_pdf_artifacts=False
    )
    return cleaner.clean(text, source=source).title


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试样例
    sample_text = open('./test_data/_12183172.md', 'r', encoding='utf-8').read()
    print("=" * 60)
    print("测试增强版文本清洗器")
    print("=" * 60)
    
    cleaner = TextCleaner()
    result = cleaner.clean(sample_text, show_progress=True)
    
    print(f"\n📖 提取的标题: {result.title}")
    print(f"\n📄 清洗后文本预览:\n{'-'*40}")
    print(result.text[0:500])
    
    print(f"\n{'='*60}")
    print("测试PDF断行合并和图表标识移除")
    print("=" * 60)
