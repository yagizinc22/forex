from __future__ import annotations

import pandas as pd


def add_baseline_signal(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    required = ["Close", "SMA50", "SMA200", "MOM20_PCT", "RSI14", "VOLUME_RATIO"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"Eksik indikator kolonlari: {missing}")

    out["SIGNAL"] = (
        (out["Close"] > out["SMA200"])
        & (out["Close"] > out["SMA50"])
        & (out["MOM20_PCT"] > 0)
        & (out["RSI14"] >= 50)
        & (out["RSI14"] <= 70)
        & (out["VOLUME_RATIO"] > 1.10)
    )
    return out
