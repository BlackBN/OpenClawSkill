# OpenClaw 工作区

所有智能助手统一放在本目录下管理。

## 目录结构

```
/Users/bn/OpenClaw/
├── README.md                 # 本说明
├── assistants/               # 各飞书 bot 对应的工作区
│   ├── openclaw-ai/          # OpenClaw AI助手（main agent）
│   └── cursor/               # Cursor AI助手（cursor agent）
└── skills/                   # 共享技能（未来新增放这里）
    └── shared/               # 多助手共用的 skill
```

## 代码仓库路径

| 类型 | 路径 |
|------|------|
| Go | `/Users/bn/Go/src/` |
| 自己的仓库 | `/Users/bn/Go/src/github.com/BlackBN/` |
| 其他语言 | `/Users/bn/Project/` |

共享 skill：`skills/shared/bn-dev-layout/`、`skills/shared/delegate-to-cursor/`

## 飞书群「BN助手」

| 飞书机器人 | Agent | 工作区 | 写代码 |
|-----------|-------|--------|--------|
| OpenClaw AI助手 | `main` | `assistants/openclaw-ai/` | 不自己写，@Cursor AI助手 |
| Cursor AI助手 | `cursor` | `assistants/cursor/` | 执行所有编程任务 |

## 新增助手

1. 在飞书开放平台创建应用并开启机器人
2. `openclaw channels add --channel feishu --account <id>`
3. `openclaw agents add <id> --workspace /Users/bn/OpenClaw/assistants/<id>`
4. 在本目录 `assistants/<id>/` 下放置 `AGENTS.md`、`SOUL.md` 等
5. 需要共享 skill → 放 `skills/shared/`；仅该助手用 → 放 `assistants/<id>/skills/`

## 常用命令

```bash
openclaw agents list --bindings
openclaw channels status --probe
openclaw skills install <slug> --agent main    # OpenClaw AI助手
openclaw skills install <slug> --agent cursor  # Cursor AI助手
```
