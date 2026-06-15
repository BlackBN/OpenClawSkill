---
name: cursor-agent
description: >
  Run Cursor Agent CLI for coding tasks — writing, editing, refactoring, reviewing, or
  planning code — without spending OpenClaw API credits. Use when the user asks to
  write/fix/refactor/review code, a coding task would otherwise be done inline with
  Sonnet/Haiku, the user says "do this in cursor" or "use cursor for this", or any
  substantial file-editing task in a known repo. NOT for conversational questions about
  code (answer inline) or tiny one-liners that don't warrant a subprocess.
metadata:
  requiredBinaries: ["agent"]
---

# Cursor Agent

Cursor Agent CLI runs on the user's Cursor subscription — zero API cost. Always prefer it over inline code generation for any non-trivial coding task.

## Prerequisites

**Required binary: `agent`** (Cursor Agent CLI)

Install from the official site: https://cursor.com/docs/cli/overview — then verify with `agent --version`.
The helper script (`scripts/run.sh`) will exit with an error if `agent` is not found in PATH.

## User Consent Required — MANDATORY

This skill MUST NOT be invoked autonomously. Every invocation requires:

1. **State intent first** — tell the user: the repo, the task, the model, and whether files will be changed
2. **Wait for explicit "yes"** — do not proceed without clear user approval
3. **Default to read-only** — use `run.sh <repo> <task> <model> ask` unless the user explicitly asks for changes
4. **Before writing files** — run in `ask` mode first, show the user the plan, then ask: *"Apply these changes?"*
5. **Before `--cloud`** — explicitly warn: *"This will send repo contents to cursor.com. OK to proceed?"*
6. **Before committing** — show the diff and get confirmation

The helper script (`scripts/run.sh`) defaults to `ask` (read-only). Pass `write` as the mode argument only after the user has confirmed changes should be applied.

## Model Routing

**默认模型：`composer-2.5`（非 fast）。** 调用 `agent -p` 时必须传 `--model`，不要省略（CLI 裸默认会落到 `composer-2.5-fast`）。

模型选择流程见同工作区 `cursor-model-select` skill 与 `MODEL.md`。

| Task type | Model flag | Mode flag |
|---|---|---|
| 默认 / 一般编程 | `--model composer-2.5` | `--mode=ask` 先只读 |
| 用户已切换模型 | `--model <MODEL.md 中的 modelId>` | 同上 |
| 代码 review / explain | `--model composer-2.5` | `--mode=ask` |
| 架构 / 复杂规划 | `--model claude-opus-4-8-thinking-high` | `--mode=plan` |
| 用户要 fast | 仅当用户明确要求 `--model xxx-fast` | — |
| 长后台任务 | `--model composer-2.5` | `--cloud` |

## Headless Commands

**Read-only first** — always start with `--mode=ask` to review before applying changes:
```bash
cd <repo> && agent -p "<task>" --model composer-2.5 --mode=ask --output-format text --trust
```

**Apply changes** — only after user confirms the plan:
```bash
cd <repo> && agent -p "<task>" --model composer-2.5 --force --output-format text --trust
```

**Cloud/background** — warn user that repo data goes to cursor.com:
```bash
cd <repo> && agent -c "<task>" --model composer-2.5 --trust
# Monitor at: cursor.com/agents
```

## Git Rule

Cursor sandbox blocks `git commit`. Always commit manually after Cursor edits:
```bash
cd <repo> && git add -A && git commit -m "<conventional commit message>" && git push
```

Show the diff to the user and confirm before committing if the change is large or touches sensitive areas.

## Repos & Workdirs

- Always `cd` to the correct repo before running
- Check for `.cursor/rules` and `AGENTS.md` in the repo root — Cursor loads these automatically for project context

## Context & Sessions

- Add `@<file>` in prompt to include specific files in context
- `--continue` or `--resume` to continue a previous session
- `agent ls` to list previous sessions

## Output Handling

- `--output-format text` → clean final answer, summarise key changes to the user
- `--output-format json` → structured, use for scripted parsing
- Always report back: what changed, what was committed, any issues found

## References

- Model list & details: `references/models.md`
- Slash commands (interactive mode): `references/slash-commands.md`
