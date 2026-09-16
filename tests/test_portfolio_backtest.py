import pandas as pd

from app.backtest.portfolio import run_cross_sectional_backtest


def _frame(scores, opens=None, closes=None):
    n = len(scores)
    idx = pd.date_range("2026-01-01", periods=n, freq="D")
    opens = opens or [100.0] * n
    closes = closes or [100.0] * n
    return pd.DataFrame({"Open": opens, "Close": closes, "SETUP_SCORE": scores}, index=idx)


def test_portfolio_executes_after_signal_day_close():
    data = {
        "AAA": _frame([90, 90, 90], opens=[100, 110, 120], closes=[100, 111, 121]),
        "BBB": _frame([10, 10, 10], opens=[100, 100, 100], closes=[100, 100, 100]),
    }
    result = run_cross_sectional_backtest(
        data,
        initial_cash=1000,
        top_n=1,
        rebalance_days=1,
        min_score=60,
        fee_bps=0,
        slippage_bps=0,
    )
    first_buy = result.transactions[result.transactions["side"] == "BUY"].iloc[0]
    assert first_buy["symbol"] == "AAA"
    assert first_buy["price"] == 110
    assert first_buy["signal_date"] == pd.Timestamp("2026-01-01")


def test_top_n_selection_is_cross_sectional_and_ranked():
    data = {
        "AAA": _frame([80, 80, 80]),
        "BBB": _frame([90, 90, 90]),
        "CCC": _frame([70, 70, 70]),
    }
    result = run_cross_sectional_backtest(
        data,
        initial_cash=3000,
        top_n=2,
        rebalance_days=2,
        min_score=60,
        fee_bps=0,
        slippage_bps=0,
    )
    first = result.selections[result.selections["signal_date"] == pd.Timestamp("2026-01-01")]
    assert first["symbol"].tolist() == ["BBB", "AAA"]


def test_portfolio_does_not_use_leverage():
    data = {
        "AAA": _frame([100, 100], opens=[100, 100], closes=[100, 100]),
        "BBB": _frame([99, 99], opens=[100, 100], closes=[100, 100]),
    }
    result = run_cross_sectional_backtest(
        data,
        initial_cash=1000,
        top_n=2,
        rebalance_days=1,
        min_score=0,
        fee_bps=0,
        slippage_bps=0,
    )
    assert (result.equity_curve["Cash"] >= -1e-9).all()
    assert (result.equity_curve["Exposure"] <= 1.0000001).all()
