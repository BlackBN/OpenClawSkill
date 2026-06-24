---
name: business-profile
description: "上市公司业务基本面画像：主营业务拆解、收入结构、产业链位置、商业模式、行业竞争、SWOT、催化剂与未来展望。用户问公司是做什么的、行业怎么样、业务优劣势、投资逻辑、深度基本面、业务分析时使用。勿用于纯财务打分(business-quality)、同行排名(competitor-analysis)或估值(valuation-matrix)。"
---

# 业务基本面画像（business-profile）

**做什么：** 用结构化数据 + 专业卖方框架，回答「这家公司做什么、在行业什么位置、优劣势何在、未来看什么」。

**和 `business-quality` 的分工：**

| Skill | 核心问题 |
|-------|----------|
| **business-profile** | 业务是什么、行业逻辑、SWOT、催化剂（**叙事 + 分部数据**） |
| business-quality | 财务好不好、护城河打分（**量化质地**） |

**设计参考：** 卖方深度报告「公司研究」章节 + `company-research-cn` 二级/制造业框架（产能、产业链、竞争对标）。

## 数据来源

| 市场 | 数据源 | 代码格式 |
|------|--------|----------|
| **A 股** | akshare 同花顺主营 + 东财主营构成 + `_data` 财报 | `301366.SZ`、`002167` |
| **港股** | akshare + `_data`（分部数据可能缺失） | `0700.HK` |
| **美股** | yfinance 公司摘要 + `_data` | `NVDA` |

安装：`pip install -r skills/shared/requirements.txt`

## 脚本用法

```bash
python3 scripts/fetch_data.py 301366.SZ
python3 scripts/fetch_data.py 301366.SZ --peers 002916.SZ 002463.SZ 300476.SZ
python3 scripts/fetch_data.py 002167.SZ
python3 scripts/fetch_data.py 0700.HK
```

**输出：** stdout Markdown（含已验证数据表 + Agent 待填章节）；stderr JSON。

## 跑完脚本后你要做什么

### 1. 先读数据，再写判断

脚本已提供：**快照、分部收入、财务轨迹、股东结构**。禁止与数据矛盾的臆测；缺数据处写「待核实」。

### 2. 完成五个专业章节

| 章节 | 要求 |
|------|------|
| **投资逻辑** | 3 条可证伪要点，每条绑定 KPI（如 PCBA 占比、设计服务毛利率、下游 AI/通信订单） |
| **商业模式** | 怎么赚钱、客户是谁、轻/重资产、单位经济（人数×人均产值、产能利用率） |
| **产业链 & 竞争** | 上中下游利润池；对标 3–5 家 peer（可再跑 `competitor-analysis`） |
| **SWOT** | 每条标注 📌事实 / 🔍判断 / ⚠️推断 |
| **催化剂 & 风险** | 12–36 月事件日历 + 风险矩阵（概率×影响） |

### 3. 制造业 / 半导体专项（适用时必写）

- 产能、利用率、CapEx、良率
- 研发验证 vs 量产节奏
- 客户集中度、订单能见度

### 4. 证据约束

1. 每个核心结论 ≥2 个数值或可追溯来源
2. 分部数据以脚本 `segments.report_date` 为准
3. 行业规模、市占率若来自搜索，须标注来源与日期
4. 不给具体买卖价位（交给 `valuation-matrix`）

### 5. 衔接下一步

```
business-profile → competitor-analysis → business-quality → valuation-matrix
```

## 报告结构（完整交付时）

```markdown
# [公司] 业务基本面深度分析

## 执行摘要（3–5 句 + 核心结论）

## 投资逻辑（3 条）

## 公司概览 & 收入结构（脚本数据 + 解读）

## 商业模式与产业链位置

## 行业分析（TAM/周期/政策/竞争格局）

## SWOT

## 未来展望 & 催化剂

## 风险矩阵

## 跟踪 KPI 清单
```

## A 股示例（一博科技 301366）

脚本会输出：PCB 设计 vs PCBA 制造收入占比、下游行业分布（网络通信/工控/AI 等）、历史营收 CAGR。Agent 补充：高速 SI/PI 壁垒、工程师规模瓶颈、与深南/沪电/胜宏的差异。
