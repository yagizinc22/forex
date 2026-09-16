from __future__ import annotations

import pandas as pd
import yfinance as yf

REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def normalize_bist_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    return symbol if symbol.endswith(".IS") else f"{symbol}.IS"


def fetch_daily_ohlcv(symbol: str, period: str = "5y") -> pd.DataFrame:
    ticker = normalize_bist_symbol(symbol)
    df = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if df.empty:
        raise ValueError(f"Veri bulunamadi: {ticker}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Eksik piyasa verisi kolonlari: {missing}")

    out = df[REQUIRED_COLUMNS].copy()
    out.index = pd.to_datetime(out.index)
    out = out.sort_index().dropna(subset=["Open", "High", "Low", "Close"])
    out["Volume"] = out["Volume"].fillna(0)
    return out
