"""Optional AllTick REST tick quote — set ALLTICK_TOKEN to enable.

Docs: https://github.com/alltick/alltick-realtime-forex-crypto-stock-tick-finance-websocket-api
Free tier trade-tick: ~1 request / 10 seconds (see interface_limitation).
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

import requests

from .market import normalize_ticker, to_alltick_code
from .utils import safe_float

_SESSION = requests.Session()
_SESSION.trust_env = False

_TOKEN = (os.environ.get("ALLTICK_TOKEN") or os.environ.get("ALLTICK_API_KEY") or "").strip()
_BASE_URL = os.environ.get(
    "ALLTICK_BASE_URL",
    "https://quote.alltick.co/quote-stock-b-api",
).rstrip("/")
_MIN_INTERVAL = float(os.environ.get("ALLTICK_MIN_INTERVAL", "10"))
_last_call = 0.0


def is_configured() -> bool:
    return bool(_TOKEN)


def _rate_ok() -> bool:
    global _last_call
    return time.time() - _last_call >= _MIN_INTERVAL


def _mark_called():
    global _last_call
    _last_call = time.time()


def _tick_time_ms(raw_ms: str | None) -> str | None:
    if not raw_ms:
        return None
    try:
        ts = int(raw_ms) / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (TypeError, ValueError, OSError):
        return None


def get_quote(code: str, market: str) -> dict | None:
    """Latest trade tick for CN / HK / US when ALLTICK_TOKEN is set."""
    if not _TOKEN or not _rate_ok():
        return None

    display, raw, mkt = normalize_ticker(code)
    market = market or mkt
    at_code = to_alltick_code(display, raw, market)
    if not at_code:
        return None

    payload = {
        "trace": str(uuid.uuid4()),
        "data": {"symbol_list": [{"code": at_code}]},
    }
    query = quote(json.dumps(payload, separators=(",", ":")))
    url = f"{_BASE_URL}/trade-tick?token={_TOKEN}&query={query}"

    try:
        r = _SESSION.get(url, timeout=12)
        _mark_called()
        if r.status_code in (429, 502, 503):
            return None
        r.raise_for_status()
        body = r.json()
    except Exception:
        return None

    if body.get("ret") != 200:
        return None

    ticks = (body.get("data") or {}).get("tick_list") or []
    if not ticks:
        return None

    tick = ticks[0]
    price = safe_float(tick.get("price"))
    if price is None or price <= 0:
        return None

    currency = {"CN": "CNY", "HK": "HKD", "US": "USD"}.get(market, "USD")
    return {
        "symbol": display,
        "shortName": raw,
        "longName": raw,
        "currentPrice": price,
        "regularMarketPrice": price,
        "marketCap": None,
        "trailingPE": None,
        "priceToBook": None,
        "returnOnEquity": None,
        "currency": currency,
        "_source": "alltick",
        "_stale": False,
        "price_date": _tick_time_ms(tick.get("tick_time")),
        "_alltick_code": at_code,
    }
