"""
Unified market data router for A-share / HK / US.

CN & HK → akshare (Eastmoney / THS)
US & others → yfinance (Yahoo Finance)
"""

from __future__ import annotations

import pandas as pd

from . import cn, hk, us
from .market import (
    BENCHMARKS,
    MARKET_CONFIGS,
    detect_market,
    get_benchmark,
    get_market_config,
    get_tax_rate,
    normalize_ticker,
)
from .utils import compute_beta, throttle

__all__ = [
    "detect_market",
    "get_tax_rate",
    "get_market_config",
    "get_benchmark",
    "BENCHMARKS",
    "MARKET_CONFIGS",
    "normalize_ticker",
    "get_info",
    "get_history",
    "download_closes",
    "get_annual_financials",
    "screen_market",
    "enrich_screener_row",
    "get_etf_history",
]


def _module(market: str):
    if market == "CN":
        return cn
    if market == "HK":
        return hk
    return us


def get_info(ticker: str) -> dict:
    display, code, market = normalize_ticker(ticker)
    mod = _module(market)
    if market == "CN":
        info = mod.get_quote(code)
    elif market == "HK":
        info = mod.get_quote(code)
    else:
        info = mod.get_quote(display)
    info.setdefault("symbol", display)
    return info


def get_history(ticker: str, days: int = 400, start: str | None = None) -> pd.DataFrame:
    display, code, market = normalize_ticker(ticker)
    mod = _module(market)
    if market in ("CN", "HK"):
        return mod.get_history(code, days=days)
    return mod.get_history(display, days=days, start=start)


def get_etf_history(ticker: str, days: int = 400) -> pd.DataFrame:
    display, code, market = normalize_ticker(ticker)
    mod = _module(market)
    if market == "CN":
        return mod.get_etf_history(code, days=days)
    if market == "HK":
        return mod.get_etf_history(display, days=days)
    return us.get_history(display, days=days)


def get_annual_financials(ticker: str, years: int = 5) -> dict:
    display, code, market = normalize_ticker(ticker)
    mod = _module(market)
    if market in ("CN", "HK"):
        return mod.get_annual_financials(code, years=years)
    return mod.get_annual_financials(display, years=years)


def download_closes(tickers: list[str], days: int = 365) -> pd.DataFrame:
    frames = {}
    for t in tickers:
        hist = get_history(t, days=days)
        display, _, _ = normalize_ticker(t)
        if hist.empty or "Close" not in hist.columns:
            continue
        frames[display] = hist["Close"]
        throttle(0.1)
    if not frames:
        return pd.DataFrame()
    out = pd.DataFrame(frames).sort_index().ffill()
    return out


def screen_market(
    region: str = "cn",
    max_pe: float = 20,
    min_roe: float = 15,
    min_mcap: float = 1e9,
    sector_keyword: str | None = None,
    industry_keyword: str | None = None,
    top: int = 25,
) -> tuple[list[dict], int]:
    region = region.lower()
    if region in ("cn", "a", "a-share", "ashare"):
        rows = cn.screen(max_pe, min_roe, min_mcap, sector_keyword, industry_keyword, top)
        return rows, len(rows)
    if region == "hk":
        rows = hk.screen(max_pe, min_roe, min_mcap, sector_keyword, industry_keyword, top)
        return rows, len(rows)
    # US via yfinance server-side
    quotes, total = us.screen_server_side(region, sector_keyword, max_pe, min_roe, min_mcap, top)
    return quotes, total


def get_index_constituents(index: str, region: str = "cn") -> list[str]:
    if region.lower() in ("cn", "a", "a-share", "ashare"):
        return cn.get_index_constituents(index)
    return []


def enrich_screener_row(ticker: str) -> dict:
    _, _, market = normalize_ticker(ticker)
    return _module(market).enrich_screener_row(ticker)


def compute_ticker_beta(ticker: str, benchmark: str | None = None) -> float | None:
    display, _, market = normalize_ticker(ticker)
    bench = benchmark or get_benchmark(market)
    hist = get_history(display, days=400)
    bench_hist = get_etf_history(bench, days=400) if market == "CN" else get_history(bench, days=400)
    if hist.empty or bench_hist.empty:
        return None
    return compute_beta(hist["Close"], bench_hist["Close"])
