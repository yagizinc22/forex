from __future__ import annotations

import math
import pandas as pd


def compute_setup_score(row: pd.Series) -> float:
    """Return a transparent 0-100 technical setup score.

    This is not a probability of future return. It is only a normalized score
    describing how closely the latest observation matches the project's
    trend/momentum/liquidity preferences.
    """
    score = 0.0

    close = float(row.get("Close", math.nan))
    sma50 = float(row.get("SMA50", math.nan))
    sma200 = float(row.get("SMA200", math.nan))
    rsi = float(row.get("RSI14", math.nan))
    mom20 = float(row.get("MOM20_PCT", math.nan))
    vol_ratio = float(row.get("VOLUME_RATIO", math.nan))
    atr_pct = float(row.get("ATR_PCT", math.nan))

    if math.isfinite(close) and math.isfinite(sma200) and close > sma200:
        score += 25
    if math.isfinite(close) and math.isfinite(sma50) and close > sma50:
        score += 15
    if math.isfinite(sma50) and math.isfinite(sma200) and sma50 > sma200:
        score += 10

    if math.isfinite(mom20):
        if mom20 > 10:
            score += 20
        elif mom20 > 5:
            score += 15
        elif mom20 > 0:
            score += 10

    if math.isfinite(rsi):
        if 52 <= rsi <= 65:
            score += 15
        elif 45 <= rsi <= 70:
            score += 8

    if math.isfinite(vol_ratio):
        if vol_ratio >= 1.5:
            score += 10
        elif vol_ratio >= 1.1:
            score += 6

    # Prefer tradable volatility; extreme ATR receives no bonus.
    if math.isfinite(atr_pct):
        if 1.0 <= atr_pct <= 4.5:
            score += 5
        elif 0.5 <= atr_pct <= 7.0:
            score += 2

    return min(100.0, score)
