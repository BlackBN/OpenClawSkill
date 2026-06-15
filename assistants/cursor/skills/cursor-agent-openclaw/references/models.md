# Cursor Agent — Available Models

运行 `agent models` 获取实时列表。用户默认：**composer-2.5**（非 fast）。

## 默认（本工作区）

| ID | 说明 |
|---|---|
| `composer-2.5` | **默认** Composer 2.5，质量优先 |
| ~~`composer-2.5-fast`~~ | 禁止作为默认；仅用户明确要求时用 |

## 常用备选

| ID | 说明 |
|---|---|
| `claude-opus-4-8-thinking-high` | Opus 深度思考 / 架构 |
| `gpt-5.3-codex-high` | Codex 高精度 |
| `auto` | CLI 自动选择 |

## 模型切换

飞书发：`/models` 或 `选择模型` → 见 `cursor-model-select` skill。

持久化选用：写入 `MODEL.md` 的 `modelId` 字段。

## Max / Fast

- 带 `-fast` 后缀：更快，质量可能略降；**不要默认使用**
- Max Mode：交互模式 `/max-mode on`；谨慎使用
