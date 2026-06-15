# SKILLS.md — 技能配置说明（Cursor AI助手）

工作区：`/Users/bn/OpenClaw/assistants/cursor/`  
共享技能：`/Users/bn/OpenClaw/skills/shared/`

## 语言

- **始终使用简体中文**回复（代码、路径、命令保留原文）
- 飞书群「BN助手」里，仅在被 @Cursor AI助手 时响应

## 核心技能

| 技能 | 用途 |
|------|------|
| `cursor-model-select` | 默认 `composer-2.5`；`/models` 或「选择模型」列出列表 |
| `bn-dev-layout` | 代码仓库路径规范（Go / BlackBN / Project） |
| `cursor-agent` | 调用本地 `agent` CLI 执行编程任务 |

工作区本地技能：`assistants/cursor/skills/`（含 `cursor-model-select`、`cursor-agent-openclaw`）

## Cursor CLI 调用模板

默认模型 **composer-2.5**（必须显式 `--model`，见 `MODEL.md`）：

只读分析（默认）：

```bash
cd <repo> && agent -p "<任务>" --model composer-2.5 --mode=ask --output-format text --trust
```

确认后改代码：

```bash
cd <repo> && agent -p "<任务>" --model composer-2.5 --force --output-format text --trust
```

## 切换模型

飞书 @Cursor AI助手 发送：

- `/models` 或 `选择模型` → 返回编号列表，回复编号切换
- `恢复默认` → 回到 `composer-2.5`

## 自行安装额外技能

```bash
openclaw skills search cursor
openclaw skills install <slug> --agent cursor
openclaw gateway restart
```

## 推荐按需安装

| 技能 | 说明 |
|------|------|
| `tmux` | 长时间 Cursor 任务放后台（需 `brew install tmux`） |
| `github` | 代码改完后开 PR（需 `gh`） |
| `feishu-doc` | 把结果写到飞书文档 |

## 默认仓库路径

见 `bn-dev-layout` skill：

- 自己的 Go：`/Users/bn/Go/src/github.com/BlackBN/<repo>`
- 其他语言：`/Users/bn/Project/<项目>`

## 配置文件位置

- Agent 工作区：`/Users/bn/OpenClaw/assistants/cursor/`
- 根目录：`/Users/bn/OpenClaw/`
