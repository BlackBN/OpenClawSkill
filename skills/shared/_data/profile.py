"""Business profile data — main business text, segment mix, shareholders."""

from __future__ import annotations

from .market import detect_market, normalize_ticker
from .provider import get_annual_financials, get_info
from .utils import safe_float


def _ak():
    import akshare as ak
    return ak


def _em_symbol(display: str, raw: str, market: str) -> str:
    if market == "CN":
        return f"{'SH' if raw.startswith(('6', '9')) else 'SZ'}{raw}"
    return raw


def get_main_business_text(code: str) -> dict:
    """THS main business summary (CN)."""
    display, raw, market = normalize_ticker(code)
    if market != "CN":
        return {}
    try:
        ak = _ak()
        df = ak.stock_zyjs_ths(symbol=raw)
        if df is None or df.empty:
            return {}
        row = df.iloc[0]
        return {
            "main_business": str(row.get("主营业务") or ""),
            "product_type": str(row.get("产品类型") or ""),
            "product_names": str(row.get("产品名称") or ""),
            "business_scope": str(row.get("经营范围") or ""),
        }
    except Exception:
        return {}


def get_segment_mix(code: str) -> dict:
    """Eastmoney segment breakdown by product / industry / region (CN)."""
    display, raw, market = normalize_ticker(code)
    if market != "CN":
        return {}
    try:
        ak = _ak()
        df = ak.stock_zygc_em(symbol=_em_symbol(display, raw, market))
        if df is None or df.empty:
            return {}
        df = df.copy()
        df["报告日期"] = df["报告日期"].astype(str)
        latest = df["报告日期"].max()
        out: dict = {"report_date": latest, "by_product": [], "by_industry": [], "by_region": []}
        mapping = {
            "按产品分类": "by_product",
            "按行业分类": "by_industry",
            "按地区分类": "by_region",
        }
        sub = df[df["报告日期"] == latest]
        for cn_label, key in mapping.items():
            part = sub[sub["分类类型"] == cn_label].copy()
            if part.empty:
                continue
            part = part.sort_values("收入比例", ascending=False)
            rows = []
            for _, r in part.iterrows():
                rev = safe_float(r.get("主营收入"))
                share = safe_float(r.get("收入比例"))
                gm = safe_float(r.get("毛利率"))
                rows.append({
                    "name": str(r.get("主营构成") or ""),
                    "revenue": rev,
                    "revenue_yi": round(rev / 1e8, 2) if rev else None,
                    "revenue_share_pct": round(share * 100, 2) if share and share <= 1 else share,
                    "gross_margin_pct": round(gm * 100, 2) if gm and abs(gm) <= 1 else gm,
                })
            out[key] = rows
        return out
    except Exception:
        return {}


def get_top_shareholders(code: str, top: int = 5) -> list[dict]:
    display, raw, market = normalize_ticker(code)
    if market != "CN":
        return []
    try:
        ak = _ak()
        df = ak.stock_main_stock_holder(stock=raw)
        if df is None or df.empty:
            return []
        rows = []
        for _, r in df.head(top).iterrows():
            rows.append({
                "name": str(r.get("股东名称") or ""),
                "shares": safe_float(r.get("持股数量")),
                "pct": safe_float(r.get("持股比例")),
                "nature": str(r.get("股本性质") or ""),
                "as_of": str(r.get("截至日期") or ""),
            })
        return rows
    except Exception:
        return []


def _revenue_cagr(revenue: dict) -> float | None:
    years = sorted(revenue.keys())
    if len(years) < 2:
        return None
    first, last = revenue[years[0]], revenue[years[-1]]
    n = len(years) - 1
    if not first or not last or first <= 0:
        return None
    try:
        return round((abs(last / first) ** (1 / n) - 1) * 100 * (1 if last >= first else -1), 2)
    except Exception:
        return None


def get_business_profile(code: str, years: int = 5) -> dict:
    """Structured business profile facts for agent narrative layer."""
    display, raw, market = normalize_ticker(code)
    info = get_info(display)
    fin = get_annual_financials(raw, years=years)
    name = fin.get("name") or info.get("shortName") or raw

    if fin.get("error") and not info.get("currentPrice"):
        return {"error": fin.get("error", "No data"), "ticker": display, "name": name}

    revenue = fin.get("revenue") or {}
    gross_profit = fin.get("gross_profit") or {}
    net_income = fin.get("net_income") or {}
    sorted_years = sorted(revenue.keys())
    annual = {}
    for yr in sorted_years:
        rev = revenue.get(yr)
        gp = gross_profit.get(yr)
        ni = net_income.get(yr)
        gm = round(gp / rev * 100, 2) if gp and rev else None
        nm = round(ni / rev * 100, 2) if ni and rev else None
        annual[yr] = {
            "revenue_yi": round(rev / 1e8, 2) if rev else None,
            "gross_margin_pct": gm,
            "net_margin_pct": nm,
            "net_income_yi": round(ni / 1e8, 2) if ni else None,
        }

    ttm = fin.get("ttm") or {}
    main = get_main_business_text(raw)
    segments = get_segment_mix(raw)
    holders = get_top_shareholders(raw)

    industry = info.get("industry") or "Unknown"
    if industry in ("Unknown", "", None) and main.get("main_business"):
        industry = _infer_industry(main.get("main_business", ""))

    return {
        "ticker": display,
        "name": name,
        "market": market,
        "industry": industry,
        "sector": info.get("sector") or "Unknown",
        "snapshot": {
            "price": info.get("currentPrice"),
            "pe_trailing": info.get("trailingPE"),
            "pb": info.get("priceToBook"),
            "market_cap_yi": round(info["marketCap"] / 1e8, 2) if info.get("marketCap") else None,
            "currency": info.get("currency") or ("CNY" if market == "CN" else "HKD" if market == "HK" else "USD"),
            "_quote_sources": info.get("_sources") or info.get("_source"),
        },
        "main_business": main,
        "segments": segments,
        "shareholders": holders,
        "financial_highlights": {
            "annual": annual,
            "revenue_cagr_pct": _revenue_cagr(revenue),
            "ttm": {
                "period": ttm.get("as_of_period"),
                "revenue_yi": round(ttm["revenue"] / 1e8, 2) if ttm.get("revenue") else None,
                "net_income_yi": round(ttm["net_income"] / 1e8, 2) if ttm.get("net_income") else None,
                "revenue_yoy_pct": ttm.get("revenue_yoy_pct"),
            } if ttm else {},
        },
        "freshness": fin.get("freshness") or {},
        "warnings": fin.get("freshness", {}).get("warnings") or [],
    }


def _infer_industry(text: str) -> str:
    keywords = {
        "PCB": "印制电路板",
        "半导体": "半导体",
        "芯片": "半导体",
        "银行": "银行",
        "保险": "保险",
        "医药": "医药生物",
        "白酒": "白酒",
        "新能源": "新能源",
        "锂": "有色金属",
        "锆": "有色金属",
    }
    for key, ind in keywords.items():
        if key in text:
            return ind
    return "Unknown"
