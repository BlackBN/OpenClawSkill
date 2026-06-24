"""Shared multi-source quote merge + cache."""

from __future__ import annotations

import time
from typing import Callable

_MERGE_KEYS = (
    "symbol", "shortName", "longName", "currentPrice", "regularMarketPrice",
    "marketCap", "trailingPE", "priceToBook", "returnOnEquity", "currency",
    "price_date", "_stale",
)

_CACHE_TTL_SEC = 45


def cache_get(store: dict[str, tuple[float, dict]], key: str) -> dict | None:
    item = store.get(key)
    if not item:
        return None
    ts, val = item
    if time.time() - ts > _CACHE_TTL_SEC:
        store.pop(key, None)
        return None
    return val


def cache_set(store: dict[str, tuple[float, dict]], key: str, val: dict):
    store[key] = (time.time(), val)


def merge_quotes(base: dict | None, patch: dict | None) -> dict | None:
    if not patch:
        return base
    if not base:
        out = dict(patch)
        out["_sources"] = [patch.get("_source", "unknown")]
        return out

    out = dict(base)
    sources = list(out.get("_sources") or [])
    src = patch.get("_source")
    if src and src not in sources:
        sources.append(src)
    out["_sources"] = sources

    for key in _MERGE_KEYS:
        if out.get(key) is None and patch.get(key) is not None:
            out[key] = patch[key]

    if patch.get("_stale"):
        if not base.get("_stale"):
            out["_stale"] = False
    elif patch.get("_stale") is False:
        out["_stale"] = False

    if not out.get("_source"):
        out["_source"] = patch.get("_source")
    return out


def has_price(q: dict | None) -> bool:
    if not q:
        return False
    price = q.get("currentPrice")
    return price is not None and price > 0


def fetch_merged_quote(
    raw: str,
    display: str,
    currency: str,
    sources: list[tuple[str, Callable[[str], dict | None]]],
    cache: dict[str, tuple[float, dict]],
) -> dict | None:
    cached = cache_get(cache, raw)
    if cached:
        return cached

    merged: dict | None = None
    for _name, fetcher in sources:
        try:
            partial = fetcher(raw)
        except Exception:
            partial = None
        merged = merge_quotes(merged, partial)
        if has_price(merged) and merged.get("trailingPE") is not None:
            break

    if not merged:
        return None

    merged.setdefault("symbol", display)
    merged.setdefault("shortName", raw)
    merged.setdefault("longName", raw)
    merged.setdefault("currency", currency)
    cache_set(cache, raw, merged)
    return merged
