"""Free CN quote/kline fallbacks — Tencent, Sina, Eastmoney mirrors."""

from __future__ import annotations

import re
import time

import pandas as pd
import requests

from .market import cn_exchange_code, normalize_ticker
from .utils import safe_float

_SESSION = requests.Session()
_SESSION.trust_env = False
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
})

_EM_HOSTS = (
    "https://push2.eastmoney.com",
    "https://82.push2.eastmoney.com",
    "https://push2delay.eastmoney.com",
)


def _tencent_symbol(raw: str) -> str:
    return f"sh{raw}" if raw.startswith(("6", "9")) else f"sz{raw}"


def _sina_symbol(raw: str) -> str:
    return _tencent_symbol(raw)


def _get_json(url: str, params: dict, *, timeout: int = 10, retries: int = 2) -> dict | None:
    for attempt in range(retries):
        try:
            r = _SESSION.get(url, params=params, timeout=timeout)
            if r.status_code in (429, 502, 503):
                time.sleep(0.4 * (2 ** attempt))
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt < retries - 1:
                time.sleep(0.3 * (2 ** attempt))
    return None


def _get_text(url: str, *, headers: dict | None = None, timeout: int = 10, retries: int = 2) -> str | None:
    for attempt in range(retries):
        try:
            r = _SESSION.get(url, headers=headers, timeout=timeout)
            if r.status_code in (429, 502, 503):
                time.sleep(0.4 * (2 ** attempt))
                continue
            r.raise_for_status()
            return r.text
        except Exception:
            if attempt < retries - 1:
                time.sleep(0.3 * (2 ** attempt))
    return None


def _quote_dict(
    display: str,
    raw: str,
    name: str,
    price: float | None,
    *,
    source: str,
    pe=None,
    pb=None,
    mcap=None,
    roe=None,
    stale: bool = False,
    price_date: str | None = None,
) -> dict | None:
    if price is None or price <= 0:
        return None
    return {
        "symbol": display,
        "shortName": name or raw,
        "longName": name or raw,
        "currentPrice": price,
        "regularMarketPrice": price,
        "marketCap": mcap,
        "trailingPE": pe,
        "priceToBook": pb,
        "returnOnEquity": roe,
        "currency": "CNY",
        "_source": source,
        "_stale": stale,
        "price_date": price_date,
    }


def get_quote_eastmoney_ulist(code: str) -> dict | None:
    """Eastmoney batch quote — lighter & often more stable than stock/get."""
    display, raw, _ = normalize_ticker(code)
    secid = f"{cn_exchange_code(raw)}.{raw}"
    params = {
        "fltt": "2",
        "invt": "2",
        "fields": "f12,f14,f2,f9,f23,f20,f184",
        "secids": secid,
    }
    for host in _EM_HOSTS:
        payload = _get_json(f"{host}/api/qt/ulist.np/get", params)
        if not payload:
            continue
        rows = (payload.get("data") or {}).get("diff") or []
        if not rows:
            continue
        row = rows[0]
        roe = safe_float(row.get("f184"))
        return _quote_dict(
            display, raw, str(row.get("f14") or raw),
            safe_float(row.get("f2")),
            source="eastmoney_ulist",
            pe=safe_float(row.get("f9")),
            pb=safe_float(row.get("f23")),
            mcap=safe_float(row.get("f20")),
            roe=roe / 100 if roe and abs(roe) > 1 else roe,
        )
    return None


def get_quote_eastmoney(code: str) -> dict | None:
    """Eastmoney single-stock endpoint (full fields, sometimes rate-limited)."""
    display, raw, _ = normalize_ticker(code)
    secid = f"{cn_exchange_code(raw)}.{raw}"
    params = {
        "secid": secid,
        "fields": "f57,f58,f43,f116,f117,f162,f167,f184,f292,f127",
    }
    for host in _EM_HOSTS:
        payload = _get_json(f"{host}/api/qt/stock/get", params)
        if not payload:
            continue
        data = payload.get("data") or {}
        price = safe_float(data.get("f43"))
        if price is not None:
            price = round(price / 100, 2)
        pe = safe_float(data.get("f162"))
        if pe is not None:
            pe = round(pe / 100, 2)
        pb = safe_float(data.get("f167"))
        if pb is not None:
            pb = round(pb / 100, 2)
        roe = safe_float(data.get("f184"))
        return _quote_dict(
            display, raw, str(data.get("f58") or raw), price,
            source="eastmoney",
            pe=pe, pb=pb,
            mcap=safe_float(data.get("f116")),
            roe=roe / 100 if roe and abs(roe) > 1 else roe,
        )
    return None


def get_quote_tencent(code: str) -> dict | None:
    display, raw, _ = normalize_ticker(code)
    sym = _tencent_symbol(raw)
    text = _get_text(f"https://qt.gtimg.cn/q={sym}")
    if not text:
        return None
    m = re.search(r'"([^"]+)"', text.strip())
    if not m:
        return None
    parts = m.group(1).split("~")
    if len(parts) < 4:
        return None
    return _quote_dict(display, raw, parts[1], safe_float(parts[3]), source="tencent")


def get_quote_sina(code: str) -> dict | None:
    display, raw, _ = normalize_ticker(code)
    sym = _sina_symbol(raw)
    text = _get_text(
        f"https://hq.sinajs.cn/list={sym}",
        headers={"Referer": "https://finance.sina.com.cn"},
    )
    if not text:
        return None
    m = re.search(r'"([^"]*)"', text.strip())
    if not m:
        return None
    parts = m.group(1).split(",")
    if len(parts) < 4:
        return None
    price_date = None
    if len(parts) >= 31 and parts[30]:
        price_date = parts[30].strip()
    return _quote_dict(
        display, raw, parts[0], safe_float(parts[3]),
        source="sina", price_date=price_date,
    )


def get_quote_from_kline(code: str) -> dict | None:
    """Last resort: most recent daily close (may be stale after hours)."""
    display, raw, _ = normalize_ticker(code)
    df = get_kline_tencent(raw, days=5)
    if df.empty:
        return None
    last = df.iloc[-1]
    return _quote_dict(
        display, raw, raw, safe_float(last["Close"]),
        source="kline_close", stale=True,
        price_date=str(df.index[-1].date()),
    )


def get_kline_tencent(code: str, days: int = 400) -> pd.DataFrame:
    display, raw, _ = normalize_ticker(code)
    sym = _tencent_symbol(raw)
    limit = min(days + 30, 500)
    payload = _get_json(
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
        {"param": f"{sym},day,,,{limit},qfq"},
        timeout=20,
    )
    if not payload:
        return pd.DataFrame()
    stock = (payload.get("data") or {}).get(sym) or {}
    rows_raw = stock.get("qfqday") or stock.get("day") or []
    rows = []
    for item in rows_raw:
        if len(item) < 6:
            continue
        rows.append({
            "Date": item[0],
            "Open": float(item[1]),
            "Close": float(item[2]),
            "High": float(item[3]),
            "Low": float(item[4]),
            "Volume": float(item[5]),
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date").sort_index().tail(days)
