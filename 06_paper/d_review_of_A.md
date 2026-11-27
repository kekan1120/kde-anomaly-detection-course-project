# D 对 A 理论与文献材料的交叉复核

| 项目 | 内容 |
|---|---|
| 复核人 | D 陈永喆 |
| 被复核人 | A 林辰旭（理论与文献负责人） |
| 复核日期 | 2026-11-27 |
| 复核范围 | `docs/theory-note.md`、`docs/research-questions-hypotheses.md`、`docs/paper-citation-guide.md`、论文 §2 与参考文献 |
| 复核性质 | D→A 交叉复核；不替代 A 对原始文献的最终核验 |

## 核对动作与结果

| 核对项 | 证据位置 | 结果 |
|---|---|---|
| KDE 定义、核函数归一化与带宽缩放 | `theory-note.md` §1–§2；论文 §2.2 | 通过。$1/(nh^d)$、高斯核归一化和各向同性标量带宽在两处一致。 |
| 概率与概率密度区分 | `theory-note.md` §4；论文 §1.2 | 通过。正文明确单点概率、区域积分和密度值不必属于 $[0,1]$。 |
| KDE 异常分数与阈值方向 | `theory-note.md` §5；`research-questions-hypotheses.md` §3；论文 §2.2 | 通过。统一为负对数密度、分数越大越异常，阈值来自正常验证集。 |
| LOF 概念边界与 novelty 约束 | `theory-note.md` §6；论文 §2.3 | 通过。正文将 LOF 写成局部相对稀疏度，不称为概率密度，并写明 `novelty=True` 与训练正常样本拟合。 |
| H1–H4 可证伪性 | `research-questions-hypotheses.md` §2；论文 §3.1 | 通过。支持条件、推翻条件和 H4 的“测试 AUC 仅事后描述”口径一致。 |
| 参考文献真实性与论文引用映射 | `theory-note.md` §8；论文 §2、§3.4、参考文献 | 通过内容映射。四类来源均能在 A 的已核验文献表中定位。 |

## 需 A 在最终排版前确认的事项

1. 教材 [5] 的最终正文引用应按课程要求补充章节或页码；`theory-note.md` 当前注明“引用时按章节补页码”。
2. `docs/paper-citation-guide.md` 中的图目录和 v1.1 状态属于历史口径，最终提交材料应以 `course_report.md`、`c_review_of_D.md` 和 `05_results/main_v1_1_near/` 的当前状态为准。

以上两点是文档维护事项，不改变 v1.0 far-only 主结果、公式或假设判定。D 已将核对结果反馈给 A，等待 A 在最终排版时确认。
