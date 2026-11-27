# 项目状态

- 状态：**C 已产出 v1.1 正式结果；D 论文完成并经 C 复核；阶段 0 仅差 B 会话链接**
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
| 研究问题与假设可证伪化 | 已核准 | A/B/C/D 全签（`stage0-closure-checklist.md` 三） |
| 四名成员个人会话记录 | 3/4 有凭证 | 按 [`docs/session-link-policy.md`](docs/session-link-policy.md)：D 分享链接；A、C DSH 导出凭证（已确认等价，decision-log #25）；**B 待填** |
| 阶段0关闭检查清单 | 已建立 | `docs/stage0-closure-checklist.md`：6 条退出条件 + 四人确认/核准表 |
| 阶段0章程核准 | 基本完成 | A/B/C/D 已确认与核准；**仅差 B 会话链接**即可关闭 |

## 阶段0退出条件

- [x] 四名成员姓名和组长已登记。
- [x] 截止日期及提交入口格式已从课程平台确认。
- [x] 每名成员的任务、交付件和交叉审阅对象已确认。（A/B/C/D 全签，见检查清单 2.3）
- [x] 研究问题、假设、数据划分、参数选择和指标协议经全组核准。（A/B/C/D 全签，见检查清单三）
- [ ] 四份个人AI过程记录已建立并记录对应会话链接维护人。（A/D 已填；**B 待填**；C 用导出+仓库链接替代，待确认）
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
| 空区紧凑簇 `anomaly.near` 启用 | **已完成** | `04_code/config_ref.json` = B-v1.1-near；C 正式结果 `05_results/main_v1_1_near/`（核验 17/17、审计 13/13、交叉 12/12、对账 39/39）；`recall_compact_void` = 125/125 |
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
| **B 交付入库** | 完成 | `01_protocol_and_data_dictionary.md`（权威协议）、`HANDOFF_README.md`、`START_HERE.md`、`process-logs/member_B.md`（7 回合）；`config_ref.json` 升 **B-v1.1-near** |
| **B 裁定三问** | 完成 | Q-A 点级嵌套（新增 `far.n_draw=250`，抽样与 n_test 解耦）；Q-B 接受 `B-v1.1-near`（v1.0 仍为预注册主结果）；Q-C 跑 10 种子 |
| **v1.1 参考结果** | 已产出（B 侧） | `05_results/ref_check_v1.1/`；C17 不变性 max\|Δ\|=0、C18 far 点级嵌套成立、`recall_compact_void` 全 10 配置 = 125/125 |
| **A 文档被 B 取代/修订** | 已处理 | `docs/experiment-protocol.md` §1–§9 加「已被取代」横幅；`stage0-closure-checklist.md` B 已签并附两条建议（H3 判据、术语表分位数）已采纳 |
| **C v1.1 正式结果** | 完成 | `05_results/main_v1_1_near/`；`recall_compact_void` 全配置 125/125（印证机制预期，**非方法差异**） |
| **D 论文完成** | 完成 | `06_paper/course_report.md`（摘要 245 字）；`numeric_traceability.md` 数字追溯表 |
| **C 复核 D** | 通过 | `06_paper/c_review_of_D.md`：32 项，数值 **0 错误、0 跨版本混用**；2 项小修（图 5 图注、1 张未引用图） |
| **D 阶段 0 签字** | 完成 | 检查清单 2.3 + 三 全签（A/B/C/D 齐） |
