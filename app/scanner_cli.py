from __future__ import annotations

import argparse

from app.scanner.bist_scanner import scan_symbols
from app.universe.bist100 import BIST100_Q3_2026, EFFECTIVE_FROM, EFFECTIVE_TO, UNIVERSE_NAME, validate_universe


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Market AI v0.2 BIST scanner")
    parser.add_argument("--period", default="5y")
    parser.add_argument("--fee-bps", type=float, default=10.0)
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--signals-only", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    validate_universe()

    result = scan_symbols(BIST100_Q3_2026, period=args.period, fee_bps=args.fee_bps)
    table = result.table.copy()

    if args.signals_only and not table.empty:
        table = table[table["signal"]]

    columns = [
        "symbol",
        "date",
        "close",
        "setup_score",
        "signal",
        "rsi14",
        "mom20_pct",
        "volume_ratio",
        "atr_pct",
        "bt_trades",
        "bt_win_rate_pct",
        "bt_expectancy_pct",
        "bt_profit_factor",
    ]

    print(f"\nMarket AI v0.2 - {UNIVERSE_NAME}")
    print(f"Universe effective: {EFFECTIVE_FROM} -> {EFFECTIVE_TO}")
    print("NOTE: setup_score is not a probability; it is a rules-fit score.\n")

    if table.empty:
        print("Tarama sonucu yok.")
    else:
        shown = table[columns].head(max(args.top, 1))
        with __import__("pandas").option_context("display.max_columns", None, "display.width", 180):
            print(shown.to_string(index=False, formatters={
                "close": "{:.2f}".format,
                "setup_score": "{:.0f}".format,
                "rsi14": "{:.1f}".format,
                "mom20_pct": "{:.2f}".format,
                "volume_ratio": "{:.2f}".format,
                "atr_pct": "{:.2f}".format,
                "bt_win_rate_pct": "{:.1f}".format,
                "bt_expectancy_pct": "{:.3f}".format,
                "bt_profit_factor": "{:.2f}".format,
            }))

    if result.errors:
        print(f"\nVeri/hesaplama hatasi olan sembol sayisi: {len(result.errors)}")
        for symbol, message in result.errors[:10]:
            print(f"- {symbol}: {message}")
        if len(result.errors) > 10:
            print(f"... ve {len(result.errors) - 10} hata daha")


if __name__ == "__main__":
    main()
