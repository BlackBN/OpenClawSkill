"""Eastmoney HK kline with Tencent fallback."""

from __future__ import annotations

import time

import pandas as pd
import requests

from . import hk_fallback
from .market import hk_secid, normalize_ticker

_SESSION = requests.Session()
_SESSION.trust_env = False
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
})

_KLINE_CACHE: dict[str, tuple[float, pd.DataFrame]] = {}
_CACHE_TTL_SEC = 45


def _cache_get(key: str) -> pd.DataFrame | None:
    item = _KLINE_CACHE.get(key)
    if not item:
        return None
    ts, val = item
    if time.time() - ts > _CACHE_TTL_SEC:
        _KLINE_CACHE.pop(key, None)
        return None
    return val


def _cache_set(key: str, val: pd.DataFrame):
    _KLINE_CACHE[key] = (time.time(), val)


def _get_json(url: str, params: dict, *, timeout: int = 20, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            r = _SESSION.get(url, params=params, timeout=timeout)
            if r.status_code in (429, 502, 503):
                time.sleep(0.8 * (2 ** attempt))
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt < retries - 1:
                time.sleep(0.5 * (2 ** attempt))
    return None


def get_kline(code: str, days: int = 400) -> pd.DataFrame:
    display, raw, _ = normalize_ticker(code)
    cache_key = f"{raw}:{days}"
    cached = _cache_get(cache_key)
    if cached is not None and not cached.empty:
        return cached

    secid = hk_secid(raw)
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "klt": "101",
        "fqt": "1",
        "lmt": str(min(days + 30, 500)),
        "end": "20500101",
        "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    }
    payload = _get_json(url, params, timeout=20)
    if payload:
        klines = (payload.get("data") or {}).get("klines") or []
        rows = []
        for line in klines:
            parts = line.split(",")
            if len(parts) < 6:
                continue
            rows.append({
                "Date": parts[0],
                "Open": float(parts[1]),
                "Close": float(parts[2]),
                "High": float(parts[3]),
                "Low": float(parts[4]),
                "Volume": float(parts[5]),
            })
        if rows:
            df = pd.DataFrame(rows)
            df["Date"] = pd.to_datetime(df["Date"])
            out = df.set_index("Date").sort_index()
            _cache_set(cache_key, out)
            return out

    out = hk_fallback.get_kline_tencent(raw, days=days)
    if not out.empty:
        _cache_set(cache_key, out)
    return out
