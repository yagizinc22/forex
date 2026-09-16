from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.backtest.signal_edge import backtest_next_open
from app.data.market_data import fetch_daily_ohlcv, normalize_bist_symbol
from app.indicators.technical import add_indicators
from app.scanner.score import compute_setup_score
from app.strategies.baseline import add_baseline_signal


@dataclass
class ScanResult:
    table: pd.DataFrame
    errors: list[tuple[str, str]]


def scan_symbols(
    symbols: list[str] | tuple[str, ...],
    period: str = "5y",
    fee_bps: float = 10.0,
) -> ScanResult:
    rows: list[dict] = []
    errors: list[tuple[str, str]] = []

    for symbol in symbols:
        try:
            df = fetch_daily_ohlcv(symbol, period=period)
            df = add_indicators(df)
            df = add_baseline_signal(df)

            ready = df.dropna(subset=["SMA50", "SMA200", "RSI14", "ATR14", "MOM20_PCT"])
            if ready.empty:
                raise ValueError("Yeterli tarihsel veri yok")

            latest = ready.iloc[-1]
            bt = backtest_next_open(df, fee_bps=fee_bps)

            rows.append(
                {
                    "symbol": symbol.upper(),
                    "ticker": normalize_bist_symbol(symbol),
                    "date": ready.index[-1].date().isoformat(),
                    "close": float(latest["Close"]),
                    "setup_score": compute_setup_score(latest),
                    "signal": bool(latest["SIGNAL"]),
                    "rsi14": float(latest["RSI14"]),
                    "mom20_pct": float(latest["MOM20_PCT"]),
                    "volume_ratio": float(latest["VOLUME_RATIO"]) if pd.notna(latest["VOLUME_RATIO"]) else float("nan"),
                    "atr_pct": float(latest["ATR_PCT"]),
                    "above_sma50": bool(latest["Close"] > latest["SMA50"]),
                    "above_sma200": bool(latest["Close"] > latest["SMA200"]),
                    "sma50_above_sma200": bool(latest["SMA50"] > latest["SMA200"]),
                    "bt_trades": bt.trades,
                    "bt_win_rate_pct": bt.win_rate_pct,
                    "bt_expectancy_pct": bt.expectancy_pct,
                    "bt_profit_factor": bt.profit_factor,
                }
            )
        except Exception as exc:  # scanner should continue if one ticker fails
            errors.append((symbol, str(exc)))

    table = pd.DataFrame(rows)
    if not table.empty:
        table = table.sort_values(
            ["setup_score", "bt_expectancy_pct", "bt_trades"],
            ascending=[False, False, False],
        ).reset_index(drop=True)

    return ScanResult(table=table, errors=errors)
