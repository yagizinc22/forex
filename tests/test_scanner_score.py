import pandas as pd

from app.scanner.score import compute_setup_score


def test_strong_setup_scores_high():
    row = pd.Series(
        {
            "Close": 120.0,
            "SMA50": 110.0,
            "SMA200": 100.0,
            "RSI14": 58.0,
            "MOM20_PCT": 12.0,
            "VOLUME_RATIO": 1.7,
            "ATR_PCT": 2.5,
        }
    )
    assert compute_setup_score(row) == 100.0


def test_weak_setup_scores_low():
    row = pd.Series(
        {
            "Close": 90.0,
            "SMA50": 100.0,
            "SMA200": 110.0,
            "RSI14": 35.0,
            "MOM20_PCT": -8.0,
            "VOLUME_RATIO": 0.7,
            "ATR_PCT": 9.0,
        }
    )
    assert compute_setup_score(row) == 0.0
