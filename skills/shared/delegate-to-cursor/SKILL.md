---
name: delegate-to-cursor
description: >
  OpenClaw AI助手 遇到写代码任务时，在飞书群 BN助手 里 @Cursor AI助手 委派任务，禁止自己调 Cursor CLI 或直接改代码。
  触发：写代码、改代码、新建工程、refactor、debug 代码、review diff、任何需要动仓库文件的操作。
metadata:
  openclaw:
    emoji: "🎯"
---

# 委派给 Cursor AI助手（飞书群）

**OpenClaw AI助手 不亲自写代码。** 凡涉及修改或创建代码仓库的任务，必须在群里交给 **Cursor AI助手**。

## 何时委派（必须）

- 写/改/删源代码文件
- 新建工程项目
- Refactor、修 bug、加功能、写测试
- Code review 需要读仓库并可能改文件
- 用户说「帮我实现」「改一下代码」「建个项目」

## 何时不委派（自己处理）

- 纯概念解释、语法问答（不动仓库）
- 飞书文档/日程/天气等非代码任务
- 用户明确只要文字方案、不要动代码

## 委派步骤（BN助手 群）

1. **先简短告知用户**：「这个需要写代码，我 @Cursor AI助手 来执行。」
2. **用 `message` 工具在同一群发送**，正文格式：

```
@Cursor AI助手 <完整任务描述>

仓库路径：<绝对路径，按 bn-dev-layout 规范>
模式：只读分析 / 确认后改代码（默认先只读）
```

3. **任务描述要自包含**：Cursor AI助手 看不到你俩的私聊上下文，把需求、约束、路径写全。
4. **不要**在本机执行 `agent` CLI，**不要**使用 `cursor-agent` skill。

## 路径规范

委派前读取 `bn-dev-layout` skill，按规范填写仓库路径：

- 自己的 Go 项目 → `/Users/bn/Go/src/github.com/BlackBN/<name>`
- 第三方 Go → `/Users/bn/Go/src/github.com/<owner>/<repo>`
- 其他语言 → `/Users/bn/Project/<name>`

## 示例

用户：「帮我在新项目里搭个 Go HTTP 服务」

你在群里发：

```
@Cursor AI助手 在 /Users/bn/Go/src/github.com/BlackBN/<项目名> 初始化 Go HTTP 服务（main + /health），先只读给方案，不要直接改文件。
```

用户：「修一下 BlackBN/xxx 的 login bug」

```
@Cursor AI助手 分析并修复 /Users/bn/Go/src/github.com/BlackBN/xxx 的 login 问题，先只读定位原因，给出方案后再问用户是否 apply。
```

## 与用户对话

委派后对用户说：「已 @Cursor AI助手，请看群里它的回复。」不要重复执行同一任务。
