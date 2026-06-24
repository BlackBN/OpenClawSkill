"""Market detection and configuration for CN / HK / US tickers."""

from __future__ import annotations

MARKET_CONFIGS = {
    "US": {"tax_rate": 0.21, "risk_free_rate": 0.045, "currency": "USD", "label": "United States"},
    "HK": {"tax_rate": 0.165, "risk_free_rate": 0.04, "currency": "HKD", "label": "Hong Kong"},
    "CN": {"tax_rate": 0.25, "risk_free_rate": 0.02, "currency": "CNY", "label": "China A-share"},
    "JP": {"tax_rate": 0.30, "risk_free_rate": 0.01, "currency": "JPY", "label": "Japan"},
    "UK": {"tax_rate": 0.25, "risk_free_rate": 0.04, "currency": "GBP", "label": "United Kingdom"},
}

BENCHMARKS = {
    "US": "SPY",
    "HK": "2800.HK",
    "CN": "510300.SS",
    "JP": "1306.T",
    "UK": "ISF.L",
}

# Map Eastmoney / akshare industry keywords → valuation-matrix sector keys
CN_INDUSTRY_TO_SECTOR = {
    "银行": "Financial Services",
    "保险": "Financial Services",
    "证券": "Financial Services",
    "半导体": "Technology",
    "软件": "Technology",
    "互联网": "Communication Services",
    "通信": "Communication Services",
    "医药": "Healthcare",
    "医疗": "Healthcare",
    "生物": "Healthcare",
    "白酒": "Consumer Defensive",
    "食品": "Consumer Defensive",
    "饮料": "Consumer Defensive",
    "家电": "Consumer Cyclical",
    "汽车": "Consumer Cyclical",
    "零售": "Consumer Cyclical",
    "房地产": "Real Estate",
    "地产": "Real Estate",
    "钢铁": "Basic Materials",
    "有色": "Basic Materials",
    "化工": "Basic Materials",
    "煤炭": "Energy",
    "石油": "Energy",
    "电力": "Utilities",
    "公用": "Utilities",
    "机械": "Industrials",
    "军工": "Industrials",
    "建筑": "Industrials",
    "运输": "Industrials",
}


def detect_market(ticker: str) -> str:
    t = ticker.upper().strip()
    if t.endswith(".HK"):
        return "HK"
    if t.endswith(".SS") or t.endswith(".SZ"):
        return "CN"
    if t.endswith(".T"):
        return "JP"
    if t.endswith(".L"):
        return "UK"
    if t.endswith(".DE"):
        return "DE"
    if t.endswith(".PA"):
        return "FR"
    if t.endswith(".AS"):
        return "NL"
    # Bare 6-digit code → A-share
    core = t.split(".")[0]
    if core.isdigit() and len(core) == 6:
        return "CN"
    # Bare 4-5 digit → HK
    if core.isdigit() and 1 <= len(core) <= 5:
        return "HK"
    return "US"


def get_tax_rate(market: str) -> float:
    return MARKET_CONFIGS.get(market, MARKET_CONFIGS["US"])["tax_rate"]


def get_market_config(market: str) -> dict:
    return MARKET_CONFIGS.get(market, MARKET_CONFIGS["US"])


def get_benchmark(market: str) -> str:
    return BENCHMARKS.get(market, "SPY")


def normalize_ticker(ticker: str) -> tuple[str, str, str]:
    """Return (display_ticker, raw_code, market)."""
    t = ticker.upper().strip()
    market = detect_market(t)
    if market == "CN":
        code = t.replace(".SS", "").replace(".SZ", "").replace("SH", "").replace("SZ", "")
        code = "".join(c for c in code if c.isdigit())
        code = code.zfill(6)
        suffix = ".SS" if code.startswith(("6", "9")) else ".SZ"
        return f"{code}{suffix}", code, market
    if market == "HK":
        code = t.replace(".HK", "")
        code = "".join(c for c in code if c.isdigit())
        code = code.zfill(5)
        return f"{code}.HK", code, market
    return t, t, market


def cn_exchange_code(code: str) -> str:
    """Eastmoney secid market prefix: 0=SZ, 1=SH."""
    return "1" if code.startswith(("6", "9")) else "0"


def hk_secid(code: str) -> str:
    """Eastmoney secid for HK stocks: 116.{5-digit code}."""
    return f"116.{code.zfill(5)}"


def to_alltick_code(display: str, raw: str, market: str) -> str | None:
    """AllTick symbol format — see https://alltick.co code list."""
    if market == "CN":
        suffix = "SH" if raw.startswith(("6", "9")) else "SZ"
        return f"{raw}.{suffix}"
    if market == "HK":
        return f"{int(raw)}.HK"
    if market == "US":
        sym = display.split(".")[0].upper()
        return f"{sym}.US"
    return None


def map_cn_sector(industry: str | None) -> str:
    if not industry:
        return "Unknown"
    for key, sector in CN_INDUSTRY_TO_SECTOR.items():
        if key in industry:
            return sector
    return "Unknown"
