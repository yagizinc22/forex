from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import product
from typing import Iterable

import numpy as np
import pandas as pd

from app.backtest.event_driven import run_event_backtest
from app.strategies.configurable import StrategyParams, add_configurable_signal


@dataclass(frozen=True)
class BacktestParams:
    stop_atr: float
    target_r: float
    max_hold_days: int


@dataclass
class FoldResult:
    fold: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    strategy_params: StrategyParams
    backtest_params: BacktestParams
    train_score: float
    train_return_pct: float
    train_sharpe: float
    train_max_drawdown_pct: float
    train_trades: int
    test_return_pct: float
    test_sharpe: float
    test_max_drawdown_pct: float
    test_trades: int


def _objective(metrics, min_trades: int = 8) -> float:
    """Robust train objective; penalizes low sample size and drawdown."""
    if metrics.trades < min_trades:
        return float("-inf")
    sharpe = float(metrics.sharpe)
    if not np.isfinite(sharpe):
        sharpe = 3.0 if sharpe > 0 else 0.0
    drawdown_penalty = abs(float(metrics.max_drawdown_pct)) / 20.0
    return sharpe + (float(metrics.cagr_pct) / 25.0) - drawdown_penalty


def parameter_grid(
    *,
    rsi_lows: Iterable[float] = (45, 50, 55),
    rsi_highs: Iterable[float] = (65, 70, 75),
    volume_mins: Iterable[float] = (1.0, 1.1, 1.25),
    momentum_mins: Iterable[float] = (0.0, 2.0, 5.0),
    trend_filters: Iterable[bool] = (False, True),
    stop_atrs: Iterable[float] = (1.5, 2.0, 2.5),
    target_rs: Iterable[float] = (1.5, 2.0, 3.0),
    max_holds: Iterable[int] = (10, 20, 30),
):
    for values in product(
        rsi_lows,
        rsi_highs,
        volume_mins,
        momentum_mins,
        trend_filters,
        stop_atrs,
        target_rs,
        max_holds,
    ):
        rsi_low, rsi_high, volume_min, momentum_min, trend_filter, stop_atr, target_r, max_hold = values
        if rsi_low >= rsi_high:
            continue
        yield (
            StrategyParams(
                rsi_low=float(rsi_low),
                rsi_high=float(rsi_high),
                volume_ratio_min=float(volume_min),
                momentum_min_pct=float(momentum_min),
                require_sma50_above_sma200=bool(trend_filter),
            ),
            BacktestParams(float(stop_atr), float(target_r), int(max_hold)),
        )


def evaluate_params(
    df: pd.DataFrame,
    strategy_params: StrategyParams,
    backtest_params: BacktestParams,
    *,
    initial_cash: float,
    risk_pct: float,
    fee_bps: float,
    slippage_bps: float,
):
    signaled = add_configurable_signal(df, strategy_params)
    return run_event_backtest(
        signaled,
        initial_cash=initial_cash,
        risk_pct=risk_pct,
        stop_atr=backtest_params.stop_atr,
        target_r=backtest_params.target_r,
        max_hold_days=backtest_params.max_hold_days,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )


def _slice_with_warmup(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, warmup_bars: int = 220) -> pd.DataFrame:
    ordered = df.sort_index()
    start_pos = ordered.index.searchsorted(start, side="left")
    warm_start = max(0, start_pos - warmup_bars)
    sliced = ordered.iloc[warm_start: ordered.index.searchsorted(end, side="right")].copy()
    return sliced


def _mask_signals_to_window(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    out = df.copy()
    if "SIGNAL" in out.columns:
        mask = (out.index >= start) & (out.index <= end)
        out.loc[~mask, "SIGNAL"] = False
    return out


def walk_forward_optimize(
    df: pd.DataFrame,
    *,
    train_years: int = 3,
    test_years: int = 1,
    step_years: int = 1,
    initial_cash: float = 100_000.0,
    risk_pct: float = 0.5,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    min_train_trades: int = 8,
    grid=None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if train_years <= 0 or test_years <= 0 or step_years <= 0:
        raise ValueError("train_years, test_years ve step_years pozitif olmali")

    data = df.sort_index().copy()
    data.index = pd.to_datetime(data.index)
    if data.empty:
        return pd.DataFrame(), pd.DataFrame()

    combinations = list(grid if grid is not None else parameter_grid())
    if not combinations:
        raise ValueError("Parametre grid bos")

    first_date = pd.Timestamp(data.index.min()).normalize()
    last_date = pd.Timestamp(data.index.max()).normalize()
    train_start = first_date
    fold_no = 1
    fold_results: list[FoldResult] = []
    search_rows: list[dict] = []

    while True:
        train_end = train_start + pd.DateOffset(years=train_years) - pd.Timedelta(days=1)
        test_start = train_end + pd.Timedelta(days=1)
        test_end = test_start + pd.DateOffset(years=test_years) - pd.Timedelta(days=1)
        if test_end > last_date:
            break

        train_raw = _slice_with_warmup(data, train_start, train_end)
        test_raw = _slice_with_warmup(data, test_start, test_end)

        best = None
        best_score = float("-inf")
        best_train_result = None

        for strategy_params, bt_params in combinations:
            train_signaled = add_configurable_signal(train_raw, strategy_params)
            train_signaled = _mask_signals_to_window(train_signaled, train_start, train_end)
            train_result = run_event_backtest(
                train_signaled,
                initial_cash=initial_cash,
                risk_pct=risk_pct,
                stop_atr=bt_params.stop_atr,
                target_r=bt_params.target_r,
                max_hold_days=bt_params.max_hold_days,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
            )
            score = _objective(train_result.metrics, min_trades=min_train_trades)
            search_rows.append({
                "fold": fold_no,
                **asdict(strategy_params),
                **asdict(bt_params),
                "train_score": score,
                "train_return_pct": train_result.metrics.total_return_pct,
                "train_sharpe": train_result.metrics.sharpe,
                "train_max_drawdown_pct": train_result.metrics.max_drawdown_pct,
                "train_trades": train_result.metrics.trades,
            })
            if score > best_score:
                best_score = score
                best = (strategy_params, bt_params)
                best_train_result = train_result

        if best is None or best_train_result is None or not np.isfinite(best_score):
            train_start = train_start + pd.DateOffset(years=step_years)
            fold_no += 1
            continue

        strategy_params, bt_params = best
        test_signaled = add_configurable_signal(test_raw, strategy_params)
        test_signaled = _mask_signals_to_window(test_signaled, test_start, test_end)
        test_result = run_event_backtest(
            test_signaled,
            initial_cash=initial_cash,
            risk_pct=risk_pct,
            stop_atr=bt_params.stop_atr,
            target_r=bt_params.target_r,
            max_hold_days=bt_params.max_hold_days,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        )

        fold_results.append(FoldResult(
            fold=fold_no,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            strategy_params=strategy_params,
            backtest_params=bt_params,
            train_score=best_score,
            train_return_pct=best_train_result.metrics.total_return_pct,
            train_sharpe=best_train_result.metrics.sharpe,
            train_max_drawdown_pct=best_train_result.metrics.max_drawdown_pct,
            train_trades=best_train_result.metrics.trades,
            test_return_pct=test_result.metrics.total_return_pct,
            test_sharpe=test_result.metrics.sharpe,
            test_max_drawdown_pct=test_result.metrics.max_drawdown_pct,
            test_trades=test_result.metrics.trades,
        ))

        train_start = train_start + pd.DateOffset(years=step_years)
        fold_no += 1

    fold_rows = []
    for r in fold_results:
        fold_rows.append({
            "fold": r.fold,
            "train_start": r.train_start,
            "train_end": r.train_end,
            "test_start": r.test_start,
            "test_end": r.test_end,
            **asdict(r.strategy_params),
            **asdict(r.backtest_params),
            "train_score": r.train_score,
            "train_return_pct": r.train_return_pct,
            "train_sharpe": r.train_sharpe,
            "train_max_drawdown_pct": r.train_max_drawdown_pct,
            "train_trades": r.train_trades,
            "test_return_pct": r.test_return_pct,
            "test_sharpe": r.test_sharpe,
            "test_max_drawdown_pct": r.test_max_drawdown_pct,
            "test_trades": r.test_trades,
            "degradation_pct": r.test_return_pct - r.train_return_pct,
        })

    return pd.DataFrame(fold_rows), pd.DataFrame(search_rows)
