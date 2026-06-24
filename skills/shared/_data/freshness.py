"""Data freshness helpers — period keys, TTM, report metadata."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

try:
    import pandas as pd
except ImportError:
    pd = None


def period_key_from_report(s: str | None) -> str | None:
    """Map 报告期 → sortable key: 2025Q1 … 2025Q4, or 2025A for year-only."""
    if not s:
        return None
    text = str(s).strip()
    m = re.search(r"(20\d{2})", text)
    if not m:
        return None
    year = m.group(1)
    md = re.search(r"[-/年](\d{1,2})[-/月]?(\d{1,2})?", text)
    if not md:
        return f"{year}A"
    month = int(md.group(1))
    if month <= 3:
        return f"{year}Q1"
    if month <= 6:
        return f"{year}Q2"
    if month <= 9:
        return f"{year}Q3"
    return f"{year}Q4"


def period_sort_key(pk: str) -> tuple[int, int]:
    if pk.endswith("A"):
        return int(pk[:-1]), 5
    m = re.match(r"(\d{4})Q(\d)", pk)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(20\d{2})", pk)
    return (int(m.group(1)), 0) if m else (0, 0)


def sorted_period_keys(keys: list[str]) -> list[str]:
    return sorted(keys, key=period_sort_key)


def latest_dict_entry(d: dict[str, Any]) -> tuple[str, Any] | None:
    if not d:
        return None
    k = sorted_period_keys(list(d.keys()))[-1]
    return k, d[k]


def compute_ttm(quarterly: dict[str, float], min_quarters: int = 4) -> dict | None:
    """Sum the latest *min_quarters* quarterly values (TTM)."""
    qkeys = [k for k in sorted_period_keys(list(quarterly.keys())) if "Q" in k]
    if len(qkeys) < min_quarters:
        return None
    use = qkeys[-min_quarters:]
    total = sum(quarterly[k] for k in use if quarterly.get(k) is not None)
    return {
        "as_of_period": use[-1],
        "periods": use,
        "value": total,
    }


def yoy_pct(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior == 0:
        return None
    return round((current / prior - 1) * 100, 2)


def build_freshness(
    *,
    quote: dict | None = None,
    hist=None,
    annual_periods: list[str] | None = None,
    quarterly_periods: list[str] | None = None,
    ttm: dict | None = None,
    warnings: list[str] | None = None,
) -> dict:
    now = datetime.now()
    price_date = None
    if hist is not None and not getattr(hist, "empty", True):
        try:
            price_date = hist.index[-1].strftime("%Y-%m-%d")
        except Exception:
            pass

    quote = quote or {}
    ann = sorted_period_keys(annual_periods or [])
    qtr = sorted_period_keys(quarterly_periods or [])

    return {
        "fetched_at": now.strftime("%Y-%m-%d %H:%M"),
        "quote_as_of": now.strftime("%Y-%m-%d"),
        "price": quote.get("currentPrice") or quote.get("regularMarketPrice"),
        "price_date": price_date,
        "latest_annual_period": ann[-1] if ann else None,
        "latest_quarterly_period": qtr[-1] if qtr else None,
        "ttm_as_of": (ttm or {}).get("revenue_as_of") or (ttm or {}).get("as_of_period"),
        "ttm_available": bool(ttm and ttm.get("revenue") is not None),
        "warnings": warnings or [],
    }


def format_freshness_md(freshness: dict | None, fin: dict | None = None) -> str:
    """Markdown block for skill reports."""
    f = freshness or (fin or {}).get("freshness") or {}
    if not f:
        return ""

    lines = [
        "## 数据时效说明",
        "",
        "| 项目 | 值 |",
        "|------|-----|",
        f"| 拉取时间 | {f.get('fetched_at', '—')} |",
        f"| 股价日期 | {f.get('price_date') or '—'} |",
        f"| 最新股价 | {f.get('price') if f.get('price') is not None else '—'} |",
        f"| 最新年报期 | {f.get('latest_annual_period') or '—'} |",
        f"| 最新季报期 | {f.get('latest_quarterly_period') or '—'} |",
    ]

    ttm = (fin or {}).get("ttm") or {}
    if f.get("ttm_available") and ttm:
        rev = ttm.get("revenue")
        ni = ttm.get("net_income")
        rev_b = round(rev / 1e8, 2) if rev else None
        ni_b = round(ni / 1e8, 2) if ni else None
        lines.append(f"| TTM 截止 | {ttm.get('as_of_period', '—')} |")
        if rev_b is not None:
            lines.append(f"| TTM 营收 (亿) | {rev_b} |")
        if ni_b is not None:
            lines.append(f"| TTM 净利润 (亿) | {ni_b} |")
        if ttm.get("revenue_yoy_pct") is not None:
            lines.append(f"| TTM 营收 YoY | {ttm['revenue_yoy_pct']:+.1f}% |")
        if ttm.get("net_income_yoy_pct") is not None:
            lines.append(f"| TTM 净利 YoY | {ttm['net_income_yoy_pct']:+.1f}% |")
    else:
        lines.append("| TTM | 不可用（季报不足 4 期） |")

    for w in f.get("warnings") or []:
        lines.append(f"\n⚠ _{w}_")

    lines.append("")
    return "\n".join(lines)
