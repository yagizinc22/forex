from __future__ import annotations

import argparse

from app.backtest.portfolio import run_cross_sectional_backtest
from app.data.market_data import fetch_daily_ohlcv
from app.indicators.technical import add_indicators
from app.universe.bist100 import BIST100_Q3_2026, EFFECTIVE_FROM, EFFECTIVE_TO


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Market AI v0.5 BIST100 portfolio backtest")
    p.add_argument("--period", default="5y")
    p.add_argument("--top-n", type=int, default=5)
    p.add_argument("--rebalance-days", type=int, default=5)
    p.add_argument("--min-score", type=float, default=60.0)
    p.add_argument("--initial-cash", type=float, default=100000.0)
    p.add_argument("--fee-bps", type=float, default=10.0)
    p.add_argument("--slippage-bps", type=float, default=5.0)
    p.add_argument("--show-transactions", type=int, default=20)
    return p


def main() -> None:
    args = build_parser().parse_args()

    data = {}
    errors = []
    for symbol in BIST100_Q3_2026:
        try:
            df = fetch_daily_ohlcv(symbol, period=args.period)
            data[symbol] = add_indicators(df)
        except Exception as exc:  # data provider errors are reported, not hidden
            errors.append((symbol, str(exc)))

    result = run_cross_sectional_backtest(
        data,
        initial_cash=args.initial_cash,
        top_n=args.top_n,
        rebalance_days=args.rebalance_days,
        min_score=args.min_score,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
    )
    m = result.metrics

    print("\nMarket AI v0.5 - BIST100 cross-sectional portfolio")
    print("=" * 72)
    print(f"Initial cash          : {m.initial_cash:,.2f} TL")
    print(f"Final equity          : {m.final_equity:,.2f} TL")
    print(f"Total return          : {m.total_return_pct:.2f}%")
    print(f"CAGR                  : {m.cagr_pct:.2f}%")
    print(f"Max drawdown          : {m.max_drawdown_pct:.2f}%")
    print(f"Sharpe                : {m.sharpe:.2f}")
    print(f"Sortino               : {m.sortino:.2f}")
    print(f"Rebalances            : {m.rebalances}")
    print(f"Transactions          : {m.transactions}")
    print(f"Cumulative turnover   : {m.cumulative_turnover_pct:.2f}%")
    print(f"Average holdings      : {m.avg_holdings:.2f}")
    print(f"Exposure              : {m.exposure_pct:.2f}%")

    if not result.transactions.empty and args.show_transactions > 0:
        print("\nLast transactions")
        print("-" * 72)
        print(result.transactions.tail(args.show_transactions).to_string(index=False))

    print("\nImportant methodology note")
    print("- Signals/scores are observed at close; portfolio changes happen next open.")
    print("- Long-only, equal-weight, no leverage, no shorting.")
    print(f"- Universe file is labelled {EFFECTIVE_FROM} -> {EFFECTIVE_TO}.")
    print("- Using today's/Q3 2026 constituents over older history creates survivorship bias.")
    print("- Research-grade historical results require point-in-time index membership.\n")

    if errors:
        print(f"Data errors: {len(errors)}")
        for symbol, message in errors[:10]:
            print(f"- {symbol}: {message}")


if __name__ == "__main__":
    main()
