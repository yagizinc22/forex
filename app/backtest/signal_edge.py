from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    trades: int
    win_rate_pct: float
    avg_return_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    expectancy_pct: float


def backtest_next_open(df: pd.DataFrame, fee_bps: float = 10.0) -> BacktestResult:
    if "SIGNAL" not in df.columns:
        raise ValueError("SIGNAL kolonu bulunamadi")

    out = df.copy()
    entry = out["Open"].shift(-1)
    exit_ = out["Open"].shift(-2)
    gross = (exit_ / entry) - 1
    net = gross - (fee_bps / 10_000)

    returns = net[out["SIGNAL"].fillna(False)].dropna()
    trades = len(returns)
    if trades == 0:
        return BacktestResult(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    wins = returns[returns > 0]
    losses = returns[returns <= 0]
    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    return BacktestResult(
        trades=trades,
        win_rate_pct=float((returns > 0).mean() * 100),
        avg_return_pct=float(returns.mean() * 100),
        avg_win_pct=float(wins.mean() * 100) if len(wins) else 0.0,
        avg_loss_pct=float(losses.mean() * 100) if len(losses) else 0.0,
        profit_factor=profit_factor,
        expectancy_pct=float(returns.mean() * 100),
    )
