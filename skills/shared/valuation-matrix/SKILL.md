---
name: valuation-matrix
description: "多方法估值：DCF、反向DCF、PE/PB、EV/EBITDA、FCF收益率、分析师共识(A股常缺失)。用户问合理价、贵不贵、目标价区间、市场在定价多少成长时使用。勿用于批量选股或竞争对比。"
---

# 估值矩阵（valuation-matrix）

**做什么：** 用 5 种独立方法 + 反向 DCF **三角验证** 合理价值区间。回答：「这票值多少钱？现价隐含了什么预期？」

**适合谁：** 已有候选股，买入前最后一道量化关。

**A 股/HK 注意：** 东财/akshare 财报可支撑 DCF 与倍数；**卖方一致预期目标价在 A 股常缺失**，脚本会自动降权或跳过分析师法，勿强行解读。

## 数据来源

| 市场 | 数据源 | 说明 |
|------|--------|------|
| A 股 | akshare + 东财 | DCF、PE、PB、EV/EBITDA；共识价常无 |
| 港股 | akshare | 部分字段缺失时用历史 CAGR 兜底 |
| 美股 | yfinance | 含 analyst consensus |

行业倍数预设见脚本内 `_CN_MULTIPLES` / `_HK_MULTIPLES`（按申万/东财行业关键词映射）。

## 方法一览

| 方法 | 类型 | 回答的问题 | 权重 |
|------|------|------------|------|
| DCF（5 年） | 绝对 | 未来现金流现值 | 30% |
| PE 倍数 | 相对 | 盈利定价 | 20% |
| EV/EBITDA | 相对 | 资本结构中性运营估值 | 20% |
| FCF 收益率 | 相对 | 股东真实现金回报 | 15% |
| 分析师共识 | 市场 | 卖方预期（A 股常缺） | 15% |
| 反向 DCF | 洞察 | 现价隐含 FCF 增速 | 不计入综合分 |

缺数据的方法权重 **按比例** 分给其余方法；报告会写明实际权重。

### DCF 要点

1. 基准 FCF：多年 OCF−Capex 均值，平滑营运资本波动  
2. 增速：分析师预期 → forward/trailing EPS → 历史 CAGR → 默认 5%  
3. 5 年显性期 + Gordon 永续（2.5%）  
4. WACC：CAPM（无风险 + β×ERP，含杠杆调整）  

情景：

- **悲观**：增速 ×0.5，WACC +2pp  
- **基准**：如上  
- **乐观**：增速 ×1.5，WACC −1pp  

### 反向 DCF

给定现价，反推市场隐含的 FCF 增速，与分析师/历史对比：

- 隐含增速 >> 共识 → 定价偏乐观  
- 隐含增速 << 历史 → 可能过度悲观  

### 相对倍数

按 **行业** 给 bear/base/bull 倍数区间；A 股科技、消费、银行差异大。  
脚本会在实际 PE/EV 超出区间时自动放宽 band。

### 局限

- DCF 对增速/WACC 极敏感，终值常占 60–80%  
- 银行 OCF 含存贷流，DCF/FCF 法不适用，靠 PE  
- 高增长、负 FCF 公司主要看 PE/EV/共识  
- A 股缺少一致预期时，综合价更依赖 DCF + 历史倍数

## 脚本用法

```bash
python3 scripts/fetch_data.py 600519.SS           # 茅台
python3 scripts/fetch_data.py 002167.SZ           # 东方锆业
python3 scripts/fetch_data.py 0700.HK             # 腾讯
python3 scripts/fetch_data.py NVDA MSFT           # 美股对比
```

**输出：** stdout 含 fair value 区间、各方法对比、反向 DCF、假设表；stderr JSON。

## 跑完脚本后你要做什么

### 1. 先给估值结论

现价 vs 基准合理价：便宜 / 合理 / 偏贵；给出 bear/base/bull 区间。

### 2. 方法分歧

DCF 低、PE 高 → 现金流增速跟不上盈利叙事；共识远高于 DCF → 卖方偏乐观。

### 3. 解读反向 DCF

「市场定价未来 5 年 FCF 年化增 XX%，分析师只有 YY%」—— 这是 A 股特别有用的预期锚。

### 4. 敏感假设

高 β 股 WACC 微调即大幅改价；成熟公司终值占比高 → 永续增长率假设关键。

### 5. 决策衔接

- 增速能否兑现 → `business-quality`  
- 仓位与止损 → 用户自有风控  
- 估值鸡肋（不贵不便宜）→ 等待 catalyst 或换标的
