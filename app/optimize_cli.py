from __future__ import annotations

import argparse

import pandas as pd

from app.data.market_data import fetch_daily_ohlcv, normalize_bist_symbol
from app.indicators.technical import add_indicators
from app.optimization.walk_forward import parameter_grid, walk_forward_optimize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Market AI v0.4 walk-forward optimization")
    parser.add_argument("symbol", help="BIST sembolu, ornek: THYAO")
    parser.add_argument("--period", default="10y")
    parser.add_argument("--train-years", type=int, default=3)
    parser.add_argument("--test-years", type=int, default=1)
    parser.add_argument("--step-years", type=int, default=1)
    parser.add_argument("--initial-cash", type=float, default=100000.0)
    parser.add_argument("--risk-pct", type=float, default=0.5)
    parser.add_argument("--fee-bps", type=float, default=10.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--min-train-trades", type=int, default=8)
    parser.add_argument("--fast-grid", action="store_true", help="Daha kucuk grid ile hizli deneme")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    df = fetch_daily_ohlcv(args.symbol, period=args.period)
    df = add_indicators(df)

    grid = None
    if args.fast_grid:
        grid = list(parameter_grid(
            rsi_lows=(50,),
            rsi_highs=(65, 70),
            volume_mins=(1.0, 1.1),
            momentum_mins=(0.0, 2.0),
            trend_filters=(False, True),
            stop_atrs=(1.5, 2.0),
            target_rs=(1.5, 2.0),
            max_holds=(10, 20),
        ))

    folds, search = walk_forward_optimize(
        df,
        train_years=args.train_years,
        test_years=args.test_years,
        step_years=args.step_years,
        initial_cash=args.initial_cash,
        risk_pct=args.risk_pct,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        min_train_trades=args.min_train_trades,
        grid=grid,
    )

    print(f"\nMarket AI v0.4 - {normalize_bist_symbol(args.symbol)}")
    print("=" * 88)
    if folds.empty:
        print("Yeterli walk-forward fold olusmadi. Daha uzun period veya daha kisa train/test sec.")
        return

    cols = [
        "fold", "train_start", "train_end", "test_start", "test_end",
        "rsi_low", "rsi_high", "volume_ratio_min", "momentum_min_pct",
        "require_sma50_above_sma200", "stop_atr", "target_r", "max_hold_days",
        "train_return_pct", "train_sharpe", "train_trades",
        "test_return_pct", "test_sharpe", "test_trades", "test_max_drawdown_pct",
        "degradation_pct",
    ]
    with pd.option_context("display.max_columns", None, "display.width", 220):
        print(folds[cols].to_string(index=False, formatters={
            "train_return_pct": "{:.2f}".format,
            "train_sharpe": "{:.2f}".format,
            "test_return_pct": "{:.2f}".format,
            "test_sharpe": "{:.2f}".format,
            "test_max_drawdown_pct": "{:.2f}".format,
            "degradation_pct": "{:.2f}".format,
        }))

    profitable_folds = float((folds["test_return_pct"] > 0).mean() * 100)
    median_test_return = float(folds["test_return_pct"].median())
    median_test_sharpe = float(folds["test_sharpe"].replace([float("inf"), float("-inf")], pd.NA).dropna().median()) if not folds.empty else 0.0

    print("\nOut-of-sample summary")
    print("-" * 88)
    print(f"Fold sayisi                    : {len(folds)}")
    print(f"Pozitif test fold orani        : {profitable_folds:.1f}%")
    print(f"Medyan test getirisi           : {median_test_return:.2f}%")
    print(f"Medyan test Sharpe             : {median_test_sharpe:.2f}")
    print(f"Toplam grid degerlendirmesi    : {len(search)}")
    print("\nNOT: Train performansi secim icindir; gercek degerlendirme test kolonlaridir.")
    print("Bu arac arastirma amaclidir; yatirim tavsiyesi veya garanti getiri sistemi degildir.\n")


if __name__ == "__main__":
    main()
