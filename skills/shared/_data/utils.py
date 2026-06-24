"""Shared utilities for data providers."""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta

try:
    import numpy as np
    import pandas as pd
except ImportError:
    pd = None
    np = None


def safe_float(val, default=None):
    if val is None or val == "" or val == "-":
        return default
    try:
        if pd is not None:
            v = float(val)
            if pd.notna(v) and np is not None and np.isfinite(v):
                return round(v, 4)
            return default
        v = float(val)
        return round(v, 4)
    except (TypeError, ValueError):
        return default


def parse_cn_number(text) -> float | None:
    """Parse numbers like '166.2亿', '12.5%', '1,234.56'."""
    if text is None:
        return None
    s = str(text).strip().replace(",", "")
    if not s or s in ("-", "--", "nan", "None"):
        return None
    mult = 1.0
    if s.endswith("%"):
        s = s[:-1]
        mult = 0.01 if mult == 1.0 else mult
    if "亿" in s:
        s = s.replace("亿", "")
        mult *= 1e8
    elif "万" in s:
        s = s.replace("万", "")
        mult *= 1e4
    val = safe_float(s)
    return round(val * mult, 4) if val is not None else None


def date_range(days: int) -> tuple[str, str]:
    end = datetime.today()
    start = end - timedelta(days=days + 30)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def history_to_ohlcv(df, date_col="日期", rename=None) -> "pd.DataFrame":
    """Normalize akshare hist → yfinance-like OHLCV."""
    if df is None or df.empty:
        return pd.DataFrame()
    rename = rename or {
        "日期": "Date",
        "开盘": "Open",
        "收盘": "Close",
        "最高": "High",
        "最低": "Low",
        "成交量": "Volume",
    }
    out = df.rename(columns=rename).copy()
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"])
        out = out.set_index("Date").sort_index()
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def compute_beta(closes: "pd.Series", benchmark_closes: "pd.Series") -> float | None:
    if closes is None or benchmark_closes is None:
        return None
    aligned = pd.concat([closes.pct_change(), benchmark_closes.pct_change()], axis=1).dropna()
    if len(aligned) < 60:
        return None
    cov = aligned.cov().iloc[0, 1]
    var = aligned.iloc[:, 1].var()
    if var and var > 0:
        return round(float(cov / var), 3)
    return None


def throttle(seconds: float = 0.15):
    time.sleep(seconds)


def year_key_from_report(s: str) -> str | None:
    if not s:
        return None
    m = re.search(r"(20\d{2})", str(s))
    return m.group(1) if m else None
