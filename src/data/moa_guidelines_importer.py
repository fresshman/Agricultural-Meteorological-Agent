# -*- coding: utf-8 -*-
"""
农业农村部/省厅技术规程导入器
将 knowledge_bases/moa_guidelines/ 下的 PDF 与 HTML 提取为完整文本，
输出到 knowledge_bases/agri_knowledge_docs/moa_guidelines/*.txt，
供 kb_builder 清洗分块入库。

设计原则（用户要求）：
- 内容完整：保留适用范围、前提条件、约束（"应/宜/不宜"、"当…时"、编号条款），不做激进删减；
- 只去无关噪音（网页导航/样式/脚本），技术正文一字不删。

用法：
    python -m src.data.moa_guidelines_importer
"""
import re
from pathlib import Path

import fitz  # pymupdf
from bs4 import BeautifulSoup


def _norm_lines(text: str) -> str:
    """规整空白，但保留段落与条款换行。"""
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 合并行尾的软换行（中文续行），但保留空行作为段落分隔
    lines = [ln.rstrip() for ln in text.split("\n")]
    out = []
    for ln in lines:
        if ln.strip() == "":
            out.append("")
        else:
            out.append(ln)
    text = "\n".join(out)
    # 3 个以上空行压成 2 个
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(pdf_path: Path) -> str:
    """逐页提取 PDF 文本，保留条款结构。"""
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        t = page.get_text("text") or ""
        pages.append(t)
    doc.close()
    return _norm_lines("\n".join(pages))


def extract_html(html_path: Path) -> str:
    """提取政府网页正文：去导航/样式/脚本，保留段落与条款。"""
    raw = html_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "lxml")

    # 移除无关节点
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer",
                     "form", "button", "iframe", "svg"]):
        tag.decompose()

    # 优先取正文容器；找不到则用 body
    main = None
    for sel in ["#con", "#content", ".content", ".article", ".TRS_Editor",
                "#zoom", ".zoom", ".detail", ".main", "article"]:
        main = soup.select_one(sel)
        if main and len(main.get_text(strip=True)) > 200:
            break
    if main is None:
        main = soup.body or soup

    # 按行提取并去重（政府网页正文常因嵌套结构重复输出）
    text = main.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.split("\n")]
    seen = set()
    out = []
    for ln in lines:
        if not ln:
            out.append("")
            continue
        # 整行去重（去掉嵌套造成的重复段落）
        if ln in seen:
            continue
        seen.add(ln)
        out.append(ln)
    return _norm_lines("\n".join(out))


def _split_sections(text: str) -> str:
    """在小节标题前插入段落分隔，避免整份文件被合成单个超大 chunk。
    匹配：一、 二、 / （一）（二） / 4.2 4.3 这类编号标题。
    """
    text = re.sub(r'(?m)^([一二三四五六七八九十]+、)', r'\n\n\1', text)
    text = re.sub(r'(?m)（([一二三四五六七八九十]+）)', r'\n\n（\1', text)
    text = re.sub(r'(?m)^(\d+(?:\.\d+)+)\s', r'\n\n\1 ', text)
    return text


def main():
    root = Path(__file__).resolve().parents[2]
    src_dir = root / "knowledge_bases" / "moa_guidelines"
    out_dir = root / "knowledge_bases" / "agri_knowledge_docs" / "moa_guidelines"
    out_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(src_dir.glob("*.pdf"))
    htmls = sorted(src_dir.glob("*.html"))

    print(f"发现 PDF: {len(pdfs)} 个, HTML: {len(htmls)} 个")

    for f in pdfs + htmls:
        try:
            if f.suffix.lower() == ".pdf":
                text = extract_pdf(f)
            else:
                text = extract_html(f)
        except Exception as e:
            print(f"  ❌ 提取失败 {f.name}: {e}")
            continue

        if len(text) < 100:
            print(f"  ⚠️  内容过短，跳过 {f.name} ({len(text)} 字符)")
            continue

        # 按小节标题断段，避免整份文件合成单个超大 chunk
        text = _split_sections(text)

        out = out_dir / (f.stem + ".txt")
        out.write_text(text, encoding="utf-8")
        print(f"  ✓ {f.name} -> {out.name}  ({len(text)} 字符)")

    print(f"\n✅ 提取完成，输出目录: {out_dir}")


if __name__ == "__main__":
    main()
