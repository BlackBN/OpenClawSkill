"""Hong Kong data — multi-source quotes, akshare financials."""

from __future__ import annotations

import pandas as pd

from . import hk_em, hk_quote
from .market import map_cn_sector, normalize_ticker
from .utils import date_range, history_to_ohlcv, parse_cn_number, safe_float, year_key_from_report


def _ak():
    import akshare as ak
    return ak


def _spot_row(code: str) -> dict | None:
    q = hk_quote.get_quote(code)
    if q and q.get("currentPrice") is not None:
        return {
            "代码": code.zfill(5),
            "名称": q.get("shortName"),
            "最新价": q.get("currentPrice"),
            "市盈率": q.get("trailingPE"),
            "市净率": q.get("priceToBook"),
            "总市值": q.get("marketCap"),
            "所属行业": "",
        }
    try:
        ak = _ak()
        df = ak.stock_hk_spot_em()
        code5 = code.zfill(5)
        row = df[df["代码"].astype(str).str.zfill(5) == code5]
        if row.empty:
            row = df[df["代码"].astype(str) == code]
        if row.empty:
            return None
        return row.iloc[0].to_dict()
    except Exception:
        return None


def get_quote(code: str) -> dict:
    display, raw, _ = normalize_ticker(code)
    q = hk_quote.get_quote(raw)
    if not q:
        row = _spot_row(raw)
        if not row:
            return {"symbol": display, "shortName": raw, "longName": raw, "currency": "HKD"}
        q = {
            "symbol": display,
            "shortName": str(row.get("名称", raw)),
            "longName": str(row.get("名称", raw)),
            "currentPrice": safe_float(row.get("最新价")),
            "regularMarketPrice": safe_float(row.get("最新价")),
            "marketCap": parse_cn_number(row.get("总市值")),
            "trailingPE": safe_float(row.get("市盈率")),
            "priceToBook": safe_float(row.get("市净率")),
            "currency": "HKD",
        }

    industry = str(q.get("industry") or "")
    return {
        "symbol": display,
        "shortName": str(q.get("shortName", raw)),
        "longName": str(q.get("longName", raw)),
        "sector": map_cn_sector(industry) if industry else q.get("sector", "Unknown"),
        "industry": industry or q.get("industry", "Unknown"),
        "currentPrice": q.get("currentPrice"),
        "regularMarketPrice": q.get("regularMarketPrice"),
        "marketCap": q.get("marketCap"),
        "trailingPE": q.get("trailingPE"),
        "forwardPE": None,
        "priceToBook": q.get("priceToBook"),
        "returnOnEquity": q.get("returnOnEquity"),
        "debtToEquity": None,
        "beta": None,
        "currency": "HKD",
        "_source": q.get("_source"),
        "_sources": q.get("_sources"),
        "_stale": q.get("_stale"),
        "price_date": q.get("price_date"),
    }


def get_history(code: str, days: int = 400) -> pd.DataFrame:
    _, raw, _ = normalize_ticker(code)
    hist = hk_em.get_kline(raw, days=days)
    if not hist.empty:
        return hist
    try:
        ak = _ak()
        start, end = date_range(days)
        df = ak.stock_hk_hist(
            symbol=raw.zfill(5), period="daily", start_date=start, end_date=end, adjust="qfq"
        )
        return history_to_ohlcv(df)
    except Exception:
        return pd.DataFrame()


def get_etf_history(code: str, days: int = 400) -> pd.DataFrame:
    # HK ETF / index products: try fund_etf_hist_em with numeric code, else stock history
    raw = code.replace(".HK", "").zfill(5)
    try:
        return get_history(raw, days=days)
    except Exception:
        return pd.DataFrame()


def get_annual_financials(code: str, years: int = 5) -> dict:
    display, raw, _ = normalize_ticker(code)
    quote = get_quote(raw)
    name = quote.get("shortName", raw)
    ak = _ak()

    try:
        df = ak.stock_financial_hk_analysis_indicator_em(symbol=raw.zfill(5))
    except Exception as e:
        return {"error": f"No financial data: {e}", "ticker": display, "name": name}

    if df is None or df.empty:
        return {"error": "No financial data", "ticker": display, "name": name}

    date_col = "REPORT_DATE" if "REPORT_DATE" in df.columns else df.columns[0]

    def pick(candidates: list[str]) -> dict[str, float]:
        out = {}
        for _, row in df.iterrows():
            yr = year_key_from_report(row.get(date_col))
            if not yr:
                continue
            for col in candidates:
                if col in df.columns:
                    val = safe_float(row.get(col))
                    if val is not None:
                        out[yr] = val
                        break
        return out

    revenue = pick(["OPERATE_INCOME", "TOTAL_OPERATE_INCOME", "营业总收入"])
    net_income = pick(["HOLDER_PROFIT", "NET_PROFIT", "净利润"])
    gross_profit = pick(["GROSS_PROFIT", "毛利润"])
    equity = pick(["TOTAL_PARENT_EQUITY", "股东权益合计"])
    total_debt = pick(["TOTAL_LIABILITIES", "负债合计"])
    ocf = pick(["NETCASH_OPERATE", "经营活动产生的现金流量净额"])

    all_years = sorted(set(revenue) | set(net_income))
    if years and len(all_years) > years:
        keep = set(all_years[-years:])
        for d in (revenue, gross_profit, net_income, equity, total_debt, ocf):
            for k in list(d.keys()):
                if k not in keep:
                    del d[k]

    if total_debt:
        latest_yr = sorted(total_debt.keys())[-1]
        quote["totalDebt"] = total_debt[latest_yr]
    price = quote.get("currentPrice")
    mcap = quote.get("marketCap")
    if price and mcap:
        quote["sharesOutstanding"] = mcap / price

    return {
        "ticker": display,
        "name": name,
        "market": "HK",
        "info": quote,
        "revenue": revenue,
        "gross_profit": gross_profit,
        "net_income": net_income,
        "ebit": {},
        "rd": {},
        "equity": equity,
        "total_debt": total_debt,
        "cash": {},
        "ocf": ocf,
        "capex": {},
        "fcf": {},
    }


def screen(
    max_pe: float = 20,
    min_roe: float = 15,
    min_mcap: float = 1e9,
    sector_keyword: str | None = None,
    industry_keyword: str | None = None,
    top: int = 25,
) -> list[dict]:
    ak = _ak()
    df = ak.stock_hk_spot_em()
    rows = []
    for _, row in df.iterrows():
        code = str(row.get("代码", "")).zfill(5)
        pe = safe_float(row.get("市盈率"))
        if max_pe > 0 and (pe is None or pe <= 0 or pe > max_pe):
            continue
        mcap = parse_cn_number(row.get("总市值"))
        if min_mcap > 0 and (mcap is None or mcap < min_mcap):
            continue
        industry = str(row.get("所属行业") or "")
        if sector_keyword and sector_keyword.lower() not in industry.lower():
            continue
        if industry_keyword and industry_keyword.lower() not in industry.lower():
            continue
        display = f"{code}.HK"
        rows.append(
            {
                "symbol": display,
                "shortName": str(row.get("名称", code)),
                "marketCap": mcap,
                "trailingPE": pe,
                "regularMarketPrice": safe_float(row.get("最新价")),
                "industry": industry,
                "sector": map_cn_sector(industry),
            }
        )
    rows.sort(key=lambda x: x.get("marketCap") or 0, reverse=True)
    return rows[:top]


def enrich_screener_row(ticker: str) -> dict:
    display, code, _ = normalize_ticker(ticker)
    quote = get_quote(code)
    hist = get_history(code, days=400)
    momentum_52w = None
    if not hist.empty and len(hist) >= 60:
        start_p = hist["Close"].iloc[max(-252, -len(hist))]
        end_p = hist["Close"].iloc[-1]
        if start_p and start_p > 0:
            momentum_52w = (end_p / start_p - 1) * 100
    return {
        "ticker": display,
        "name": quote.get("shortName", display),
        "sector": quote.get("sector", ""),
        "industry": quote.get("industry", ""),
        "price": quote.get("currentPrice") or 0,
        "pe": quote.get("trailingPE"),
        "forward_pe": None,
        "ev_ebitda": None,
        "roe": (quote.get("returnOnEquity") or 0) * 100,
        "mcap": quote.get("marketCap") or 0,
        "rev_growth": 0,
        "earnings_growth": 0,
        "momentum_52w": momentum_52w or 0,
        "debt_to_equity": None,
        "ocf": 0,
        "net_income": 0,
    }
