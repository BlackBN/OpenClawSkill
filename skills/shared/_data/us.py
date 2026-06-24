"""US / global fallback via yfinance (+ optional AllTick)."""

from __future__ import annotations

import pandas as pd

from . import alltick
from .market import normalize_ticker
from .utils import safe_float


def _yf():
    import yfinance as yf
    return yf


def get_quote(ticker: str) -> dict:
    display, raw, market = normalize_ticker(ticker)
    if alltick.is_configured():
        q = alltick.get_quote(display, "US")
        if q and q.get("currentPrice"):
            try:
                yf = _yf()
                info = yf.Ticker(display).info or {}
                for key in ("longName", "shortName", "trailingPE", "priceToBook", "marketCap"):
                    if info.get(key) is not None and q.get(key) is None:
                        q[key] = info.get(key)
                if info.get("longName"):
                    q["longName"] = info["longName"]
                if info.get("shortName"):
                    q["shortName"] = info["shortName"]
            except Exception:
                pass
            q.setdefault("symbol", display)
            return q

    yf = _yf()
    try:
        info = yf.Ticker(display).info or {}
    except Exception:
        info = {}
    info.setdefault("symbol", display)
    return info


def get_history(ticker: str, days: int = 400, start: str | None = None) -> pd.DataFrame:
    yf = _yf()
    t = yf.Ticker(ticker)
    if start:
        hist = t.history(start=start)
    else:
        hist = t.history(period=f"{max(days, 30)}d")
    return hist


def get_annual_financials(ticker: str, years: int = 5) -> dict:
    yf = _yf()
    display, _, market = normalize_ticker(ticker)
    t = yf.Ticker(ticker)
    info = t.info or {}
    name = info.get("longName") or info.get("shortName", display)

    try:
        fin = t.financials
        bs = t.balance_sheet
        cf = t.cashflow
    except Exception as e:
        return {"error": str(e), "ticker": display, "name": name}

    if fin is None or fin.empty:
        return {"error": "No financial data", "ticker": display, "name": name}

    def extract_row(df, row_names):
        if df is None or df.empty:
            return {}
        out = {}
        names = row_names if isinstance(row_names, list) else [row_names]
        for name_key in names:
            if name_key in df.index:
                for col in df.columns[:years]:
                    yr = str(col.year) if hasattr(col, "year") else str(col)[:4]
                    val = safe_float(df.loc[name_key, col])
                    if val is not None:
                        out[yr] = val
                break
        return out

    revenue = extract_row(fin, "Total Revenue")
    gross_profit = extract_row(fin, "Gross Profit")
    net_income = extract_row(fin, "Net Income")
    ebit = extract_row(fin, ["EBIT", "Operating Income"])
    rd = extract_row(fin, ["Research And Development", "Research Development"])
    equity = extract_row(bs, ["Total Equity Gross Minority Interest", "Stockholders Equity"])
    total_debt = extract_row(bs, "Total Debt")
    cash = extract_row(
        bs, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]
    )
    ocf = extract_row(
        cf, ["Operating Cash Flow", "Total Cash From Operating Activities"]
    )
    capex = extract_row(cf, ["Capital Expenditure", "Capital Expenditures"])

    fcf = {}
    for yr in set(ocf) | set(capex):
        o, c = ocf.get(yr), capex.get(yr)
        if o is not None and c is not None:
            fcf[yr] = o + c  # capex negative in yfinance

    return {
        "ticker": display,
        "name": name,
        "market": market,
        "info": info,
        "revenue": revenue,
        "gross_profit": gross_profit,
        "net_income": net_income,
        "ebit": ebit,
        "rd": rd,
        "equity": equity,
        "total_debt": total_debt,
        "cash": cash,
        "ocf": ocf,
        "capex": capex,
        "fcf": fcf,
    }


def screen_server_side(region="us", sector=None, max_pe=20, min_roe=15, min_mcap=1e9, top=25):
    yf = _yf()
    conditions = [yf.EquityQuery("eq", ["region", region])]
    if sector:
        conditions.append(yf.EquityQuery("eq", ["sector", sector]))
    if max_pe > 0:
        conditions.append(yf.EquityQuery("btwn", ["peratio.lasttwelvemonths", 0, max_pe]))
    if min_roe > 0:
        conditions.append(yf.EquityQuery("gt", ["returnonequity.lasttwelvemonths", min_roe / 100]))
    if min_mcap > 0:
        conditions.append(yf.EquityQuery("gt", ["intradaymarketcap", min_mcap]))
    query = yf.EquityQuery("and", conditions)
    result = yf.screen(query, sortField="intradaymarketcap", sortAsc=False, size=min(top, 250))
    return result.get("quotes", []), result.get("total", 0)


def enrich_screener_row(ticker: str) -> dict:
    info = get_quote(ticker)
    roe_raw = info.get("returnOnEquity")
    return {
        "ticker": info.get("symbol", ticker),
        "name": info.get("shortName") or info.get("longName") or ticker,
        "sector": info.get("sector") or "",
        "industry": info.get("industry") or "",
        "price": info.get("currentPrice") or info.get("regularMarketPrice") or 0,
        "pe": info.get("trailingPE") or info.get("forwardPE"),
        "forward_pe": info.get("forwardPE"),
        "ev_ebitda": info.get("enterpriseToEbitda"),
        "roe": (roe_raw or 0) * 100,
        "mcap": info.get("marketCap") or 0,
        "rev_growth": (info.get("revenueGrowth") or 0) * 100,
        "earnings_growth": (info.get("earningsGrowth") or 0) * 100,
        "momentum_52w": (info.get("52WeekChange") or 0) * 100,
        "debt_to_equity": info.get("debtToEquity"),
        "ocf": info.get("operatingCashflow") or 0,
        "net_income": info.get("netIncomeToCommon") or 0,
    }


def download_closes(tickers: list[str], days: int = 365) -> pd.DataFrame:
    yf = _yf()
    from datetime import datetime, timedelta

    end = datetime.today()
    start = end - timedelta(days=days + 30)
    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        return data["Close"]
    if len(tickers) == 1:
        return data[["Close"]].rename(columns={"Close": tickers[0]})
    return data
