from __future__ import annotations

import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["SMA20"] = out["Close"].rolling(20).mean()
    out["SMA50"] = out["Close"].rolling(50).mean()
    out["SMA200"] = out["Close"].rolling(200).mean()

    delta = out["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out["RSI14"] = 100 - (100 / (1 + rs))
    out.loc[(avg_loss == 0) & (avg_gain > 0), "RSI14"] = 100
    out.loc[(avg_gain == 0) & (avg_loss == 0), "RSI14"] = 50

    prev_close = out["Close"].shift(1)
    true_range = pd.concat(
        [
            out["High"] - out["Low"],
            (out["High"] - prev_close).abs(),
            (out["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["ATR14"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    out["ATR_PCT"] = (out["ATR14"] / out["Close"]) * 100

    out["VOL20"] = out["Volume"].rolling(20).mean()
    out["VOLUME_RATIO"] = out["Volume"] / out["VOL20"].replace(0, np.nan)
    out["MOM20_PCT"] = out["Close"].pct_change(20) * 100

    return out
