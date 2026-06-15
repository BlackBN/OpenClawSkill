---
name: bn-dev-layout
description: >
  bn 的代码仓库目录规范。写代码、新建工程、clone 仓库、或用户问「项目放哪」时使用。
  适用于 Go、其他语言、自建仓库与第三方开源仓库的路径选择。
metadata:
  openclaw:
    emoji: "📁"
---

# bn 代码仓库路径规范

## 总览

| 类型 | 根路径 | 说明 |
|------|--------|------|
| **Go 语言** | `/Users/bn/Go/src/` | 遵循 GOPATH 风格目录 |
| **自己的仓库** | `/Users/bn/Go/src/github.com/BlackBN/` | 默认新建 Go 工程放这里 |
| **第三方开源（Go）** | `/Users/bn/Go/src/<import-path>/` | 如 `github.com/xxx/repo` → `/Users/bn/Go/src/github.com/xxx/repo` |
| **其他语言** | `/Users/bn/Project/` | Python、Node、Rust 等非 Go 项目 |

## Go 项目

- **GOPATH 根目录：** `/Users/bn/Go/src/`
- **自己的新工程（默认）：** `/Users/bn/Go/src/github.com/BlackBN/<项目名>`
- **自己的已有仓库：** `/Users/bn/Go/src/github.com/BlackBN/<repo>`
- **第三方开源：** `/Users/bn/Go/src/github.com/<owner>/<repo>`（或对应 import 路径）

新建 Go 工程时，除非用户指定其他路径，**默认创建在** `github.com/BlackBN/` 下。

## 其他语言

- 根目录：`/Users/bn/Project/`
- 示例：`/Users/bn/Project/my-python-app/`

## 路径选择规则

1. 用户说了具体路径 → 以用户为准
2. 用户说「我的项目 / 我写的」→ `github.com/BlackBN/` 下查找或新建
3. 用户说 Go / golang → `/Users/bn/Go/src/` 下按 import 路径组织
4. 用户说 clone 某开源仓库 → `/Users/bn/Go/src/<完整import路径>/`（Go）或 `/Users/bn/Project/<name>/`（非 Go）
5. 不确定语言 → 先问用户，或根据仓库特征判断

## 给 Cursor 下命令时

任务描述里**必须带上绝对路径**，例如：

```
在 /Users/bn/Go/src/github.com/BlackBN/myapp 下添加 HTTP health 接口，先只读分析
```
