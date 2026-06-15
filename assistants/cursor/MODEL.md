# MODEL.md — Cursor CLI 模型配置

## 默认模型（未指定时始终使用）

- **模型 ID：** `composer-2.5`
- **禁止默认使用：** 任何带 `-fast` 后缀的模型（如 `composer-2.5-fast`）
- **说明：** 非 fast 的 Composer 2.5，质量优先

## 当前选用（用户切换后写入，覆盖默认）

```json
{
  "modelId": null,
  "note": "null 表示使用上方默认 composer-2.5"
}
```

用户选定模型后，将 `modelId` 改为具体 ID（例如 `claude-opus-4-8-thinking-high`）。

## 模型选择触发词

用户发送以下任一内容时，**不要跑 coding 任务**，改为列出模型供选择：

- `/models` `/model` `/模型`
- `选择模型` `切换模型` `模型列表` `列出模型`

## 推荐展示列表（从 `agent models` 筛选，优先非 fast）

向用户展示编号列表，标注当前默认/当前选用。示例分组：

| # | 模型 ID | 说明 |
|---|---------|------|
| 1 | `composer-2.5` | **默认** Composer 2.5 |
| 2 | `claude-opus-4-8-thinking-high` | Opus 4.8 深度思考 |
| 3 | `gpt-5.3-codex-high` | Codex 5.3 High |
| 4 | `auto` | 自动选择 |

完整列表运行：`agent models`

用户回复编号或模型 ID 后，更新本文件 `modelId` 并确认。
