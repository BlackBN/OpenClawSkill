---
name: cursor-model-select
description: >
  Cursor CLI 模型选择与默认配置。用户说 /models、选择模型、切换模型、模型列表时使用；
  或需要在调用 agent CLI 前确认/切换模型时使用。默认模型为 composer-2.5（非 fast）。
metadata:
  openclaw:
    emoji: "🎛️"
  requiredBinaries: ["agent"]
---

# Cursor CLI 模型选择

## 默认模型

- **默认：** `composer-2.5`
- **禁止作为默认：** `composer-2.5-fast` 及一切 `*-fast` 模型（除非用户明确要求 fast）
- 配置来源：`MODEL.md`（工作区根目录）

## 解析当前应使用的模型

1. 读 `MODEL.md` 里 JSON 块的 `modelId`
2. 若 `modelId` 有值 → 用该 ID
3. 若 `modelId` 为 null → 用 `composer-2.5`
4. 用户消息里写了 `--model xxx` 或「用 xxx 模型」→ 以用户当次指令为准（最高优先级）

## 触发：列出模型供用户选择

当用户消息匹配：`/models`、`/model`、`/模型`、`选择模型`、`切换模型`、`模型列表`、`列出模型`：

1. 运行 `agent models`，获取完整列表
2. 用中文回复，给出**编号列表**（推荐 8–12 个常用项 +「回复编号或完整 model ID」）
3. **优先推荐非 fast 模型**；fast 模型单独标注「快速模式」
4. 标明当前默认 `composer-2.5` 和 `MODEL.md` 里已选中的模型（若有）
5. **不要**在此轮调用 `agent -p` 执行 coding 任务

### 推荐展示模板

```
当前默认：composer-2.5（非 fast）
当前选用：<modelId 或「同默认」>

可选模型：
1. composer-2.5 — 默认，Composer 2.5
2. claude-opus-4-8-thinking-high — Opus 深度思考
3. gpt-5.3-codex-high — Codex 高精度
4. sonnet-4.6 — （若列表中有）
5. auto — 自动
…

回复编号或 model ID 即可切换；发「恢复默认」清除选用。
```

## 用户选定模型后

1. 解析编号或 model ID（支持 `composer-2.5`、`恢复默认`）
2. 更新 `MODEL.md` JSON 中 `modelId`（恢复默认则设为 null）
3. 中文确认：「已切换为 xxx」或「已恢复默认 composer-2.5」

## 调用 agent CLI 时

所有 `agent -p` 必须带模型参数（避免 CLI 落到 composer-2.5-fast 默认）：

```bash
cd <repo> && agent -p "<任务>" --model <resolved-model-id> --mode=ask --output-format text --trust
```

`resolved-model-id` 按上文「解析当前应使用的模型」得到。

## 与 cursor-agent skill 的关系

- 本 skill 管**模型选择与默认**
- `cursor-agent` skill 管**如何跑任务**（ask/force/cloud）
- 两者同时适用：先解析模型，再按 cursor-agent 流程执行
