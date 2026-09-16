from __future__ import annotations

import argparse

from app.backtest.event_driven import run_event_backtest
from app.data.market_data import fetch_daily_ohlcv, normalize_bist_symbol
from app.indicators.technical import add_indicators
from app.strategies.baseline import add_baseline_signal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Market AI v0.3 event-driven backtest")
    parser.add_argument("symbol", help="BIST sembolu, ornek: THYAO")
    parser.add_argument("--period", default="5y")
    parser.add_argument("--initial-cash", type=float, default=100000.0)
    parser.add_argument("--risk-pct", type=float, default=0.5)
    parser.add_argument("--stop-atr", type=float, default=2.0)
    parser.add_argument("--target-r", type=float, default=2.0)
    parser.add_argument("--max-hold", type=int, default=20)
    parser.add_argument("--fee-bps", type=float, default=10.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--show-trades", type=int, default=10)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    df = fetch_daily_ohlcv(args.symbol, period=args.period)
    df = add_indicators(df)
    df = add_baseline_signal(df)

    result = run_event_backtest(
        df,
        initial_cash=args.initial_cash,
        risk_pct=args.risk_pct,
        stop_atr=args.stop_atr,
        target_r=args.target_r,
        max_hold_days=args.max_hold,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
    )
    m = result.metrics

    print(f"\nMarket AI v0.3 - {normalize_bist_symbol(args.symbol)}")
    print("=" * 64)
    print(f"Initial cash          : {m.initial_cash:,.2f} TL")
    print(f"Final equity          : {m.final_equity:,.2f} TL")
    print(f"Total return          : {m.total_return_pct:.2f}%")
    print(f"CAGR                  : {m.cagr_pct:.2f}%")
    print(f"Max drawdown          : {m.max_drawdown_pct:.2f}%")
    print(f"Sharpe                : {m.sharpe:.2f}")
    print(f"Sortino               : {m.sortino:.2f}")
    print(f"Trades                : {m.trades}")
    print(f"Win rate              : {m.win_rate_pct:.2f}%")
    print(f"Profit factor         : {m.profit_factor:.2f}")
    print(f"Expectancy            : {m.expectancy_r:.3f} R")
    print(f"Avg trade return      : {m.avg_trade_return_pct:.3f}%")
    print(f"Avg holding days      : {m.avg_holding_days:.2f}")
    print(f"Max consecutive loss  : {m.max_consecutive_losses}")
    print(f"Exposure              : {m.exposure_pct:.2f}%")

    if not result.trades.empty and args.show_trades > 0:
        cols = [
            "entry_date", "exit_date", "entry_price", "exit_price", "shares",
            "pnl", "return_pct", "r_multiple", "holding_days", "exit_reason",
        ]
        print("\nLast trades")
        print("-" * 64)
        print(result.trades[cols].tail(args.show_trades).to_string(index=False))

    print("\nNotes")
    print("- Signal is read at close; entry is next session open.")
    print("- One long position at a time; no overlapping trades.")
    print("- If stop and target are both hit intraday, stop is assumed first.")
    print("- This is a research backtest, not a prediction or investment recommendation.\n")


if __name__ == "__main__":
    main()
