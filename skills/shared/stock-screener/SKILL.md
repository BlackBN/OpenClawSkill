---
name: stock-screener
description: "A股/港股/美股多因子选股与排名。用户要筛选股票、找候选股、按PE/ROE/成长/估值/动量排名、在指数成分内选股、找便宜/高成长/高质量/高股息/强势股时使用。默认A股(cn)。勿用于单股深度分析、组合配置或下单。"
---

# 多因子选股器（stock-screener）

**做什么：** 先用服务端条件缩小股票池，再对候选股做五因子打分排序。回答「在给定市场里，哪些股票最值得进一步研究？」

**适合谁：** 自上而下选行业后的第二步；波段/打板前的量化初筛；在沪深300、恒生科技等指数成分里找标的。

**设计参考：** 借鉴开源多因子框架思路（如 AKShare 数据层、quantitative-value-system 的 PE/PB/ROE/负债率组合、CANSLIM 成长动量、Graham 价值与安全边际），针对 A 股/港股做了 ST 剔除、PB 兜底、换手率动量增强等本地化适配。

## 数据来源

| 市场 | 第一阶段（粗筛） | 第二阶段（ enrich ） | 默认 |
|------|------------------|----------------------|------|
| **A 股** | akshare 全市场快照 | akshare / 东方财富 | `--region cn` |
| **港股** | akshare HK 快照 | akshare | `--region hk` |
| **美股** | yfinance EquityQuery | yfinance | `--region us` |

安装依赖：`pip install -r skills/shared/requirements.txt`

## 两阶段架构

**阶段 1 — 服务端筛选（1 次调用）**  
按行业/板块、PE、ROE、市值等条件从全市场拉候选列表，避免逐只扫描。

**阶段 2 — 明细 enrich（约 25–50 次）**  
拉完整财务与行情，复验筛选条件，再按五因子模型打分排序。

A 股/HK 走 akshare 本地扫描；美股走 Yahoo Finance。

## 五因子评分（0–100）

| 因子 | 均衡 | 价值 | 成长 | 质量 | 股息 | 动量 | 指标 |
|------|------|------|------|------|------|------|------|
| 估值 | 25% | 40% | 10% | 15% | 35% | 5% | PE + EV/EBITDA（缺 EV/EBITDA 时用 PB） |
| 盈利 | 25% | 20% | 15% | 35% | 30% | 10% | ROE |
| 成长 | 20% | 10% | 40% | 15% | 5% | 15% | 营收 + 利润增速 |
| 动量 | 15% | 10% | 25% | 10% | 5% | 55% | 52 周涨跌幅（动量风格叠加换手率） |
| 安全 | 15% | 20% | 10% | 25% | 25% | 15% | 低负债 + 经营现金流/净利润 |

### 风格预设（`--style`）

- **balanced（默认）**：通用均衡
- **value**：偏 Graham/低估值，适合周期、深度价值
- **growth**：偏 CANSLIM，适合高成长赛道
- **quality**：偏 ROE + 低杠杆，适合防御型复利股
- **dividend**：偏估值 + 盈利 + 安全，适合高股息策略
- **momentum**：偏价格动量 + 换手，适合趋势/波段

### A 股本地化

- 自动剔除 **ST / *ST** 等风险警示股
- 银行、亏损股等缺 EV/EBITDA 时用 **PB** 参与估值分
- 动量风格下参考 **换手率**，贴近短线资金活跃度

### 关键设计

- **相对估值打分**：在同一批结果内按 PE/PB 排名，避免「PE<20 一定便宜」的跨行业误判
- **市值只做过滤不做加分**：`--mcap` 控制流动性，不参与综合分
- **缺失字段中性处理**：预亏、金融股缺部分指标时降权或给中性分

## 脚本用法

```bash
# A 股：半导体 + 成长风格
python3 scripts/fetch_data.py --region cn --industry 半导体 --pe 40 --style growth --top 15

# A 股：沪深300 内价值选股
python3 scripts/fetch_data.py --index csi300 --style value --pe 25 --roe 10

# A 股：中证500 + 质量
python3 scripts/fetch_data.py --index zz500 --style quality --pe 0 --roe 12

# 自定义主题池（锆/稀土等）
python3 scripts/fetch_data.py --tickers 002167.SZ 600111.SS 600392.SS 000831.SZ --pe 0 --roe 0

# 港股：恒生科技 + 质量
python3 scripts/fetch_data.py --region hk --index hstech --style quality

# 美股
python3 scripts/fetch_data.py --region us --sector Technology --pe 25 --style growth
```

### 参数说明

| 参数 | 默认 | 说明 |
|------|------|------|
| `--region` | cn | 市场：**cn**（A 股）、**hk**、**us** |
| `--sector` | 无 | 板块（Technology、Healthcare 等，美股/YF 分类） |
| `--industry` | 无 | 行业关键词，部分匹配（如 `半导体`、`白酒`） |
| `--pe` | 20 | 最大 PE；0 表示不限制 |
| `--roe` | 15 | 最低 ROE（%）；0 表示不限制 |
| `--mcap` | 1.0 | 最低市值（十亿美元）；0 表示不限制 |
| `--top` | 25 | 粗筛最多返回数量 |
| `--style` | balanced | 风格：balanced / value / growth / quality / dividend / momentum |
| `--tickers` | 无 | 自定义代码列表 |
| `--index` | 无 | 指数池：`csi300`/`hs300`、`zz500`、`hsi`、`hstech` |

### 各市场参数建议

| 市场 | PE | ROE | 备注 |
|------|-----|-----|------|
| A 股 | 20–40 | 10–15% | 成长赛道可放宽 PE |
| 港股 | 15–25 | 10–15% | 结构性折价，价值风格常用 |
| 美股 | 15–25 | 15%+ | 标准设定 |

## 输出字段

CSV：`ticker, name, sector, industry, price, market_cap_B, pe, forward_pe, ev_ebitda, roe_pct, revenue_growth_pct, earnings_growth_pct, momentum_52w_pct, debt_equity, score`

stdout 另有排名表、行业分布、分数段统计。

## 如何把用户意图映射到命令

- **宽板块**：「科技股」→ `--sector Technology` 或 `--industry 软件`
- **细分行业**：「半导体」→ `--industry 半导体` 或 `--tickers` 行业龙头列表
- **主题/概念**（军工、新能源、稀土）：YF 无对应 sector 时用 `--tickers` 或 `--industry` 关键词
- **风格**：「便宜/低估」→ `--style value`；「高成长」→ `--style growth` 并放宽 `--pe`；「高股息」→ `--style dividend`；「强势/趋势」→ `--style momentum`
- **指数内选股**：「在沪深300里找」→ `--index csi300`

## 跑完脚本后你要做什么

1. **说明筛选逻辑**：用了哪些过滤条件、风格、初始池多大、通过多少只。
2. **解读前 3–5 名**：哪几个因子拉高/拉低分数，例如「估值分高因 PB 在池内最低，动量分低因近 52 周跑输板块」。
3. **业务与催化剂**：用常识补充数字背后的逻辑（业绩、政策、产品周期）；不熟悉的小票再搜新闻。
4. **信号 vs 预期**：动量已经很高可能是预期兑现；估值低但 ROE 差可能是价值陷阱。
5. **剔除噪音**：优先股、B 股重复、极端 ROE/负 growth 要标注。
6. **下一步**：对优选标的跑 `business-quality`（质地）或 `valuation-matrix`（估值）。
