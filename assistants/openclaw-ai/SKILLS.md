# SKILLS.md — 技能配置说明（OpenClaw AI助手）

本文件记录 **OpenClaw AI助手** 可用技能。共享技能目录：`/Users/bn/OpenClaw/skills/shared/`

## 语言

- **始终使用简体中文**与用户交流（代码、命令、专有名词可保留英文）
- 飞书群「BN助手」里，仅在被 @ 时回复

## 当前已就绪技能

| 技能 | 用途 |
|------|------|
| `bn-dev-layout` | 代码仓库路径规范（Go / BlackBN / Project） |
| `delegate-to-cursor` | **写代码时 @Cursor AI助手 委派（禁止自己写代码）** |
| `feishu-doc` | 飞书文档读写 |
| `feishu-drive` | 飞书云盘文件 |
| `feishu-wiki` | 飞书知识库 |
| `feishu-perm` | 飞书文档权限 |
| `browser-automation` | 浏览器自动化 |
| `diagram-maker` | 架构图/流程图 |
| `weather` | 天气查询 |
| `notion` | Notion 页面 |
| `taskflow` | 多步骤任务编排 |

工作区本地技能：`assistants/openclaw-ai/skills/`  
共享技能：`skills/shared/`

## 自行安装新技能

```bash
# 搜索
openclaw skills search <关键词>

# 安装到 OpenClaw AI助手
openclaw skills install <slug> --agent main

# 安装共享技能（所有助手可用时放 skills/shared/）

# 启用（若在 openclaw.json 里被禁用）
openclaw config set skills.entries.<slug>.enabled true --strict-json
openclaw gateway restart
```

## 推荐按需安装

| 技能 | 前置条件 | 说明 |
|------|----------|------|
| `tmux` | `brew install tmux` | Cursor 长任务后台跑 |
| `github` | `brew install gh && gh auth login` | PR/Issue/CI |
| `summarize` | 无 | 总结链接/文章 |
| `clawhub` | 无 | 管理技能市场 |

## 与 Cursor AI助手 的分工

| 场景 | 做法 |
|------|------|
| 日常问答、飞书文档、调度 | 本助手直接处理 |
| 任何写代码/改仓库 | 在群里 **@Cursor AI助手** 发任务（见 `delegate-to-cursor`） |

## 配置文件位置

- 工作区技能：`/Users/bn/OpenClaw/assistants/openclaw-ai/skills/`
- 共享技能：`/Users/bn/OpenClaw/skills/shared/`
- 本地环境备注：`/Users/bn/OpenClaw/assistants/openclaw-ai/TOOLS.md`
