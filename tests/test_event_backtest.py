import pandas as pd

from app.backtest.event_driven import run_event_backtest


def _frame(rows):
    df = pd.DataFrame(rows)
    df.index = pd.date_range("2026-01-01", periods=len(df), freq="D")
    return df


def test_entry_occurs_on_next_open_not_signal_close():
    df = _frame(
        [
            {"Open": 100, "High": 101, "Low": 99, "Close": 100, "SIGNAL": True, "ATR14": 2},
            {"Open": 110, "High": 112, "Low": 109, "Close": 111, "SIGNAL": False, "ATR14": 2},
            {"Open": 111, "High": 116, "Low": 110, "Close": 115, "SIGNAL": False, "ATR14": 2},
        ]
    )
    result = run_event_backtest(
        df,
        initial_cash=100000,
        risk_pct=1.0,
        stop_atr=2.0,
        target_r=1.0,
        max_hold_days=10,
        fee_bps=0,
        slippage_bps=0,
    )
    assert len(result.trades) == 1
    assert result.trades.iloc[0]["entry_price"] == 110


def test_same_bar_stop_and_target_uses_conservative_stop():
    df = _frame(
        [
            {"Open": 100, "High": 101, "Low": 99, "Close": 100, "SIGNAL": True, "ATR14": 1},
            {"Open": 100, "High": 103, "Low": 97, "Close": 101, "SIGNAL": False, "ATR14": 1},
        ]
    )
    result = run_event_backtest(
        df,
        initial_cash=100000,
        risk_pct=1.0,
        stop_atr=2.0,
        target_r=1.0,
        max_hold_days=10,
        fee_bps=0,
        slippage_bps=0,
    )
    trade = result.trades.iloc[0]
    assert trade["exit_reason"] == "stop_ambiguous"
    assert trade["exit_price"] == 98


def test_trades_do_not_overlap():
    df = _frame(
        [
            {"Open": 100, "High": 101, "Low": 99, "Close": 100, "SIGNAL": True, "ATR14": 1},
            {"Open": 100, "High": 101, "Low": 99, "Close": 100, "SIGNAL": True, "ATR14": 1},
            {"Open": 100, "High": 101, "Low": 99, "Close": 100, "SIGNAL": True, "ATR14": 1},
            {"Open": 100, "High": 101, "Low": 99, "Close": 100, "SIGNAL": False, "ATR14": 1},
        ]
    )
    result = run_event_backtest(
        df,
        initial_cash=100000,
        risk_pct=1.0,
        stop_atr=5.0,
        target_r=5.0,
        max_hold_days=2,
        fee_bps=0,
        slippage_bps=0,
    )
    assert len(result.trades) >= 1
    for i in range(1, len(result.trades)):
        previous_exit = pd.Timestamp(result.trades.iloc[i - 1]["exit_date"])
        next_entry = pd.Timestamp(result.trades.iloc[i]["entry_date"])
        assert next_entry > previous_exit


def test_risk_sizing_caps_position_by_cash():
    df = _frame(
        [
            {"Open": 100, "High": 100, "Low": 100, "Close": 100, "SIGNAL": True, "ATR14": 0.1},
            {"Open": 100, "High": 100, "Low": 100, "Close": 100, "SIGNAL": False, "ATR14": 0.1},
        ]
    )
    result = run_event_backtest(
        df,
        initial_cash=1000,
        risk_pct=100.0,
        stop_atr=1.0,
        target_r=2.0,
        max_hold_days=1,
        fee_bps=0,
        slippage_bps=0,
    )
    assert result.trades.iloc[0]["shares"] <= 10
