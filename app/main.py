from __future__ import annotations

import argparse

from app.backtest.signal_edge import backtest_next_open
from app.data.market_data import fetch_daily_ohlcv, normalize_bist_symbol
from app.indicators.technical import add_indicators
from app.risk.position_sizing import position_size
from app.strategies.baseline import add_baseline_signal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Market AI v0.1")
    parser.add_argument("symbol", help="BIST sembolu, ornek: THYAO")
    parser.add_argument("--period", default="5y", help="Yahoo Finance period, varsayilan: 5y")
    parser.add_argument("--portfolio", type=float, default=100000.0)
    parser.add_argument("--risk-pct", type=float, default=0.5)
    parser.add_argument("--fee-bps", type=float, default=10.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    df = fetch_daily_ohlcv(args.symbol, period=args.period)
    df = add_indicators(df)
    df = add_baseline_signal(df)

    latest = df.dropna(subset=["SMA200", "RSI14", "ATR14"]).iloc[-1]
    bt = backtest_next_open(df, fee_bps=args.fee_bps)

    entry = float(latest["Close"])
    stop = max(0.01, entry - 2 * float(latest["ATR14"]))
    risk = position_size(args.portfolio, args.risk_pct, entry, stop)

    print(f"\nMarket AI v0.1 - {normalize_bist_symbol(args.symbol)}")
    print("-" * 52)
    print(f"Son kapanis       : {entry:.2f}")
    print(f"SMA50             : {latest['SMA50']:.2f}")
    print(f"SMA200            : {latest['SMA200']:.2f}")
    print(f"RSI14             : {latest['RSI14']:.2f}")
    print(f"ATR14             : {latest['ATR14']:.2f} ({latest['ATR_PCT']:.2f}%)")
    print(f"20g momentum      : {latest['MOM20_PCT']:.2f}%")
    print(f"Hacim orani       : {latest['VOLUME_RATIO']:.2f}x")
    print(f"Baseline sinyal   : {'EVET' if bool(latest['SIGNAL']) else 'HAYIR'}")

    print("\nSignal-edge backtest")
    print("-" * 52)
    print(f"Islem sayisi      : {bt.trades}")
    print(f"Win rate          : {bt.win_rate_pct:.2f}%")
    print(f"Ortalama getiri   : {bt.avg_return_pct:.3f}%")
    print(f"Ort. kazanan      : {bt.avg_win_pct:.3f}%")
    print(f"Ort. kaybeden     : {bt.avg_loss_pct:.3f}%")
    print(f"Profit factor     : {bt.profit_factor:.2f}")

    print("\nRisk plani (ornek: 2x ATR stop)")
    print("-" * 52)
    print(f"Portfoy           : {args.portfolio:,.2f} TL")
    print(f"Risk limiti       : {args.risk_pct:.2f}% = {risk['risk_budget']:,.2f} TL")
    print(f"Ornek stop        : {stop:.2f}")
    print(f"Maks lot          : {risk['shares']}")
    print(f"Pozisyon degeri   : {risk['position_value']:,.2f} TL")
    print(f"Portfoy payi      : {risk['portfolio_allocation_pct']:.2f}%")
    print("\nUYARI: Bu cikti yatirim tavsiyesi degildir; v0.1 arastirma prototipidir.\n")


if __name__ == "__main__":
    main()
