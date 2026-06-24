#!/usr/bin/env python3
"""
business-profile: structured business / industry facts for fundamental narrative.

Usage:
    python3 scripts/fetch_data.py 301366.SZ
    python3 scripts/fetch_data.py 301366.SZ --peers 002916.SZ 002463.SZ 300476.SZ
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2]
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from _data.freshness import format_freshness_md  # noqa: E402
from _data.profile import get_business_profile  # noqa: E402
from _data.provider import detect_market, get_info  # noqa: E402


def _fmt(v, suffix=""):
    if v is None:
        return "—"
    return f"{v}{suffix}"


def _segment_table(rows: list[dict], title: str) -> list[str]:
    lines = [f"### {title}", "", "| 构成 | 收入(亿) | 占比% | 毛利率% |", "|------|---------|-------|---------|"]
    if not rows:
        lines.append("| — | — | — | — |")
        return lines
    for r in rows[:8]:
        lines.append(
            f"| {r.get('name', '—')} | {_fmt(r.get('revenue_yi'))} | "
            f"{_fmt(r.get('revenue_share_pct'))} | {_fmt(r.get('gross_margin_pct'))} |"
        )
    lines.append("")
    return lines


def format_report(data: dict, peers: list[str] | None = None) -> str:
    lines = [
        f"# 业务基本面画像 — {data['ticker']} {data.get('name', '')}",
        f"\n_Generated: {datetime.now().strftime('%Y-%m-%d')}_\n",
    ]
    lines.extend(format_freshness_md(None, data).splitlines())
    lines.append("")

    snap = data.get("snapshot") or {}
    main = data.get("main_business") or {}
    seg = data.get("segments") or {}
    fh = data.get("financial_highlights") or {}
    ttm = fh.get("ttm") or {}

    lines += [
        "## 一、公司快照（数据已验证）",
        "",
        f"- **代码**：{data['ticker']} | **行业**：{data.get('industry', '—')}",
        f"- **现价**：{snap.get('currency', 'CNY')} {_fmt(snap.get('price'))} | "
        f"**PE(TTM)**：{_fmt(snap.get('pe_trailing'))} | **市值**：{_fmt(snap.get('market_cap_yi'))} 亿",
        f"- **主营业务**：{main.get('main_business') or '—'}",
        f"- **产品/服务**：{main.get('product_names') or main.get('product_type') or '—'}",
        "",
    ]

    if ttm.get("revenue_yi"):
        lines.append(
            f"**TTM（{ttm.get('period', '—')}）**：营收 {ttm['revenue_yi']} 亿，"
            f"净利润 {_fmt(ttm.get('net_income_yi'))} 亿，"
            f"营收 YoY {_fmt(ttm.get('revenue_yoy_pct'), '%')}"
        )
        lines.append("")

    if seg.get("report_date"):
        lines += [
            f"## 二、收入结构（来源：主营构成，报告期 {seg['report_date']}）",
            "",
        ]
        lines += _segment_table(seg.get("by_product") or [], "按产品/服务")
        lines += _segment_table(seg.get("by_industry") or [], "按下游行业")
        lines += _segment_table(seg.get("by_region") or [], "按地区")

    annual = fh.get("annual") or {}
    if annual:
        lines += ["## 三、财务轨迹（历史年报）", "", "| 年份 | 营收(亿) | 毛利率% | 净利率% | 净利润(亿) |", "|------|---------|---------|---------|-----------|"]
        for yr in sorted(annual.keys()):
            a = annual[yr]
            lines.append(
                f"| {yr} | {_fmt(a.get('revenue_yi'))} | {_fmt(a.get('gross_margin_pct'))} | "
                f"{_fmt(a.get('net_margin_pct'))} | {_fmt(a.get('net_income_yi'))} |"
            )
        if fh.get("revenue_cagr_pct") is not None:
            lines.append(f"\n**营收 CAGR（可用年份）**：{fh['revenue_cagr_pct']:+.1f}%")
        lines.append("")

    holders = data.get("shareholders") or []
    if holders:
        lines += ["## 四、股权结构（前五大股东）", "", "| 股东 | 持股比例% | 性质 | 截至 |", "|------|----------|------|------|"]
        for h in holders:
            lines.append(f"| {h.get('name', '—')} | {_fmt(h.get('pct'))} | {h.get('nature', '—')} | {h.get('as_of', '—')} |")
        lines.append("")

    peer_line = " ".join(peers) if peers else "（请 Agent 根据行业补充 3–5 家对标公司，并调用 competitor-analysis）"
    lines += [
        "## 五、待 Agent 深化的专业分析（基于以上数据）",
        "",
        "> 以下章节必须由 Agent 结合数据 + 搜索（年报/招股书/行业研报）完成，事实与判断须分层标注。",
        "",
        "### 5.1 投资逻辑（3 条可证伪要点）",
        "- [ ] 逻辑 1：… → 验证指标：…",
        "- [ ] 逻辑 2：… → 验证指标：…",
        "- [ ] 逻辑 3：… → 验证指标：…",
        "",
        "### 5.2 商业模式与单位经济",
        "- 价值主张 / 收费模式 / 客户类型",
        "- 轻资产 vs 重资产；人均产值、产能利用率（制造业必填）",
        "",
        "### 5.3 产业链位置与竞争格局",
        f"- 建议对标：{peer_line}",
        "- 利润池在上游/中游/下游哪一环？与龙头差异？",
        "",
        "### 5.4 SWOT（每条须引用数据或来源）",
        "| | 内容 | 证据 |",
        "|---|------|------|",
        "| 优势(S) | | |",
        "| 劣势(W) | | |",
        "| 机会(O) | | |",
        "| 威胁(T) | | |",
        "",
        "### 5.5 未来 12–36 个月催化剂 & 跟踪 KPI",
        "- 催化剂：…",
        "- KPI：…",
        "",
        "### 5.6 风险矩阵",
        "| 风险 | 概率 | 影响 | 触发信号 |",
        "|------|------|------|----------|",
        "",
        "---",
        "**下一步**：`competitor-analysis`（同行对标）→ `business-quality`（财务质地）→ `valuation-matrix`（估值）",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Business profile data fetcher")
    parser.add_argument("tickers", nargs="+", help="Ticker(s), e.g. 301366.SZ")
    parser.add_argument("--peers", nargs="*", default=[], help="Suggested peer tickers for comparison")
    args = parser.parse_args()

    ticker = args.tickers[0]
    print(f"Fetching {ticker}...", file=sys.stderr)

    data = get_business_profile(ticker)
    if data.get("error"):
        print(json.dumps(data, ensure_ascii=False, indent=2), file=sys.stderr)
        print(f"ERROR: {data['error']}", file=sys.stderr)
        sys.exit(1)

    data["assessment_date"] = datetime.now().strftime("%Y-%m-%d")
    data["suggested_peers"] = args.peers

    report = format_report(data, peers=args.peers or None)
    print(report)
    print("\n---JSON---", file=sys.stderr)
    print(json.dumps(data, ensure_ascii=False, indent=2), file=sys.stderr)

    snap = data.get("snapshot") or {}
    print(
        f"  → {data['ticker']}: {data.get('name')} | "
        f"Price={snap.get('price')} | Segments={len((data.get('segments') or {}).get('by_product') or [])} | "
        f"RevCAGR={data.get('financial_highlights', {}).get('revenue_cagr_pct')}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
