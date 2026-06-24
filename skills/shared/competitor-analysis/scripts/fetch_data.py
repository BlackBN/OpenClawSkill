#!/usr/bin/env python3
"""
competitor-analysis: Rank competitors within an industry by relative competitive position.

Usage:
    python3 scripts/fetch_data.py NVDA AMD INTC QCOM
    python3 scripts/fetch_data.py MSFT GOOGL META
"""

import sys, json
from datetime import datetime
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2]
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from _data.provider import detect_market, get_annual_financials, get_tax_rate  # noqa: E402
from _data.freshness import format_freshness_md  # noqa: E402

try:
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"ERROR: Missing dependency — {e}. Run: pip install akshare pandas numpy", file=sys.stderr)
    sys.exit(1)


def safe_float(val, default=None):
    try:
        v = float(val)
        return round(v, 4) if pd.notna(v) and np.isfinite(v) else default
    except Exception:
        return default


def fetch_company(ticker_sym):
    fin = get_annual_financials(ticker_sym, years=4)
    market = detect_market(ticker_sym)
    tax_rate = get_tax_rate(market)
    name = fin.get("name", ticker_sym)

    if fin.get("error"):
        return {"ticker": fin.get("ticker", ticker_sym.upper()), "name": name, "error": fin["error"]}

    revenue = fin.get("revenue", {})
    gross_profit = fin.get("gross_profit", {})
    net_income = fin.get("net_income", {})
    ebit = fin.get("ebit", {})
    rd = fin.get("rd", {})
    equity = fin.get("equity", {})
    total_debt = fin.get("total_debt", {})
    cash = fin.get("cash", {})

    sorted_years = sorted(revenue.keys())
    annual = {}

    for yr in sorted_years:
        rev = revenue.get(yr)
        gp = gross_profit.get(yr)
        ni = net_income.get(yr)
        eb = ebit.get(yr)
        eq = equity.get(yr)
        td = total_debt.get(yr, 0) or 0
        ca = cash.get(yr, 0) or 0
        r = rd.get(yr)

        gm = round(gp / rev * 100, 2) if gp and rev and rev != 0 else None
        nm = round(ni / rev * 100, 2) if ni and rev and rev != 0 else None
        rd_pct = round(r / rev * 100, 2) if r and rev and rev != 0 else None

        nopat = eb * (1 - tax_rate) if eb else None
        ic = td + (eq or 0) - ca
        roic = round(nopat / ic * 100, 2) if nopat and ic and ic != 0 else None

        annual[yr] = {
            "revenue_B": round(rev / 1e9, 2) if rev else None,
            "gross_margin_pct": gm, "net_margin_pct": nm,
            "rd_intensity_pct": rd_pct, "roic_pct": roic,
        }

    # Summary metrics
    rev_vals = [revenue.get(y) for y in sorted_years if revenue.get(y)]
    gm_vals = [annual[y]["gross_margin_pct"] for y in sorted_years if annual[y].get("gross_margin_pct") is not None]
    nm_vals = [annual[y]["net_margin_pct"] for y in sorted_years if annual[y].get("net_margin_pct") is not None]
    rd_vals = [annual[y]["rd_intensity_pct"] for y in sorted_years if annual[y].get("rd_intensity_pct") is not None]
    roic_vals = [annual[y]["roic_pct"] for y in sorted_years if annual[y].get("roic_pct") is not None]

    rev_cagr = None
    if len(rev_vals) >= 2 and rev_vals[0] and rev_vals[0] > 0:
        try:
            n = len(rev_vals) - 1
            rev_cagr = round(((rev_vals[-1] / rev_vals[0]) ** (1 / n) - 1) * 100, 2)
        except Exception:
            pass

    gm_change = round(gm_vals[-1] - gm_vals[0], 2) if len(gm_vals) >= 2 else None
    latest_rev_B = round(rev_vals[-1] / 1e9, 2) if rev_vals else None

    return {
        "ticker": fin.get("ticker", ticker_sym.upper()),
        "name": name,
        "annual": annual,
        "summary": {
            "latest_revenue_B": latest_rev_B,
            "latest_annual_period": sorted_years[-1] if sorted_years else None,
            "revenue_cagr_pct": rev_cagr,
            "avg_gross_margin_pct": round(sum(gm_vals) / len(gm_vals), 2) if gm_vals else None,
            "avg_net_margin_pct": round(sum(nm_vals) / len(nm_vals), 2) if nm_vals else None,
            "gross_margin_change_pp": gm_change,
            "avg_rd_intensity_pct": round(sum(rd_vals) / len(rd_vals), 2) if rd_vals else None,
            "avg_roic_pct": round(sum(roic_vals) / len(roic_vals), 2) if roic_vals else None,
        },
        "freshness": fin.get("freshness") or {},
        "ttm": fin.get("ttm") or {},
    }


def rank_score(companies, metric_key, higher_is_better=True):
    """Rank companies by metric. Returns {ticker: {rank, score_0_100, value}}."""
    scored = [(c["ticker"], c["summary"].get(metric_key)) for c in companies if c.get("summary")]
    scored = [(t, v) for t, v in scored if v is not None]
    scored.sort(key=lambda x: x[1], reverse=higher_is_better)
    n = len(scored)
    result = {}
    for i, (ticker, val) in enumerate(scored):
        rank = i + 1
        score = round((n - rank) / (n - 1) * 100, 1) if n > 1 else 50.0
        result[ticker] = {"rank": rank, "score": score, "value": val}
    return result


# Dimension weights
DIMENSIONS = {
    "revenue_growth":   {"key": "revenue_cagr_pct",       "weight": 0.30, "higher": True,  "label": "Revenue Growth"},
    "profitability":    {"key": "avg_gross_margin_pct",    "weight": 0.25, "higher": True,  "label": "Profitability"},
    "efficiency":       {"key": "avg_net_margin_pct",      "weight": 0.20, "higher": True,  "label": "Efficiency"},
    "margin_momentum":  {"key": "gross_margin_change_pp",  "weight": 0.15, "higher": True,  "label": "Margin Momentum"},
    "rd_investment":    {"key": "avg_rd_intensity_pct",    "weight": 0.10, "higher": True,  "label": "R&D Investment"},
}


def compute_rankings(companies):
    """Compute per-dimension ranks and composite competitive score."""
    dim_ranks = {}
    for dim_name, dim in DIMENSIONS.items():
        dim_ranks[dim_name] = rank_score(companies, dim["key"], dim["higher"])

    # Composite score (weighted average of dimension scores)
    composite = {}
    for c in companies:
        tk = c["ticker"]
        if c.get("error"):
            continue
        total_w = 0
        weighted_sum = 0
        detail = {}
        for dim_name, dim in DIMENSIONS.items():
            if tk in dim_ranks[dim_name]:
                s = dim_ranks[dim_name][tk]["score"]
                w = dim["weight"]
                weighted_sum += s * w
                total_w += w
                detail[dim_name] = dim_ranks[dim_name][tk]
        score = round(weighted_sum / total_w, 1) if total_w > 0 else None
        composite[tk] = {"score": score, "dimensions": detail}

    return composite, dim_ranks


def compute_revenue_share(companies):
    """Compute revenue share within peer set."""
    revs = [(c["ticker"], c["summary"].get("latest_revenue_B"))
            for c in companies if c.get("summary") and c["summary"].get("latest_revenue_B")]
    total = sum(v for _, v in revs) if revs else 0
    return {tk: round(v / total * 100, 1) if total > 0 else None for tk, v in revs}


def format_report(companies, composite, rev_shares):
    lines = []
    lines.append("# Competitive Dynamics Analysis")
    lines.append(f"\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")
    if companies and not companies[0].get("error"):
        lines.append(format_freshness_md(None, companies[0]))

    # Sort by composite score
    ranked = sorted(
        [(c, composite.get(c["ticker"], {}).get("score")) for c in companies if not c.get("error")],
        key=lambda x: x[1] or 0, reverse=True)

    # Main ranking table
    lines.append("## Competitive Ranking\n")
    lines.append("| # | Ticker | Company | Score | Growth | Profitability | Efficiency | Margin Trend | R&D | Rev Share |")
    lines.append("|---|--------|---------|-------|--------|---------------|------------|-------------|-----|-----------|")
    for i, (c, score) in enumerate(ranked, 1):
        tk = c["ticker"]
        s = c["summary"]
        cagr = f"{s['revenue_cagr_pct']:+.1f}%" if s.get('revenue_cagr_pct') is not None else "—"
        gm = f"{s['avg_gross_margin_pct']:.1f}%" if s.get('avg_gross_margin_pct') is not None else "—"
        nm = f"{s['avg_net_margin_pct']:.1f}%" if s.get('avg_net_margin_pct') is not None else "—"
        gmc = f"{s['gross_margin_change_pp']:+.1f}pp" if s.get('gross_margin_change_pp') is not None else "—"
        rd = f"{s['avg_rd_intensity_pct']:.1f}%" if s.get('avg_rd_intensity_pct') is not None else "—"
        share = f"{rev_shares.get(tk, 0):.1f}%" if rev_shares.get(tk) is not None else "—"
        lines.append(f"| {i} | **{tk}** | {c['name'][:25]} | {score} | {cagr} | {gm} | {nm} | {gmc} | {rd} | {share} |")

    # Per-company detail
    for c, score in ranked:
        tk = c["ticker"]
        s = c["summary"]
        lines.append(f"\n## {tk} — {c['name']}")
        lines.append(f"\n**Competitive Score: {score}/100** | Revenue share: {rev_shares.get(tk, 'N/A')}%\n")

        # Annual data
        years = sorted(c["annual"].keys())
        lines.append("| Year | Revenue ($B) | Gross Margin% | Net Margin% | R&D% | ROIC% |")
        lines.append("|------|-------------|---------------|-------------|------|-------|")
        for yr in years:
            m = c["annual"][yr]
            def fmt(v, suffix=""): return f"{v}{suffix}" if v is not None else "—"
            lines.append(f"| {yr} | {fmt(m.get('revenue_B'))} | {fmt(m.get('gross_margin_pct'))} | {fmt(m.get('net_margin_pct'))} | {fmt(m.get('rd_intensity_pct'))} | {fmt(m.get('roic_pct'))} |")

        # Dimension scores
        dims = composite.get(tk, {}).get("dimensions", {})
        if dims:
            lines.append("\n| Dimension | Rank | Score | Value |")
            lines.append("|-----------|------|-------|-------|")
            for dim_name, dim in DIMENSIONS.items():
                if dim_name in dims:
                    d = dims[dim_name]
                    lines.append(f"| {dim['label']} | #{d['rank']} | {d['score']:.0f} | {d['value']} |")

    # Error companies
    for c in companies:
        if c.get("error"):
            lines.append(f"\n## {c['ticker']} — ERROR: {c['error']}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/fetch_data.py TICKER1 TICKER2 [TICKER3 ...]", file=sys.stderr)
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]
    print(f"Comparing: {', '.join(tickers)}", file=sys.stderr)

    companies = []
    for sym in tickers:
        print(f"  Fetching {sym}...", file=sys.stderr)
        companies.append(fetch_company(sym))

    composite, dim_ranks = compute_rankings(companies)
    rev_shares = compute_revenue_share(companies)

    # Markdown report to stdout
    print(format_report(companies, composite, rev_shares))

    # JSON to stderr
    output = {
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "companies": {c["ticker"]: c for c in companies},
        "composite": composite,
        "revenue_shares": rev_shares,
    }
    print(f"\n---JSON---\n{json.dumps(output, indent=2, default=str)}", file=sys.stderr)


if __name__ == "__main__":
    main()
