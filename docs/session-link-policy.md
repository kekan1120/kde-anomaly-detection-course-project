# 会话链接规范（A 组长制定，2026-11-27）

> 依据：课程要求「每人使用自己账号下的同一连续会话完成所负责工作，并提供该会话完整分享链接」；
> 以及实际约束：本组部分成员在 DSH 桌面端工作，DSH 默认不提供公网分享服务。
> 本规范替代「必须为公网 URL」的单一要求，按平台分档执行。

## 1. 两档凭证形式

| 平台 | 凭证形式 | 要求 |
|---|---|---|
| **有公网分享功能**（如 DeepSeek 网页/客户端） | **原生分享链接** | 粘贴完整 URL，评审可直接打开；例：`https://chat.deepseek.com/share/xxxxxxxx` |
| **无公网分享功能**（如 DSH 桌面端本地会话） | **导出会话记录 + 仓库存档** | 按第 2 节格式导出，存入 `process-logs/member_X_session_export.md`，并在 `member_X.md` 的「会话链接」栏指向该文件 |

## 2. DSH 会话导出规范

**文件**：`process-logs/member_X_session_export.md`

**必须包含**：

| 字段 | 要求 |
|---|---|
| 成员 / 角色 | 姓名与职责 |
| 会话 ID | 完整 session ID（如 `session-d74f302b-…`） |
| 平台 | 注明 DSH 桌面端、本地会话 |
| 时间跨度 | 首次与末次交互时间（Asia/Shanghai） |
| 原始记录 | 总条数、工具调用次数 |
| 本文件内容 | 用户提示词条数 + 模型文本回复条数；工具调用与系统提示从略 |
| 导出时间 | 导出日期 |
| **凭证说明** | 明确写「DSH 桌面端无公网分享服务，以完整会话导出 + 仓库存档为等价凭证；内容与本地会话一致，不含虚构」 |

**内容要求**：保留**提示词原文**与**模型文本回复**，按时间排序；不得删改或虚构。
原始会话文件（`session.v4.jsonl.zstd`）保存在本机 `C:\Users\<用户>\.dsh\sessions\` 下，可复导。

**导出方法**（可复现）：

```powershell
# 1. 定位会话
$sess = "$env:USERPROFILE\.dsh\sessions\<workspace-dir>\session-<id>\session.v4.jsonl.zstd"
# 2. 解压
zstd -d "$sess" -o "$env:TEMP\session.jsonl"
# 3. 解析 JSONL，提取 user/message（source.kind=user）与 assistant/message 的 text，
#    过滤 system-reminder，按 time 排序，生成 markdown（见 build 脚本）
```

## 3. 当前四名成员的凭证状态

| 成员 | 平台 | 凭证 | 状态 |
|---|---|---|---|
| A 林辰旭 | DSH 桌面端 | `process-logs/member_A_session_export.md` | ✅ 已确认（decision-log #25） |
| B 连昭悦 | **待确认** | **待填** | ⬜ 待补 |
| C 沈伊镄 | DSH 桌面端 | `process-logs/member_C_session_export.md` | ✅ 已确认（decision-log #25） |
| D 陈永喆 | DeepSeek | `https://chat.deepseek.com/share/finjt1j2r3rl7znvqf` | ✅ 原生分享链接 |

## 4. 执行要求

1. 每名成员在 `process-logs/member_X.md` 顶部「会话链接」栏填**符合本规范**的凭证。
2. 若使用 DSH：把导出文件提交到仓库，链接栏指向该文件（如 `[member_X_session_export.md](member_X_session_export.md)`）。
3. 若使用 DeepSeek 等有分享功能的平台：链接栏填完整 URL。
4. **不得虚填**：没有可访问凭证的，标「待填」并找组长协调，不得粘贴无效或他人的链接。

## 5. 依据与留痕

- decision-log #25：A、C 的 DSH 导出凭证确认为等价凭证
- `process-logs/member_A_session_export.md`（2605 条原始记录 / 40 提示词 / 148 回复）
- `process-logs/member_C_session_export.md`（C 的 `/export` 原文）
- 阶段 0 关闭检查清单条件 5
