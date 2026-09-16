from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class StrategyParams:
    rsi_low: float = 50.0
    rsi_high: float = 70.0
    volume_ratio_min: float = 1.10
    momentum_min_pct: float = 0.0
    require_sma50_above_sma200: bool = False

    def validate(self) -> None:
        if not 0 <= self.rsi_low < self.rsi_high <= 100:
            raise ValueError("RSI araligi 0-100 icinde ve rsi_low < rsi_high olmali")
        if self.volume_ratio_min < 0:
            raise ValueError("volume_ratio_min negatif olamaz")


def add_configurable_signal(df: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    """Add a fully backward-looking long entry signal.

    The function uses only values already present on the current bar. Indicators
    are assumed to have been calculated with trailing/rolling formulas.
    """
    params.validate()
    out = df.copy()
    required = ["Close", "SMA50", "SMA200", "MOM20_PCT", "RSI14", "VOLUME_RATIO"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"Eksik indikator kolonlari: {missing}")

    signal = (
        (out["Close"] > out["SMA200"])
        & (out["Close"] > out["SMA50"])
        & (out["MOM20_PCT"] > params.momentum_min_pct)
        & (out["RSI14"] >= params.rsi_low)
        & (out["RSI14"] <= params.rsi_high)
        & (out["VOLUME_RATIO"] > params.volume_ratio_min)
    )

    if params.require_sma50_above_sma200:
        signal &= out["SMA50"] > out["SMA200"]

    out["SIGNAL"] = signal.fillna(False)
    return out
