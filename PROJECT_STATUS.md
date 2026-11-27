# 项目状态

- 状态：**阶段2 完成；阶段3 结果已冻结（far-only v1.0）；near 待 B-v1.1**
- 更新日期：2026-11-27
- 选题：核密度估计与基于密度的异常检测
- 分支：实验分支
- 主线：KDE带宽敏感性，并与LOF比较
- 小组规模：4人
- Git：本地仓库已初始化，分支为 `main`
- GitHub：公开仓库已创建并连接
- 仓库地址：https://github.com/kekan1120/kde-anomaly-detection-course-project

## 阶段0进度

| 项目 | 状态 | 说明 |
|---|---|---|
| 选题和实验路线 | 已确定 | KDE/异常检测，实验分支 |
| 核心问题与实验主线 | 已确定 | 带宽影响及KDE/LOF对照 |
| 四人职责分工 | 已确认 | 见[项目章程](docs/project-charter.md#角色确认) |
| 项目目录和本地Git | 已完成 | `main` 已关联 GitHub 远程分支 |
| GitHub所有者与公开仓库名 | 已完成 | `kekan1120/kde-anomaly-detection-course-project`，Public |
| 四名成员姓名与组长 | 已登记 | 组长由 A 担任，名单见项目章程 |
| 课程截止日期 | 已确认 | 2026-12-01 23:41（截图推算），剩余约 4.5 天 |
| 最终文件提交格式 | 已确认 | 两份文件（超星截图口径） |
| 研究问题与假设可证伪化 | 已起草 | A 完成 `docs/research-questions-hypotheses.md`，待全组核准 |
| 四名成员个人会话记录 | 1/4 链接已填 | 4 份文件已建；A 链接已填，B/C/D 待补 |
| 阶段0关闭检查清单 | 已建立 | `docs/stage0-closure-checklist.md`：6 条退出条件 + 四人确认/核准表 |
| 阶段0章程核准 | 进行中 | 待 B/C/D 在检查清单打勾确认后关闭 |

## 阶段0退出条件

- [x] 四名成员姓名和组长已登记。
- [x] 截止日期及提交入口格式已从课程平台确认。
- [ ] 每名成员的任务、交付件和交叉审阅对象已确认。（待 B/C/D 签字，见检查清单 2.3）
- [ ] 研究问题、假设、数据划分、参数选择和指标协议经全组核准。（待 B/C/D 签字，见检查清单三）
- [ ] 四份个人AI过程记录已建立并记录对应会话链接维护人。（4 份文件已建，会话链接待补）
- [x] GitHub远程公开仓库已创建并连接。

阶段0退出后，再进入阶段1“理论、数据与实验协议”的验收。

## 阶段2实现与复现（成员 C）进度

| 项目 | 状态 | 证据 |
|---|---|---|
| 独立实现（数据生成 / 打分 / 阈值 / 指标 / 峰结构 / 实验 / 落盘） | 完成 | `04_code/src/kdelof/` |
| 复现 B 的基准数值 | 完成 | 三个划分 sha256 **逐位一致**；50 项对账**偏差 0** |
| 正确性核验（15 项） | 15 PASS / 0 FAIL | `05_results/main/sanity_checks.md` |
| 结果审计（13 项） | 13 PASS / 0 FAIL | `05_results/main/audit_results.md` |
| 用 B 的审计脚本审 C 的结果（12 项） | 12 PASS / 0 FAIL | `05_results/main/audit_by_B_suite.md` |
| 与 B 基准逐项对账（50 项） | 50 PASS / 0 FAIL | `05_results/main/reconciliation_vs_B.md` |
| 干净环境重跑（新建 venv + 独立输出目录） | 一致 | 指纹 sha256 一致，指标最大偏差 0.0 |
| 交叉审查 B 的参考实现 | 发现并修正 1 处缺陷 | `04_code/ref_check/PATCHES_C.md` |
| 个人 AI 过程记录 | 已建立 | `process-logs/member_C.md` |
| 空区紧凑簇 `anomaly.near` 启用 | 待 **B 发布 B-v1.1** | 提案：`docs/protocol-change-B-v1.1.md`；签署后 C 重跑 |
| 待办：本机会话分享链接 | 待本人填写 | `process-logs/member_C.md` 表头 |

## 最新进展（2026-11-27）

| 事项 | 状态 | 文件 |
|---|---|---|
| 目录统一 | 完成 | A 侧草稿统一到 `04_code/ai_draft/`、`05_results/ai_draft/`，与 C 正式实现物理隔离 |
| 结果冻结口径 | 完成 | 主结果 **far-only（v1.0，冻结于 `7f4990c`）**；near 待 v1.1 |
| A 侧草稿降级 | 完成 | boundary / compact@(0,0) 经 C 证伪，作「设计迭代记录」（`docs/experiment-protocol.md` §10） |
| B-v1.1 变更提案 | 已起草，待 B 签署 | `docs/protocol-change-B-v1.1.md`（near.enabled=true、n_test 125/125） |
| 论文引用口径 | 已建立，待 D 使用 | `docs/paper-citation-guide.md`（禁止引用 near / ai_draft 数字） |
| 阶段0关闭包 | 已建立，待 B/C/D 签字 | `docs/stage0-closure-checklist.md` |
| A 会话链接 | 已填 | `process-logs/member_A.md` |
