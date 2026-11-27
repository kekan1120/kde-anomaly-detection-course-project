# -*- coding: utf-8 -*-
"""生成课程提交用的两份 DOCX（预演打包，可重复运行）。

用法：
    python 07_submission/build_submission.py

输入：
    process-logs/member_A.md ~ member_D.md  → 合并为 07_submission/human_ai_process_record.md
    06_paper/course_report.md               → 直接转 docx
输出：
    07_submission/human_ai_process_record.docx
    07_submission/topic_report.docx

依赖：pandoc（PATH 中可用）。
"""
import os
import subprocess
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUB = os.path.join(PROJ, "07_submission")
PLOG = os.path.join(PROJ, "process-logs")

MEMBERS = [
    ("member_A.md", "一、成员 A · 林辰旭（组长兼理论负责人）"),
    ("member_B.md", "二、成员 B · 连昭悦（数据与实验设计）"),
    ("member_C.md", "三、成员 C · 沈伊镄（实现与复现）"),
    ("member_D.md", "四、成员 D · 陈永喆（结果分析与论文整合）"),
]

HEAD = """# 瓦洛兰特小组 · 人机协作流程记录

## 封面信息

- 课程：机器学习 · 人机协作分组课程报告
- 小组：**瓦洛兰特**
- 组长：A 林辰旭（理论、文献与项目组织，7–10 h）
- 成员 B：连昭悦（数据与实验设计，7–10 h）
- 成员 C：沈伊镄（实现、复现与核验，8–11 h）
- 成员 D：陈永喆（结果分析、论文整合与提交清单，8–11 h）
- 日期：2026-11-27
- 说明：本文件为课程要求的「人机协作流程记录」（55 分），由四名成员各自账号下同一连续会话的真实交互记录合并而成；每条记录均含真实提示词、模型输出摘要、人工核验动作与最终采用决定。

## 小组人机协作范式总结

本项目稳定采用「**先限定、再推导、必核验、后采用**」的五步范式：

1. **先限定问题与符号**：开工前由 A 锁定研究问题、假设、符号与得分/阈值方向，避免后续反复漂移。
2. **模型只出草稿**：让模型提供推导草稿、代码骨架、图表脚本与文献要点，明确**不得代下结论**。
3. **用可复查动作核验**：手算特例（如 KDE 手算 0.5558）、断言（分数方向、混淆矩阵自洽）、独立实现重跑（C 的 50 项对账 0 偏差）、脚本核验（32 项数字复核）——不写「已审核」这种空话。
4. **如实记录错误并修正**：A 侧设计被 C 证伪（球壳边界标签矛盾、鞍部紧凑簇非空区）、配置口径被纠正（H4 不得把测试最优当选择准则）、版本口径被修正（far-only 冻结 vs near post-hoc）——全部保留证据链。
5. **最后人工决定采用或拒绝**：每份记录都有「最终采用」栏，说明采用、改写或拒绝及理由。

**分工与互审闭环**：A 审 B（数据协议）→ B 审 C（实现与复现）→ C 审 D（论文图表与数字）→ D 审 A（理论与文献）；四人各主责一块、各审一块，核心推导、实验协议、实现与结论均有独立检查人。

"""


def merge_process_logs() -> str:
    parts = [HEAD]
    for fname, title in MEMBERS:
        path = os.path.join(PLOG, fname)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        lines = content.split("\n")
        if lines and lines[0].startswith("# "):
            lines = lines[1:]
        body = "\n".join(lines).strip()
        parts.append(f"\n---\n\n## {title}\n\n{body}\n")
    out = os.path.join(SUB, "human_ai_process_record.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return out


def pandoc_to_docx(md: str, docx: str, resource_path: str = None) -> None:
    cmd = ["pandoc", md, "-o", docx]
    if resource_path:
        cmd.append(f"--resource-path={resource_path}")
    print("run:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    os.makedirs(SUB, exist_ok=True)
    merged = merge_process_logs()
    print("merged:", merged)

    paper_md = os.path.join(PROJ, "06_paper", "course_report.md")
    pandoc_to_docx(paper_md, os.path.join(SUB, "topic_report.docx"),
                   resource_path=os.path.join(PROJ, "06_paper"))
    pandoc_to_docx(merged, os.path.join(SUB, "human_ai_process_record.docx"))

    for name in ("topic_report.docx", "human_ai_process_record.docx"):
        p = os.path.join(SUB, name)
        print(f"OK  {name}  {os.path.getsize(p)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
