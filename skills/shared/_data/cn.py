"""A-share data via akshare (Eastmoney / THS aggregated)."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from . import cn_em
from .market import cn_exchange_code, map_cn_sector, normalize_ticker
from .freshness import (
    build_freshness,
    compute_ttm,
    period_key_from_report,
    period_sort_key,
    sorted_period_keys,
    yoy_pct,
)
from .utils import (
    compute_beta,
    date_range,
    history_to_ohlcv,
    parse_cn_number,
    safe_float,
    throttle,
    year_key_from_report,
)


def _ak():
    import akshare as ak
    return ak


def _spot_row(code: str) -> dict | None:
    q = cn_em.get_quote(code)
    if q and q.get("currentPrice") is not None:
        return {
            "代码": code,
            "名称": q.get("shortName"),
            "最新价": q.get("currentPrice"),
            "市盈率-动态": q.get("trailingPE"),
            "市净率": q.get("priceToBook"),
            "总市值": q.get("marketCap"),
            "所属行业": "",
        }
    try:
        ak = _ak()
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == code]
        if row.empty:
            return None
        return row.iloc[0].to_dict()
    except Exception:
        return None


def get_quote(code: str) -> dict:
    display, raw, _ = normalize_ticker(code)
    q = cn_em.get_quote(raw)
    if q:
        q.setdefault("sector", "Unknown")
        q.setdefault("industry", "Unknown")
        return q

    row = _spot_row(code)
    if not row:
        return {"symbol": display, "shortName": raw, "longName": raw}
    display, _, _ = normalize_ticker(code)
    pe = safe_float(row.get("市盈率-动态"))
    pb = safe_float(row.get("市净率"))
    price = safe_float(row.get("最新价"))
    mcap = parse_cn_number(row.get("总市值"))
    industry = str(row.get("所属行业") or row.get("行业") or "")
    sector = map_cn_sector(industry)
    roe_raw = safe_float(row.get("净资产收益率"))
    if roe_raw is None:
        # spot table may not have ROE; leave None
        pass
    return {
        "symbol": display,
        "shortName": str(row.get("名称", code)),
        "longName": str(row.get("名称", code)),
        "sector": sector,
        "industry": industry or "Unknown",
        "currentPrice": price,
        "regularMarketPrice": price,
        "marketCap": mcap,
        "trailingPE": pe,
        "forwardPE": None,
        "priceToBook": pb,
        "returnOnEquity": roe_raw / 100 if roe_raw and roe_raw > 1 else roe_raw,
        "debtToEquity": None,
        "beta": None,
        "currency": "CNY",
    }


def get_history(code: str, days: int = 400) -> pd.DataFrame:
    _, raw, _ = normalize_ticker(code)
    hist = cn_em.get_kline(raw, days=days)
    if not hist.empty:
        return hist
    try:
        ak = _ak()
        start, end = date_range(days)
        df = ak.stock_zh_a_hist(
            symbol=raw, period="daily", start_date=start, end_date=end, adjust="qfq"
        )
        return history_to_ohlcv(df)
    except Exception:
        return pd.DataFrame()


def get_etf_history(code: str, days: int = 400) -> pd.DataFrame:
    etf_code = code.replace(".SS", "").replace(".SZ", "")
    try:
        ak = _ak()
        start, end = date_range(days)
        df = ak.fund_etf_hist_em(
            symbol=etf_code, period="daily", start_date=start, end_date=end, adjust="qfq"
        )
        hist = history_to_ohlcv(df)
        if not hist.empty:
            return hist
    except Exception:
        pass
    return cn_em.get_etf_kline(etf_code, days=days)


def _annual_abstract(code: str) -> pd.DataFrame:
    ak = _ak()
    try:
        return ak.stock_financial_abstract_ths(symbol=code, indicator="按年度")
    except Exception:
        return pd.DataFrame()


def _report_table(code: str, fn_name: str, indicator: str = "按年度") -> pd.DataFrame:
    ak = _ak()
    fn = getattr(ak, fn_name, None)
    if fn is None:
        return pd.DataFrame()
    try:
        return fn(symbol=code, indicator=indicator)
    except Exception:
        if indicator != "按报告期":
            try:
                return fn(symbol=code, indicator="按报告期")
            except Exception:
                return pd.DataFrame()
        return pd.DataFrame()


def _pick_series(df: pd.DataFrame, candidates: list[str], *, quarterly: bool = False) -> dict[str, float]:
    if df is None or df.empty:
        return {}
    out: dict[str, float] = {}
    date_col = "报告期" if "报告期" in df.columns else df.columns[0]
    for _, row in df.iterrows():
        raw_date = row.get(date_col)
        if quarterly:
            pk = period_key_from_report(raw_date)
        else:
            yr = year_key_from_report(raw_date)
            pk = yr
        if not pk:
            continue
        for col in candidates:
            if col in df.columns:
                val = parse_cn_number(row.get(col))
                if val is not None:
                    out[pk] = val
                    break
    return out


def _latest_abstract_row(abstract: pd.DataFrame) -> pd.Series | None:
    if abstract is None or abstract.empty:
        return None
    date_col = "报告期" if "报告期" in abstract.columns else abstract.columns[0]
    tmp = abstract.copy()
    tmp["_sort"] = tmp[date_col].apply(lambda x: period_sort_key(period_key_from_report(x) or "0000A"))
    return tmp.sort_values("_sort", ascending=False).iloc[0]


def _build_ttm_block(quarterly: dict[str, dict[str, float]]) -> dict:
    """Build TTM metrics + YoY from quarterly dicts."""
    rev_q = quarterly.get("revenue", {})
    ni_q = quarterly.get("net_income", {})
    gp_q = quarterly.get("gross_profit", {})

    rev_ttm = compute_ttm(rev_q)
    ni_ttm = compute_ttm(ni_q)
    gp_ttm = compute_ttm(gp_q)

    if not rev_ttm:
        return {}

    as_of = rev_ttm["as_of_period"]

    def prior_ttm(series: dict[str, float]) -> float | None:
        keys = sorted_period_keys([k for k in series if "Q" in k])
        if as_of not in keys:
            return None
        idx = keys.index(as_of)
        if idx < 7:
            return None
        window = keys[idx - 7 : idx - 3]
        return sum(series.get(k, 0) or 0 for k in window)

    rev_prior = prior_ttm(rev_q)
    ni_prior = prior_ttm(ni_q)

    return {
        "as_of_period": as_of,
        "revenue": rev_ttm["value"],
        "net_income": ni_ttm["value"] if ni_ttm else None,
        "gross_profit": gp_ttm["value"] if gp_ttm else None,
        "revenue_as_of": as_of,
        "revenue_yoy_pct": yoy_pct(rev_ttm["value"], rev_prior),
        "net_income_yoy_pct": yoy_pct(ni_ttm["value"] if ni_ttm else None, ni_prior),
    }


def get_annual_financials(code: str, years: int = 5) -> dict:
    display, raw, _ = normalize_ticker(code)
    quote = get_quote(raw)
    name = quote.get("shortName", raw)
    warnings: list[str] = []
    if not name or name == raw:
        q = cn_em.get_quote(raw)
        if q:
            name = q.get("shortName", name)
            quote.update(q)
    if quote.get("currentPrice") is None:
        warnings.append("实时股价/PE 未获取到，可能为 API 限流或网络问题")

    abstract = _annual_abstract(raw)
    benefit = _report_table(raw, "stock_financial_benefit_ths")
    debt = _report_table(raw, "stock_financial_debt_ths")
    cashflow = _report_table(raw, "stock_financial_cash_ths")

    # Quarterly tables (TTM)
    q_benefit = _report_table(raw, "stock_financial_benefit_ths", indicator="按单季度")
    if q_benefit.empty:
        q_benefit = _report_table(raw, "stock_financial_benefit_ths", indicator="按报告期")
    q_cash = _report_table(raw, "stock_financial_cash_ths", indicator="按单季度")
    if q_cash.empty:
        q_cash = _report_table(raw, "stock_financial_cash_ths", indicator="按报告期")

    if abstract.empty and benefit.empty:
        return {"error": "No financial data", "ticker": display, "name": name}

    revenue = _pick_series(abstract, ["营业总收入", "营业收入"]) or _pick_series(
        benefit, ["营业总收入", "营业收入"]
    )
    gross_profit = _pick_series(benefit, ["毛利润", "营业毛利"])
    if not gross_profit and revenue:
        gm_pct = _pick_series(abstract, ["销售毛利率", "毛利率"])
        gross_profit = {}
        for yr, pct in gm_pct.items():
            if yr in revenue and pct is not None:
                ratio = pct / 100 if abs(pct) > 1 else pct
                gross_profit[yr] = revenue[yr] * ratio
    net_income = _pick_series(abstract, ["净利润", "归属于母公司所有者的净利润"]) or _pick_series(
        benefit, ["净利润", "归属于母公司所有者的净利润"]
    )
    ebit = _pick_series(benefit, ["营业利润", "营业总成本"])
    rd = _pick_series(benefit, ["研发费用", "研发支出"])
    equity = _pick_series(debt, ["所有者权益合计", "股东权益合计", "归属于母公司股东权益合计"])
    total_debt = _pick_series(debt, ["负债合计", "总负债"])
    cash_eq = _pick_series(debt, ["货币资金"])
    ocf = _pick_series(cashflow, ["经营活动产生的现金流量净额", "经营活动现金流量净额"])
    capex = _pick_series(cashflow, ["购建固定资产、无形资产和其他长期资产支付的现金", "资本开支"])

    quarterly = {
        "revenue": _pick_series(q_benefit, ["营业总收入", "营业收入"], quarterly=True),
        "net_income": _pick_series(q_benefit, ["净利润", "归属于母公司所有者的净利润"], quarterly=True),
        "gross_profit": _pick_series(q_benefit, ["毛利润", "营业毛利"], quarterly=True),
        "ocf": _pick_series(q_cash, ["经营活动产生的现金流量净额", "经营活动现金流量净额"], quarterly=True),
    }
    ttm = _build_ttm_block(quarterly)

    # Trim to latest N years
    all_years = sorted(set(revenue) | set(net_income))
    if years and len(all_years) > years:
        keep = set(all_years[-years:])
        for d in (revenue, gross_profit, net_income, ebit, rd, equity, total_debt, cash_eq, ocf, capex):
            for k in list(d.keys()):
                if k not in keep:
                    del d[k]

    latest_row = _latest_abstract_row(abstract)
    if latest_row is not None:
        roe = parse_cn_number(latest_row.get("净资产收益率"))
        if roe is not None:
            quote["returnOnEquity"] = roe / 100 if abs(roe) > 1 else roe
        gm = parse_cn_number(latest_row.get("销售毛利率"))
        if gm is not None:
            quote["grossMargins"] = gm / 100 if gm > 1 else gm

    latest_yr = all_years[-1] if all_years else None
    if latest_yr and latest_yr in total_debt:
        quote["totalDebt"] = total_debt[latest_yr]
    if latest_yr and latest_yr in cash_eq:
        quote["totalCash"] = cash_eq[latest_yr]

    price = quote.get("currentPrice")
    mcap = quote.get("marketCap")
    if price and mcap:
        quote["sharesOutstanding"] = mcap / price

    fcf_by_year = {}
    for yr in set(ocf) | set(capex):
        o = ocf.get(yr)
        c = capex.get(yr)
        if o is not None and c is not None:
            fcf_by_year[yr] = o - abs(c)

    q_periods = sorted_period_keys(
        list(set(quarterly["revenue"]) | set(quarterly["net_income"]))
    )
    freshness = build_freshness(
        quote=quote,
        hist=None,
        annual_periods=all_years,
        quarterly_periods=q_periods,
        ttm=ttm,
        warnings=warnings,
    )

    return {
        "ticker": display,
        "name": name,
        "market": "CN",
        "info": quote,
        "revenue": revenue,
        "gross_profit": gross_profit,
        "net_income": net_income,
        "ebit": ebit,
        "rd": rd,
        "equity": equity,
        "total_debt": total_debt,
        "cash": cash_eq,
        "ocf": ocf,
        "capex": capex,
        "fcf": fcf_by_year,
        "quarterly": quarterly,
        "ttm": ttm,
        "freshness": freshness,
    }


def is_st_stock(name: str) -> bool:
    """Exclude ST / *ST / 退 from universe (A-share risk control)."""
    if not name:
        return False
    n = str(name).upper()
    return "ST" in n or "退" in n


def get_index_constituents(index: str) -> list[str]:
    """Fetch index constituents and return normalized tickers."""
    mapping = {
        "csi300": "000300",
        "hs300": "000300",
        "zz500": "000905",
        "csi500": "000905",
        "zz1000": "000852",
    }
    symbol = mapping.get(index.lower(), index)
    try:
        ak = _ak()
        df = ak.index_stock_cons_csindex(symbol=symbol)
        codes = df["成分券代码"].astype(str).str.zfill(6).tolist()
        return [normalize_ticker(c)[0] for c in codes]
    except Exception:
        return []


def _spot_fields(row: dict) -> dict:
    """Normalize Eastmoney spot row fields."""
    name = str(row.get("名称", ""))
    industry = str(row.get("所属行业") or row.get("行业") or "")
    return {
        "name": name,
        "industry": industry,
        "pe": safe_float(row.get("市盈率-动态")),
        "pb": safe_float(row.get("市净率")),
        "price": safe_float(row.get("最新价")),
        "mcap": parse_cn_number(row.get("总市值")),
        "turnover_pct": safe_float(row.get("换手率")),
        "volume_ratio": safe_float(row.get("量比")),
        "momentum_pct": safe_float(row.get("60日涨跌幅") or row.get("年初至今涨跌幅")),
    }


def screen(
    max_pe: float = 20,
    min_roe: float = 15,
    min_mcap: float = 1e9,
    sector_keyword: str | None = None,
    industry_keyword: str | None = None,
    top: int = 25,
) -> list[dict]:
    try:
        ak = _ak()
        df = ak.stock_zh_a_spot_em()
    except Exception:
        # Minimal fallback: cannot full-scan without akshare; return empty
        print("[data] CN full-market scan unavailable; use --tickers mode", file=__import__("sys").stderr)
        return []
    rows = []
    for _, row in df.iterrows():
        code = str(row.get("代码", ""))
        if not code:
            continue
        fields = _spot_fields(row.to_dict())
        if is_st_stock(fields["name"]):
            continue
        pe = fields["pe"]
        if max_pe > 0 and (pe is None or pe <= 0 or pe > max_pe):
            continue
        mcap = fields["mcap"]
        if min_mcap > 0 and (mcap is None or mcap < min_mcap):
            continue
        industry = fields["industry"]
        if sector_keyword and sector_keyword.lower() not in industry.lower():
            if sector_keyword.lower() not in map_cn_sector(industry).lower():
                continue
        if industry_keyword and industry_keyword.lower() not in industry.lower():
            continue
        display, _, _ = normalize_ticker(code)
        rows.append(
            {
                "symbol": display,
                "shortName": fields["name"] or code,
                "marketCap": mcap,
                "trailingPE": pe,
                "priceToBook": fields["pb"],
                "regularMarketPrice": fields["price"],
                "industry": industry,
                "sector": map_cn_sector(industry),
                "turnover_pct": fields["turnover_pct"],
            }
        )
    rows.sort(key=lambda x: x.get("marketCap") or 0, reverse=True)
    return rows[:top]


def enrich_screener_row(ticker: str) -> dict:
    display, code, _ = normalize_ticker(ticker)
    quote = get_quote(code)
    hist = get_history(code, days=400)
    momentum_52w = None
    price_date = None
    if not hist.empty and len(hist) >= 60:
        start_p = hist["Close"].iloc[max(-252, -len(hist))]
        end_p = hist["Close"].iloc[-1]
        price_date = hist.index[-1].strftime("%Y-%m-%d")
        if start_p and start_p > 0:
            momentum_52w = (end_p / start_p - 1) * 100

    fin = get_annual_financials(code, years=3)
    rev = fin.get("revenue", {})
    ni = fin.get("net_income", {})
    years = sorted(rev.keys())

    # Prefer TTM YoY; fallback to latest annual YoY
    ttm = fin.get("ttm") or {}
    rev_growth = ttm.get("revenue_yoy_pct")
    earnings_growth = ttm.get("net_income_yoy_pct")
    if rev_growth is None and len(years) >= 2 and rev.get(years[-2]):
        rev_growth = yoy_pct(rev.get(years[-1]), rev.get(years[-2]))
    if earnings_growth is None and len(years) >= 2:
        earnings_growth = yoy_pct(ni.get(years[-1]), ni.get(years[-2]))

    roe = quote.get("returnOnEquity")
    if roe is not None and abs(roe) <= 1:
        roe = roe * 100

    latest_yr = years[-1] if years else None
    ocf_vals = fin.get("ocf", {})
    ni_vals = fin.get("net_income", {})
    ocf = ocf_vals.get(latest_yr) if latest_yr else None
    net_income = ni_vals.get(latest_yr) if latest_yr else None
    if ocf is None:
        ocf = 0
    if net_income is None:
        net_income = 0
    cf_quality = (ocf / net_income) if net_income and net_income > 0 else None

    if fin.get("freshness") and price_date:
        fin["freshness"]["price_date"] = price_date

    return {
        "ticker": display,
        "name": quote.get("shortName", display),
        "sector": quote.get("sector", ""),
        "industry": quote.get("industry", ""),
        "price": quote.get("currentPrice") or 0,
        "pe": quote.get("trailingPE"),
        "pb": quote.get("priceToBook"),
        "forward_pe": None,
        "ev_ebitda": None,
        "roe": roe or 0,
        "mcap": quote.get("marketCap") or 0,
        "rev_growth": rev_growth or 0,
        "earnings_growth": earnings_growth or 0,
        "momentum_52w": momentum_52w or quote.get("momentum_pct") or 0,
        "turnover_pct": quote.get("turnover_pct") or 0,
        "debt_to_equity": None,
        "ocf": ocf,
        "net_income": net_income,
        "cf_quality": cf_quality,
        "is_st": is_st_stock(quote.get("shortName", "")),
        "data_freshness": fin.get("freshness"),
        "price_date": price_date,
    }
