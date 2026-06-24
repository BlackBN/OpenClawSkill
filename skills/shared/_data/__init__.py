"""Shared market data layer for alpha-skills (CN/HK/US)."""

from .provider import (
    BENCHMARKS,
    MARKET_CONFIGS,
    detect_market,
    download_closes,
    enrich_screener_row,
    get_index_constituents,
    get_annual_financials,
    get_benchmark,
    get_etf_history,
    get_history,
    get_info,
    get_market_config,
    get_tax_rate,
    normalize_ticker,
    screen_market,
)

__all__ = [
    "detect_market",
    "get_tax_rate",
    "get_market_config",
    "get_benchmark",
    "normalize_ticker",
    "get_info",
    "get_history",
    "get_etf_history",
    "get_annual_financials",
    "download_closes",
    "screen_market",
    "get_index_constituents",
    "BENCHMARKS",
    "MARKET_CONFIGS",
]
