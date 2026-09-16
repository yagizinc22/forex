import pandas as pd

from app.backtest.signal_edge import backtest_next_open
from app.strategies.baseline import add_baseline_signal


def test_baseline_signal_true_when_all_conditions_hold():
    df = pd.DataFrame(
        {
            "Close": [120.0],
            "SMA50": [110.0],
            "SMA200": [100.0],
            "MOM20_PCT": [5.0],
            "RSI14": [60.0],
            "VOLUME_RATIO": [1.2],
        }
    )
    out = add_baseline_signal(df)
    assert bool(out.loc[0, "SIGNAL"]) is True


def test_backtest_next_open_uses_future_open_prices():
    df = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 103.0, 102.0],
            "SIGNAL": [True, False, False, False],
        }
    )
    result = backtest_next_open(df, fee_bps=0)
    assert result.trades == 1
    assert round(result.avg_return_pct, 6) == round(((103 / 101) - 1) * 100, 6)
