# 项目状态

- 状态：**阶段0进行中**
- 更新日期：2026-11-26
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
| 课程截止日期 | 已确认 | 2026-12-01 23:41（截图推算），剩余约 5.4 天 |
| 最终文件提交格式 | 已确认 | 两份文件（超星截图口径） |
| 研究问题与假设可证伪化 | 已起草 | A 完成 `docs/research-questions-hypotheses.md`，待全组核准 |
| 四名成员个人会话记录 | 部分建立 | A 已建 `process-logs/member_A.md`，B/C/D 待建 |
| 阶段0章程核准 | 进行中 | 以上待确认项补齐后由四人确认 |

## 阶段0退出条件

- [x] 四名成员姓名和组长已登记。
- [x] 截止日期及提交入口格式已从课程平台确认。
- [ ] 每名成员的任务、交付件和交叉审阅对象已确认。
- [ ] 研究问题、假设、数据划分、参数选择和指标协议经全组核准。
- [ ] 四份个人AI过程记录已建立并记录对应会话链接维护人。
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
| 待办：`anomaly.near`（空区紧凑簇）是否启用 | **待 A/D 拍板** | 只需一行配置；**必须在看结果前决定** |
| 待办：本机会话分享链接 | 待本人填写 | `process-logs/member_C.md` 表头 |
