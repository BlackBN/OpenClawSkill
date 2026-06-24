#!/usr/bin/env python3
"""
sector-radar: Sector/industry momentum scanner.

Accepts any ETF tickers + an optional benchmark. Computes multi-period
momentum, momentum acceleration, relative strength vs benchmark, relative
valuation rank, and volume trend.

Data sources:
  A-share / HK → akshare (Eastmoney)
  US / others → yfinance (fallback)

Usage:
    python3 scripts/fetch_data.py 512480 512400 159928 515030 --benchmark 510300
    python3 scripts/fetch_data.py 3067.HK 3033.HK 2800.HK --benchmark 2800.HK
    python3 scripts/fetch_data.py XLK XLF XLE --benchmark SPY
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2]
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from _data.provider import detect_market, get_etf_history, get_history, get_info  # noqa: E402

MOMENTUM_WINDOWS = [
    (63, 0.35, "3M"),
    (126, 0.35, "6M"),
    (252, 0.30, "12M"),
]


def get_return(hist, days: int) -> float | None:
    try:
        if hist.empty or "Close" not in hist.columns:
            return None
        if len(hist) < days + 1:
            days = len(hist) - 1
        if days <= 0:
            return None
        end_price = hist["Close"].iloc[-1]
        start_price = hist["Close"].iloc[-(days + 1)]
        return round((end_price / start_price - 1) * 100, 2)
    except Exception:
        return None


def momentum_score(returns: dict) -> float:
    scores = []
    weights = []
    for days, weight, _ in MOMENTUM_WINDOWS:
        ret = returns.get(days)
        if ret is not None:
            normalized = max(0.0, min(1.0, (ret + 30) / 60))
            scores.append(normalized * weight)
            weights.append(weight)
    if not weights:
        return 50.0
    return round(sum(scores) / sum(weights) * 100, 1)


def momentum_acceleration(r3m: float | None, r6m: float | None) -> float | None:
    if r3m is None or r6m is None:
        return None
    ann_3m = r3m * 4
    ann_6m = r6m * 2
    return round(ann_3m - ann_6m, 1)


def relative_strength(sector_return: float | None, bench_return: float | None) -> float | None:
    if sector_return is None or bench_return is None:
        return None
    return round(sector_return - bench_return, 2)


def volume_trend(hist, short=20, long=60) -> float | None:
    try:
        if hist.empty or "Volume" not in hist.columns:
            return None
        vol = hist["Volume"]
        if len(vol) < long:
            return None
        short_avg = vol.iloc[-short:].mean()
        long_avg = vol.iloc[-long:].mean()
        if long_avg == 0:
            return None
        return round(short_avg / long_avg, 2)
    except Exception:
        return None


def rank_score(values: list[float | None]) -> list[float]:
    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    n = len(values)
    scores = [50.0] * n
    if not valid:
        return scores
    sorted_vals = sorted(valid, key=lambda x: x[1])
    for rank, (idx, _) in enumerate(sorted_vals):
        scores[idx] = round(rank / max(len(valid) - 1, 1) * 100, 1)
    return scores


def fetch_symbol_history(sym: str, days: int = 400):
    market = detect_market(sym)
    if market == "CN":
        return get_etf_history(sym, days=days)
    return get_history(sym, days=days)


def fetch_benchmark(ticker: str) -> dict:
    try:
        hist = fetch_symbol_history(ticker)
        returns = {}
        for days, _, _ in MOMENTUM_WINDOWS:
            returns[days] = get_return(hist, days)
        returns[21] = get_return(hist, 21)
        return returns
    except Exception:
        return {}


def main():
    parser = argparse.ArgumentParser(description="Sector/industry momentum scanner")
    parser.add_argument("etfs", nargs="+", help="ETF/index tickers to scan")
    parser.add_argument("--benchmark", default=None, help="Benchmark (510300, 2800.HK, SPY)")
    parser.add_argument("--labels", nargs="*", default=None, help="Sector labels matching etfs order")
    args = parser.parse_args()

    etfs = [e.upper() for e in args.etfs]
    labels = args.labels or [None] * len(etfs)
    if len(labels) < len(etfs):
        labels.extend([None] * (len(etfs) - len(labels)))

    today = datetime.now()
    bench_returns = {}
    if args.benchmark:
        bench_returns = fetch_benchmark(args.benchmark.upper())

    results = []
    for sym, label in zip(etfs, labels):
        try:
            hist = fetch_symbol_history(sym)
            info = get_info(sym)
            sector_name = label or info.get("shortName") or info.get("longName") or sym

            returns = {}
            for days, _, _ in MOMENTUM_WINDOWS:
                returns[days] = get_return(hist, days)
            r1m = get_return(hist, 21)

            score = momentum_score(returns)
            pe = info.get("trailingPE")
            div_yield = info.get("yield") or info.get("dividendYield")
            vol_trend_val = volume_trend(hist)
            accel = momentum_acceleration(returns.get(63), returns.get(126))
            rs_6m = relative_strength(returns.get(126), bench_returns.get(126))

            price_date = None
            if hist is not None and not hist.empty:
                try:
                    price_date = hist.index[-1].strftime("%Y-%m-%d")
                except Exception:
                    pass

            results.append({
                "etf": sym,
                "sector": sector_name,
                "price_date": price_date,
                "r1m": r1m,
                "r3m": returns.get(63),
                "r6m": returns.get(126),
                "r12m": returns.get(252),
                "pe": round(pe, 1) if pe else None,
                "div_yield": round(div_yield * 100, 2) if div_yield else None,
                "vol_trend": vol_trend_val,
                "accel": accel,
                "rs_6m": rs_6m,
                "momentum": score,
            })
        except Exception as e:
            print(f"WARN: Failed {sym}: {e}", file=sys.stderr)

    if not results:
        print("ERROR: No data retrieved for any ticker.")
        sys.exit(1)

    pes = [r["pe"] for r in results]
    pe_ranks = rank_score(pes)
    pe_val_scores = [round(100 - s, 1) for s in pe_ranks]
    for r, vs in zip(results, pe_val_scores):
        r["val_rank"] = vs

    accels = [r["accel"] for r in results]
    accel_scores = rank_score(accels)
    for r, as_ in zip(results, accel_scores):
        r["accel_score"] = as_

    vol_trends = [r["vol_trend"] for r in results]
    vol_scores = rank_score(vol_trends)
    for r, vs in zip(results, vol_scores):
        composite = (r["momentum"] * 0.50 + r["accel_score"] * 0.15 +
                     r["val_rank"] * 0.20 + vs * 0.15)
        r["score"] = round(composite, 1)

    results.sort(key=lambda x: x["score"], reverse=True)

    bench_label = f" (vs {args.benchmark.upper()})" if args.benchmark else ""
    print(f"# Sector Radar Report{bench_label}", flush=True)
    print(f"\n_Generated: {today.strftime('%Y-%m-%d %H:%M')}_\n")
    print("_Scoring: Momentum 50% + Acceleration 15% + Valuation 20% + Volume 15%_\n")
    print("_Data: A-share/HK via akshare · US via yfinance_\n")
    latest_dates = sorted({r["price_date"] for r in results if r.get("price_date")})
    if latest_dates:
        print(f"_K线截至: {latest_dates[-1]}_\n")

    has_rs = any(r["rs_6m"] is not None for r in results)
    rs_header = " RS 6M |" if has_rs else ""
    rs_sep = "-------|" if has_rs else ""

    print("## Sector Rankings\n")
    print(f"| # | ETF | Sector | 3M% | 6M% | 12M% | Accel | P/E |{rs_header} Vol | Score |")
    print(f"|---|-----|--------|-----|-----|------|-------|-----|{rs_sep}-----|-------|")

    fmt = lambda v: f"{v:+.1f}%" if v is not None else "N/A"
    for i, r in enumerate(results, 1):
        pe_str = str(r["pe"]) if r["pe"] else "N/A"
        accel_str = f"{r['accel']:+.1f}" if r["accel"] is not None else "N/A"
        vol_str = f"{r['vol_trend']:.2f}" if r["vol_trend"] else "N/A"
        rs_col = f" {fmt(r['rs_6m'])} |" if has_rs else ""
        print(f"| {i} | **{r['etf']}** | {r['sector']} | {fmt(r['r3m'])} | {fmt(r['r6m'])} | {fmt(r['r12m'])} | {accel_str} | {pe_str} |{rs_col} {vol_str} | {r['score']} |")

    n = len(results)
    top_third = results[:max(n // 3, 1)]
    bottom_third = results[max(n - n // 3, n - 1):]

    print("\n## Momentum Leaders\n")
    for r in top_third:
        print(f"- **{r['etf']}** ({r['sector']}): Score {r['score']}, Momentum {r['momentum']}")

    print("\n## Momentum Laggards\n")
    for r in bottom_third:
        print(f"- **{r['etf']}** ({r['sector']}): Score {r['score']}, Momentum {r['momentum']}")

    has_accel = any(r["accel"] is not None for r in results)
    if has_accel:
        mid_mom = sorted(r["momentum"] for r in results)[n // 2]
        print("\n## Momentum × Trend Quality Quadrant\n")
        q1, q2, q3, q4 = [], [], [], []
        for r in results:
            if r["accel"] is None:
                continue
            high_mom = r["momentum"] >= mid_mom
            accel_pos = r["accel"] > 0
            if high_mom and accel_pos:
                q1.append(r)
            elif high_mom and not accel_pos:
                q2.append(r)
            elif not high_mom and accel_pos:
                q3.append(r)
            else:
                q4.append(r)
        if q1:
            print(f"**Strong + accelerating:** {', '.join(r['etf'] for r in q1)}")
        if q2:
            print(f"**Strong + decelerating:** {', '.join(r['etf'] for r in q2)}")
        if q3:
            print(f"**Weak + accelerating:** {', '.join(r['etf'] for r in q3)}")
        if q4:
            print(f"**Weak + decelerating:** {', '.join(r['etf'] for r in q4)}")

    print("\n---\n_CSV data written to stderr_", file=sys.stdout)
    header = "etf,sector,r3m,r6m,r12m,accel,pe,div_yield,vol_trend,rs_6m,momentum,val_rank,accel_score,score"
    print(header, file=sys.stderr)
    for r in results:
        vals = [
            r["etf"], f'"{r["sector"]}"', str(r["r3m"] or ""),
            str(r["r6m"] or ""), str(r["r12m"] or ""), str(r["accel"] or ""),
            str(r["pe"] or ""), str(r["div_yield"] or ""),
            str(r["vol_trend"] or ""), str(r["rs_6m"] or ""),
            str(r["momentum"]), str(r["val_rank"]),
            str(r["accel_score"]), str(r["score"]),
        ]
        print(",".join(vals), file=sys.stderr)


if __name__ == "__main__":
    main()
