# 飞书 / OpenClaw 一键投研 Prompt

> 配合仓库 7 个 Skill 使用（**自上而下顺序**）：
>
> `sector-radar` → `stock-screener` → `business-profile` → `competitor-analysis` → `business-quality` → `valuation-matrix` → `portfolio-monitor`
>
> **默认市场：A 股 + 港股**（数据来自 akshare / 东方财富；美股走 yfinance 兜底）

---

## 前置条件

| 项目 | 说明 |
|------|------|
| Skill 安装 | 7 个 skill 已装到 `~/.openclaw/workspace/skills/` |
| Python 依赖 | `pip install -r skills/shared/requirements.txt` |
| 模型鉴权 | OpenClaw 默认 `modelstudio/qwen3.5-plus`（阿里云百炼）。若报 401，在 `openclaw chat` 里执行 `/auth modelstudio` 填入 DashScope API Key |
| 输出语言 | 所有模板均要求 **中文输出** |

Skill 脚本路径（Agent 优先用已安装路径）：

```text
~/.openclaw/workspace/skills/<skill-name>/scripts/fetch_data.py
```

本地仓库调试路径：

```text
skills/shared/<skill-name>/scripts/fetch_data.py
```

---

## 占位符说明

复制模板时改这几处：

| 占位符 | 示例 | 说明 |
|--------|------|------|
| `{目标}` | `002167.SZ`、`600519.SS`、`0700.HK`、`NVDA` | 公司代码 |
| `{市场}` | `A股` / `HK` / `US` | 决定 ETF 列表与 `--region` |
| `{风格}` | 见下表 | 传给 `--style` |

**风格预设（`--style`）：**

| 风格 | 适用场景 |
|------|----------|
| `balanced` | 通用均衡（默认） |
| `growth` | 高成长赛道、CANSLIM 思路 |
| `value` | 低估值、周期、深度价值 |
| `quality` | 高 ROE、低杠杆、防御复利 |
| `dividend` | 高股息、红利策略 |
| `momentum` | 趋势/波段/强势股（A 股含换手率） |

**A 股代码格式：** `002167.SZ`、`600519.SS`，或裸 6 位 `002167`  
**港股代码格式：** `0700.HK`、`00700`

---

## 各市场 Step 1 ETF 速查

### A 股（benchmark: `510300` 沪深300）

```bash
# 宽行业轮动：半导体、有色、消费、新能源、酒
512480 512400 159928 515030 512690 --benchmark 510300

# 扩展：证券、医药、医疗、军工
512880 512010 512170 515000 --benchmark 510300
```

| 代码 | 板块 |
|------|------|
| 512480 | 半导体 |
| 512400 | 有色金属 |
| 159928 | 消费 |
| 515030 | 新能源 |
| 512690 | 酒 |
| 512880 | 证券 |
| 512010 | 医药 |
| 512170 | 医疗 |
| 515000 | 军工 |

### 港股（benchmark: `2800.HK` 盈富）

```bash
3067.HK 3033.HK 3012.HK 2828.HK --benchmark 2800.HK
```

### 美股（benchmark: `SPY`）

```bash
XLK XLF XLE XLV XLI XLY XLP --benchmark SPY
```

---

## 模板 A：完整链路（推荐）

适合：已有目标票，或想走完 6 步的标准投研。

```
请对 {目标} 做完整投研（{市场}，{风格} 风格）。

严格按以下 6 步顺序执行：每步先跑对应 skill 的 fetch_data.py，再按 SKILL.md「跑完脚本后你要做什么」补定性分析。全部中文输出，最后给 BUY/HOLD/SELL 和仓位建议（不构成法定投资建议）。

【Step 1 · sector-radar · 行业轮动】
- A股：512480 512400 159928 515030 512690 --benchmark 510300
- 港股：3067.HK 3033.HK 3012.HK 2828.HK --benchmark 2800.HK
- 美股：XLK XLF XLE XLV XLI --benchmark SPY
- 输出：板块排名 + 动量×加速四象限 + {目标} 所在行业是否强势

【Step 2 · stock-screener · 多因子选股】
- A股示例：--region cn --industry {行业关键词} --style {风格} --top 15
- 或在指数内筛：--index csi300 --style {风格} --pe 30 --roe 10
- 若已有 {目标}：--tickers {目标} + 3–5 只同业，--pe 0 --roe 0 仅做排名对比
- 输出：Top 5 候选 + 五因子得分拆解 + 是否 ST/异常指标

【Step 3 · business-profile · 业务基本面】
- 对 {目标} 跑 business-profile（可加 --peers 3–5 家竞品代码）
- 输出：分部收入结构、商业模式、产业链位置、SWOT、催化剂与风险矩阵

【Step 4 · competitor-analysis · 竞争排名】
- 以 {目标} 为核心，拉 3–5 个直接竞品做 peer 排名
- A股示例：002167.SZ 600111.SS 600392.SS 000831.SZ
- 港股示例：0700.HK 9988.HK 9618.HK
- 输出：谁领先/落后、份额变化、毛利动量

【Step 5 · business-quality · 生意质量】
- 对 Step 4 排名前 2 名跑 business-quality
- 输出：护城河（宽/窄/无）+ 6 维质量分 + 5 个商业问题 + ST/周期风险提示

【Step 6 · valuation-matrix · 估值矩阵】
- 对 {目标} 跑 valuation-matrix
- 输出：Bear/Base/Bull 公允价、反向 DCF 隐含增速、各方法分歧
- 注意：A 股分析师一致预期常缺失，勿强行解读

【Step 7 · portfolio-monitor · 组合诊断】（可选）
- 若提供持仓：格式 "002167.SZ:30 600111.SS:40 600392.SS:30"
- 基准自动：A 股 510300.SS，港股 2800.HK，美股 SPY
- 无持仓则跳过，给单票建议仓位区间

【最终汇总】
1. 三句话 Executive Summary
2. 行业观点（Step 1）
3. 业务基本面（Step 3）
4. 竞争地位（Step 4）
5. 生意质量（Step 5）
6. 估值与安全边际（Step 6）
6. 投资建议：BUY/HOLD/SELL + 理由 + 3 个关键风险 + 3 个跟踪指标
7. 若已持仓：再平衡建议（Step 7）
```

---

## 模板 B：快速单票（约 5 分钟）

适合：已有标的，跳过板块轮动和选股。

```
快速研究 {目标}（{市场}），跑 4 步：
1. business-profile：业务拆解、行业逻辑、SWOT、催化剂
2. competitor-analysis：找 3–5 个直接竞品做排名
3. business-quality：护城河与质量分
4. valuation-matrix：公允价区间 + 反向 DCF + 贵不贵

中文输出，结尾 BUY/HOLD/SELL + 一句话理由 + 最大风险。
```

---

## 模板 C：自上而下选股（无目标票）

适合：从市场出发，让 AI 帮你挑 3 只深研标的。

```
帮我从 {市场} 选 3 只值得深研的股票，风格 {风格}：

1. sector-radar 找最强 2 个行业（A股用 512480 512400 159928 515030 512690 --benchmark 510300）
2. 每个强势行业 stock-screener 筛 Top 3
   - A股：--region cn --industry {对应关键词} --style {风格} --top 10
   - 或在 --index csi300 / zz500 内筛
3. 6 只里 competitor-analysis 横向比一轮
4. 综合最高的 3 只做 business-quality + valuation-matrix

输出：3 只推荐 + 各自 BUY/HOLD/SELL + 优先级排序 + 为什么选这几只。
```

---

## 模板 D：波段 / 动量选股（A 股）

适合：趋势持股、强势股筛选；**打板仍需额外补充情绪/梯队/资金面**。

```
从 A 股 {指数或行业} 里找 {风格=momentum} 强势票，步骤：

1. sector-radar：512480 512400 515030 512880 512690 --benchmark 510300
   → 找出动量最强且「强+加速」象限的 1–2 个行业

2. stock-screener：
   --region cn --industry {Step1强势行业} --style momentum --top 15 --pe 0 --roe 0
   或在 --index csi300 / zz500 内：--index csi300 --style momentum --pe 0 --roe 0

3. 对 Top 3 各跑 business-quality（排除 ST、质量分过低）
4. 对最优 1–2 只跑 valuation-matrix（看是否涨过头）

中文输出：3 只波段候选 + 入场逻辑 + 止损/止盈参考位 + 需盯的 catalyst。
说明：本链路偏量价+基本面，不含涨停板梯队分析。
```

---

## 模板 E：高股息 / 红利（A 股）

```
在 A 股红利/价值方向选股，--style dividend：

1. stock-screener --index csi300 --style dividend --pe 20 --roe 10 --top 15
   或 --region cn --industry 银行 --style dividend --top 10

2. Top 5 跑 business-quality（看现金流质量、负债）
3. Top 3 跑 valuation-matrix（看股息率隐含估值）

中文输出：3 只红利候选 + 股息逻辑 + 主要风险（周期/坏账/政策）。
```

---

## 示例 1：A 股 · 东方锆业（完整链路）

```
请对 002167.SZ 做完整投研（A股，growth 风格），严格按 6 步跑脚本：

Step 1：512480 512400 159928 515030 512690 --benchmark 510300
Step 2：--region cn --industry 有色 --style growth --tickers 002167.SZ 600111.SS 600392.SS 000831.SZ --pe 0 --roe 0
Step 3 peers：002167.SZ 600111.SS 600392.SS 000831.SZ
Step 4：002167.SZ + 排名第 2 的竞品
Step 5：002167.SZ

中文输出，最后 BUY/HOLD/SELL + 关键风险（锆价、稀土政策、周期位置）。
```

---

## 示例 2：A 股 · 贵州茅台（质量 + 估值）

```
请对 600519.SS 做完整投研（A股，quality 风格）：

Step 1：512690 159928 512010 --benchmark 510300
Step 2：--tickers 600519.SS 000858.SZ 000568.SZ 600809.SS --style quality --pe 0 --roe 0
Step 3 peers：600519.SS 000858.SZ 000568.SZ 600809.SS
Step 4–5：600519.SS

中文输出，重点：定价权、渠道库存、估值 vs 历史中枢，结尾 BUY/HOLD/SELL。
```

---

## 示例 3：港股 · 腾讯（快速单票）

```
快速研究 0700.HK（HK），模板 B：

Step 1 peers：0700.HK 9988.HK 9618.HK 1810.HK
Step 2：0700.HK business-quality
Step 3：0700.HK valuation-matrix

中文输出，BUY/HOLD/SELL + 游戏/广告/云业务 catalyst。
```

---

## 示例 4：美股 · NVDA（完整链路）

```
请对 NVDA 做完整投研（US，growth 风格）：

Step 1：XLK SMH SOXX QQQ --benchmark SPY
Step 2：--region us --sector Technology --industry Semiconductors --style growth --tickers NVDA AMD AVGO QCOM INTC --pe 0 --roe 0
Step 3 peers：NVDA AMD INTC QCOM AVGO
Step 4：NVDA + 排名第 2 竞品
Step 5：NVDA

中文输出，BUY/HOLD/SELL + AI capex 周期风险。
```

---

## 终端直接使用

### openclaw chat / tui

在对话里粘贴上面任一模板即可。底部应显示：

```text
modelstudio/qwen3.5-plus
```

若报 `auth or provider access failed for modelstudio`，先执行 `/auth modelstudio`。

### CLI 单轮

```bash
openclaw agent --agent main -m "请对 002167.SZ 做快速单票研究（模板 B，A股）"
```

---

## 脚本手动验证（可选）

```bash
REPO=~/GoProject/src/github.com/BlackBN/OpenClawSkill/skills/shared

# A 股 · 板块轮动
python3 $REPO/sector-radar/scripts/fetch_data.py \
  512480 512400 159928 515030 512690 --benchmark 510300

# A 股 · 多因子选股（稀土/锆主题）
python3 $REPO/stock-screener/scripts/fetch_data.py \
  --tickers 002167.SZ 600111.SS 600392.SS 000831.SZ --style growth --pe 0 --roe 0

# A 股 · 沪深300 内价值选股
python3 $REPO/stock-screener/scripts/fetch_data.py \
  --index csi300 --style value --pe 25 --roe 10

# 业务 / 竞争 / 质量 / 估值
python3 $REPO/business-profile/scripts/fetch_data.py 301366.SZ --peers 002916.SZ 002463.SZ 300476.SZ
python3 $REPO/competitor-analysis/scripts/fetch_data.py 002167.SZ 600111.SS 600392.SS
python3 $REPO/business-quality/scripts/fetch_data.py 002167.SZ
python3 $REPO/valuation-matrix/scripts/fetch_data.py 002167.SZ

# 组合诊断
python3 $REPO/portfolio-monitor/scripts/fetch_data.py "002167.SZ:30 600111.SS:40 600392.SS:30"
```

---

## 注意事项

| 项目 | 说明 |
|------|------|
| 数据源 | **A 股/港股**：akshare + 东方财富；**美股**：yfinance |
| A 股局限 | 部分公司 ROE/负债字段缺失，脚本会降权并提示；分析师一致预期常无 |
| 网络 | 东财/akshare 偶发空数据或代理错误，可间隔 30s 重试 |
| ST 股 | stock-screener 自动剔除；business-quality 会标注 ST 风险 |
| 打板/短线 | 模板 D（momentum）仅覆盖趋势+基本面；打板需额外要求「涨停梯队/情绪/龙虎榜/资金面」 |
| 非投顾 | 输出为研究辅助，决策需自行判断 |

---

## Skill 与 Prompt 对应关系

```text
用户意图              →  优先 Skill
─────────────────────────────────────
哪个板块强/该配什么ETF  →  sector-radar
筛股票/找候选           →  stock-screener
公司做什么/行业/SWOT    →  business-profile
同行里谁更强            →  competitor-analysis
公司质地/护城河         →  business-quality
贵不贵/合理价           →  valuation-matrix
持仓风险/分散度         →  portfolio-monitor
```
