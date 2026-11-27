# -*- coding: utf-8 -*-
"""提交件排版后处理：统一中英文字体 + 页脚页码。

用法：
    python 07_submission/polish_docx.py

对 07_submission/ 下的两份 docx 执行：
1. 正文/标题样式设置字体：西文 Times New Roman，中文 宋体（eastAsia）
2. 页脚居中插入页码（PAGE 域）
不改变内容，仅排版。
"""
import os
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

SUB = os.path.dirname(os.path.abspath(__file__))
FILES = ["topic_report.docx", "human_ai_process_record.docx"]

LATIN = "Times New Roman"
EAST_ASIA = "宋体"


def _set_style_font(style, latin=LATIN, east_asia=EAST_ASIA):
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:ascii"), latin)
    rFonts.set(qn("w:hAnsi"), latin)
    rFonts.set(qn("w:eastAsia"), east_asia)


def _add_page_number_footer(doc):
    for section in doc.sections:
        footer = section.footer
        p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = "PAGE"
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        run._r.append(fld_begin)
        run._r.append(instr)
        run._r.append(fld_end)


def polish(path: str) -> None:
    doc = Document(path)
    # 统一所有样式的字体（含 pandoc 生成的 Body Text / First Paragraph / Compact 等）
    for style in doc.styles:
        try:
            if style.type is not None and hasattr(style, "element"):
                _set_style_font(style)
        except Exception:
            continue
    # 段落内 run 也显式设置一遍（防止样式继承失效）
    for p in doc.paragraphs:
        for r in p.runs:
            r.font.name = LATIN
            r._element.get_or_add_rPr()
            rFonts = r._element.rPr.get_or_add_rFonts()
            rFonts.set(qn("w:eastAsia"), EAST_ASIA)
    _add_page_number_footer(doc)
    doc.save(path)
    print(f"polished: {os.path.basename(path)}")


def main() -> int:
    for f in FILES:
        p = os.path.join(SUB, f)
        if os.path.exists(p):
            polish(p)
        else:
            print(f"skip (missing): {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
