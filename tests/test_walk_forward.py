import pandas as pd

from app.optimization.walk_forward import BacktestParams, parameter_grid, walk_forward_optimize
from app.strategies.configurable import StrategyParams, add_configurable_signal


def _sample_df():
    idx = pd.date_range("2020-01-01", periods=1300, freq="B")
    close = pd.Series(range(100, 1400), index=idx, dtype=float)
    df = pd.DataFrame(index=idx)
    df["Open"] = close * 0.999
    df["High"] = close * 1.01
    df["Low"] = close * 0.99
    df["Close"] = close
    df["ATR14"] = 2.0
    df["SMA50"] = close.rolling(50).mean()
    df["SMA200"] = close.rolling(200).mean()
    df["MOM20_PCT"] = close.pct_change(20) * 100
    df["RSI14"] = 60.0
    df["VOLUME_RATIO"] = 1.2
    return df


def test_configurable_signal_respects_filters():
    df = _sample_df().iloc[-10:].copy()
    out = add_configurable_signal(df, StrategyParams(rsi_low=50, rsi_high=70, volume_ratio_min=1.1))
    assert bool(out["SIGNAL"].iloc[-1]) is True


def test_walk_forward_returns_folds_with_small_grid():
    df = _sample_df()
    grid = [
        (StrategyParams(50, 70, 1.1, 0.0, False), BacktestParams(2.0, 2.0, 20)),
        (StrategyParams(55, 70, 1.1, 0.0, False), BacktestParams(1.5, 1.5, 10)),
    ]
    folds, search = walk_forward_optimize(
        df,
        train_years=2,
        test_years=1,
        step_years=1,
        initial_cash=100000,
        risk_pct=0.5,
        fee_bps=0,
        slippage_bps=0,
        min_train_trades=1,
        grid=grid,
    )
    assert not folds.empty
    assert not search.empty
    assert set(["test_return_pct", "test_sharpe", "degradation_pct"]).issubset(folds.columns)


def test_parameter_grid_has_valid_rsi_ranges():
    grid = list(parameter_grid(rsi_lows=(70,), rsi_highs=(65, 75), volume_mins=(1.0,), momentum_mins=(0.0,), trend_filters=(False,), stop_atrs=(2.0,), target_rs=(2.0,), max_holds=(20,)))
    assert len(grid) == 1
    assert grid[0][0].rsi_low == 70
    assert grid[0][0].rsi_high == 75
