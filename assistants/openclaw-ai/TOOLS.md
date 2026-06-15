# TOOLS.md — 环境与路径（OpenClaw AI助手）

## 飞书

- 群：**BN助手**
- 本 bot：**OpenClaw AI助手**（不写代码，委派给 Cursor）
- 编程 bot：**Cursor AI助手**

## 代码任务：不自己写，@ Cursor

涉及写代码时，读 `delegate-to-cursor` skill，在群里 @Cursor AI助手 发任务。  
**禁止**使用 `cursor-agent` skill 或本地 `agent` CLI。

## 仓库路径规范

详见 `bn-dev-layout` skill。摘要：

| 类型 | 路径 |
|------|------|
| Go 根 | `/Users/bn/Go/src/` |
| 自己的仓库 | `/Users/bn/Go/src/github.com/BlackBN/<repo>` |
| 新建 Go 工程 | 默认 `github.com/BlackBN/` 下 |
| 第三方 Go | `/Users/bn/Go/src/github.com/<owner>/<repo>` |
| 其他语言 | `/Users/bn/Project/<项目>` |

委派时在消息里写**绝对路径**。

## 路径

- 工作区：`/Users/bn/OpenClaw/assistants/openclaw-ai`
- 根目录：`/Users/bn/OpenClaw`
- 共享 skill：`/Users/bn/OpenClaw/skills/shared/`
