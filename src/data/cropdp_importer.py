# -*- coding: utf-8 -*-
"""
CropDP-KG 原始数据导入器
将 knowledge_bases/cropdp_docs/data*.xls（中国农作物病虫害知识图谱原始爬取数据）
转换为结构化中文文本段落，输出到 knowledge_bases/agri_knowledge_docs/cropdp/*.txt，
供 kb_builder 清洗分块入库。

字段（来源：data0~data6.xls, sheet1）：
    名称 / 英文名 / 简介 / 为害症状 / 发生规律 / 防治

用法：
    python -m src.data.cropdp_importer
"""
import re
from pathlib import Path

import pandas as pd


def _clean(text) -> str:
    """规整单格文本：去首尾空白、合并连续空白与断行。"""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    s = str(text)
    # 全角/半角空格、制表符归一
    s = s.replace("\u3000", " ").replace("\xa0", " ")
    # 合并段内多余换行/空格（保留句读）
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def build_record(row) -> str:
    """把一行表格转成一段结构化文本知识卡。"""
    name = _clean(row.get("名称"))
    en = _clean(row.get("英文名"))
    intro = _clean(row.get("简介"))
    symptom = _clean(row.get("为害症状"))
    pattern = _clean(row.get("发生规律"))
    control = _clean(row.get("防治"))

    if not name:
        return ""

    parts = [f"【病虫害名称】{name}"]
    if en:
        parts.append(f"【英文名】{en}")
    if intro:
        parts.append(f"【简介】{intro}")
    if symptom:
        parts.append(f"【为害症状】{symptom}")
    if pattern:
        parts.append(f"【发生规律】{pattern}")
    if control:
        parts.append(f"【防治方法】{control}")

    return "\n".join(parts)


def main():
    root = Path(__file__).resolve().parents[2]  # modelspace_space/
    src_dir = root / "knowledge_bases" / "cropdp_docs"
    out_dir = root / "knowledge_bases" / "agri_knowledge_docs" / "cropdp"
    out_dir.mkdir(parents=True, exist_ok=True)

    xls_files = sorted(src_dir.glob("data*.xls"))
    if not xls_files:
        print(f"⚠️ 未在 {src_dir} 找到 data*.xls")
        return

    total_records = 0
    for xf in xls_files:
        try:
            df = pd.read_excel(xf, sheet_name=0)
        except Exception as e:
            print(f"❌ 读取失败 {xf.name}: {e}")
            continue

        # 列名兼容：去空格
        df.columns = [str(c).strip() for c in df.columns]

        records = []
        for _, row in df.iterrows():
            block = build_record(row)
            if block:
                records.append(block)

        out_path = out_dir / f"{xf.stem}.txt"
        out_path.write_text("\n\n".join(records), encoding="utf-8")

        total_records += len(records)
        print(f"  ✓ {xf.name}: {len(df)} 行 -> {len(records)} 条知识卡 -> {out_path.name}")

    print(f"\n✅ CropDP 转换完成: {len(xls_files)} 个文件 / 共 {total_records} 条知识卡")
    print(f"   输出目录: {out_dir}")


if __name__ == "__main__":
    main()
