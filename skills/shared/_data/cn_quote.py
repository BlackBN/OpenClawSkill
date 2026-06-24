"""Multi-source A-share quote fetcher with merge + fallback."""

from __future__ import annotations

from typing import Callable

from . import alltick, cn_fallback
from .market import normalize_ticker
from . import quote_merge

_QUOTE_CACHE: dict[str, tuple[float, dict]] = {}

_FREE_SOURCES: list[tuple[str, Callable[[str], dict | None]]] = [
    ("eastmoney_ulist", cn_fallback.get_quote_eastmoney_ulist),
    ("eastmoney", cn_fallback.get_quote_eastmoney),
    ("tencent", cn_fallback.get_quote_tencent),
    ("sina", cn_fallback.get_quote_sina),
    ("kline_close", cn_fallback.get_quote_from_kline),
]


def _sources() -> list[tuple[str, Callable[[str], dict | None]]]:
    out: list[tuple[str, Callable[[str], dict | None]]] = []
    if alltick.is_configured():
        out.append(("alltick", lambda c: alltick.get_quote(c, "CN")))
    out.extend(_FREE_SOURCES)
    return out


def get_quote(code: str) -> dict | None:
    """Fetch quote: AllTick (optional) → 东财 → 腾讯 → 新浪 → K线兜底."""
    display, raw, _ = normalize_ticker(code)
    return quote_merge.fetch_merged_quote(
        raw, display, "CNY", _sources(), _QUOTE_CACHE
    )
