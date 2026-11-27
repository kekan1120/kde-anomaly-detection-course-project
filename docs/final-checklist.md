# 项目收尾清单（一页纸）

> 更新：2026-11-27　|　截止：**2026-12-01 23:41**
> 组长：A 林辰旭　|　组名：瓦洛兰特

## 一、A 侧（已完成 ✅）

- [x] 理论说明 `docs/theory-note.md`（A 已核验全部通过）
- [x] 可证伪假设 `docs/research-questions-hypotheses.md`
- [x] 术语表 `docs/glossary.md`（含 `inverted_cdf` 口径）
- [x] 决策日志 `docs/decision-log.md`（#1–#20 + 待办 #21–24）
- [ ] 阶段 0 关闭包 `docs/stage0-closure-checklist.md`（待 C 的 2.3 确认及 B/C 会话链接）
- [x] B-v1.1 提案 `docs/protocol-change-B-v1.1.md` → B 已签署
- [x] 论文引用口径 `docs/paper-citation-guide.md`
- [x] 论文写作任务书 `docs/paper-writing-brief-for-D.md`
- [x] 会话记录 `process-logs/member_A.md`（9 回合，A 已核验）
- [x] 参考文献 DOI/ISBN/URL/页码/访问日期 + 教材（李航《机器学习方法》2022）

## 二、C（实现与复现）剩余

- [x] 补 `04_code/run_checks.py` 的 **C3/C14** 适配（见 `05_results/main_v1_1_near/sanity_checks.md`）
- [x] 跑 **v1.1 正式结果**（独立目录 `05_results/main_v1_1_near/`，未覆盖 v1.0）
- [ ] 复核 D 的图表与正文数字（逐项回对 C 的结果）
- [ ] 阶段 0 检查清单 C 行确认 + `member_C.md` 补会话链接（C3/C14 和正式结果已完成）

## 三、D（分析与论文）剩余

- [x] 论文正文 `06_paper/course_report.md`（按 `docs/paper-writing-brief-for-D.md`；待 A 排版、C 复核）
- [x] 阶段 0 检查清单 D 行签字 + `member_D.md` 真实回合与会话链接

## 四、阶段 0 关闭（全组）

- [ ] C 在 `docs/stage0-closure-checklist.md` 的 2.3 确认（D 已完成）
- [ ] 四份记录均有会话链接（A/D 已填；C 用 `/export` 凭证待确认；**B 待填**）
- [ ] A 在 `PROJECT_STATUS.md` 标记「阶段 0 已关闭」

## 五、提交前 12 项检查

- [ ] 封面：组名「瓦洛兰特」+ 四名成员姓名 + 工作量 + 组长 A
- [ ] 两份文件齐全：人机协作流程记录 + 专题探究论文
- [ ] 摘要 150–250 字
- [ ] 关键词 3–5 个
- [ ] 每张图在正文有引用与解释
- [ ] 主检测数字能回对 `05_results/main/metrics.csv`；E0、多种子和审计计数单独标明各自来源与边界
- [ ] 全文无 near / `compact_void` / `ai_draft` 的数字
- [ ] AUC/AP 未跨版本比较
- [ ] 参考文献真实可查（DOI/ISBN/URL 见 `theory-note.md` §8）
- [ ] 四份过程记录含可访问的会话分享链接
- [ ] 论文含固定随机种子与复现说明
- [ ] 提交入口：超星学习通「分组任务」→ 组长「开始作答」

## 六、时间倒排

| 时间 | 里程碑 | 责任人 |
|---|---|---|
| 11-28 | D 完成 §1–§3；C 完成 C3/C14 适配 | D、C |
| 11-29 | D 完成 §4 + 图表；C 跑 v1.1 正式结果 | D、C |
| 11-30 | D 完成 §5–§6 + 文献；C 复核 D 数字；C/D 签阶段 0 | D、C |
| 12-01 14:00 | 论文初稿冻结，交 A 审 | D |
| 12-01 20:00 | 终稿，A 打包 `07_submission/` | A |
| **12-01 23:41** | **提交** | A |
