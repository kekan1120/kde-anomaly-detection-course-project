# 提交前检查清单（含当前状态）

> 更新：2026-11-27 15:10　|　截止：**2026-12-01 23:41**　|　入口：超星学习通「分组任务」→ 组长「开始作答」
> 打包脚本：`07_submission/build_submission.py`（可重复运行，幂等）

## 0. 已生成的两份提交文件（PDF 推荐提交，DOCX 为可编辑源）

| 文件 | 内容 | 大小 | 状态 |
|---|---|---|---|
| `07_submission/topic_report.pdf` | 专题探究论文 PDF（**16 页**，7 图 4 表，公式 OMML 渲染、页码齐全） | 833 KB | ✅ **推荐提交** |
| `07_submission/human_ai_process_record.pdf` | 人机协作流程记录 PDF（38 页，四成员完整记录） | 675 KB | ✅ **推荐提交** |
| `07_submission/topic_report.docx` | 论文 Word 源（中文图、宋体/Times New Roman、页码） | 488 KB | ✅ 可编辑备用 |
| `07_submission/human_ai_process_record.docx` | 流程记录 Word 源 | 62 KB | ✅ 可编辑备用 |

> 生成链：`build_submission.py`（md→docx）→ `polish_docx.py`（字体/页码）→ office 工具（docx→pdf）。
> 全链路可重复执行；源文件为 `06_paper/course_report.md` 与 `process-logs/member_*.md`。

## 1. 专题探究论文（45 分）

- [x] Word 排版完成（pandoc 生成，公式转 OMML、图已嵌入）
- [x] 封面：组名「瓦洛兰特」、题目、A/B/C/D 姓名、组长、各自工作量
- [x] 摘要 **245 字**（150–250 区间内）
- [x] 关键词（见正文，需最终核对 3–5 个）
- [x] 公式、术语、概率 vs 概率密度、分数方向由 A 复核
- [x] 主结果只引 `05_results/main/metrics.csv`（C 复核：0 处跨版本混用）
- [x] 图 1–7 文件、图注、轴名、参数齐全（含 3 个子智能体检查修正：图 6 轴名、正文图引用）
- [x] 图表数字可由 CSV/JSON 重建
- [x] H1–H4 均有支持/推翻条件与实际判定；H4 未把测试最优带宽写成事前选参
- [x] 讨论含 v1.0 far-only 主结果、合成数据与高维/超参数局限；附录含 v1.1 版本边界说明
- [x] 正文未引 near 数字；附录注明 v1.1 为 post-hoc 分层补充、不进入主表
- [x] 未跨版本比较 AUC/AP
- [x] 参考文献 DOI/ISBN/URL/页码/访问日期已补齐（`theory-note.md` §8）
- [x] 非主笔成员复核数字（`06_paper/c_review_of_D.md`，32 项）

## 2. 人机协作流程记录（55 分）

- [x] 四份成员记录合并为一份（`human_ai_process_record.md` → docx）
- [x] 每名成员均含：真实提示词、模型输出摘要、人工核验动作、纠错/拒绝理由、最终采用
- [x] D 的 `member_D.md` 已填真实 DeepSeek 链接与回合
- [x] **B 的会话分享链接已补**（DSH 导出凭证 `member_B_session_export.md`，B 本人于 2026-11-27 补填）
- [x] **C 的会话分享链接已确认**（DSH 导出凭证 `member_C_session_export.md`，decision-log #25；按 `docs/session-link-policy.md` 为等价凭证）
- [x] 未虚构模型输出、错误、链接或核验结果（各记录均标注真实来源）
- [x] 小组人机协作范式总结已写入（「先限定、再推导、必核验、后采用」五步）

## 3. 阶段 0 与协作闭环

- [x] A/B/C/D 在 `stage0-closure-checklist.md` 2.3 与三 全签
- [x] 互审闭环：A 审 B、B 审 C、C 审 D、D 审 A（均有证据文件）
- [x] 组长确认 v1.0 far-only 主结果口径（`PROJECT_STATUS.md`）
- [x] B-v1.1 已签署；C 正式 v1.1 结果已产出（`05_results/main_v1_1_near/`），未覆盖 v1.0 冻结结果
- [x] GitHub 工作树干净、提交文件可打开
- [ ] 临时文件清理（可选：`__pycache__` 已在 .gitignore）

## 4. 阻塞提交的待办

| # | 事项 | 责任人 | 状态 |
|---|---|---|---|
| 1 | B 的会话分享链接 | B | ✅ 已补（DSH 导出凭证） |
| 2 | C 的替代凭证 | C + A | ✅ 已确认（decision-log #25） |
| 3 | **最终提交** | **A** | ⬜ 超星「开始作答」 |

## 5. 提交文件名建议

- `瓦洛兰特_人机协作流程记录_v1.0.docx`
- `瓦洛兰特_专题探究论文_v1.0.docx`

若入口要求合并为一个文件，再生成合并副本；仓库内保留两份独立源文件以便追溯。
