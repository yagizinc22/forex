from __future__ import annotations

from dataclasses import dataclass
from math import floor, sqrt

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Trade:
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    shares: int
    stop_price: float
    target_price: float
    pnl: float
    return_pct: float
    r_multiple: float
    holding_days: int
    exit_reason: str


@dataclass(frozen=True)
class BacktestMetrics:
    initial_cash: float
    final_equity: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe: float
    sortino: float
    trades: int
    win_rate_pct: float
    profit_factor: float
    expectancy_r: float
    avg_trade_return_pct: float
    avg_holding_days: float
    max_consecutive_losses: int
    exposure_pct: float


@dataclass
class EventBacktestResult:
    metrics: BacktestMetrics
    trades: pd.DataFrame
    equity_curve: pd.DataFrame


def _finite(value: float, fallback: float = 0.0) -> float:
    return float(value) if np.isfinite(value) else fallback


def _max_consecutive_losses(pnls: list[float]) -> int:
    best = 0
    current = 0
    for pnl in pnls:
        if pnl <= 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _calculate_metrics(
    initial_cash: float,
    equity_curve: pd.DataFrame,
    trades: list[Trade],
    exposed_days: int,
) -> BacktestMetrics:
    final_equity = float(equity_curve["Equity"].iloc[-1]) if not equity_curve.empty else initial_cash
    total_return = (final_equity / initial_cash) - 1 if initial_cash > 0 else 0.0

    if len(equity_curve) >= 2:
        days = max((equity_curve.index[-1] - equity_curve.index[0]).days, 1)
        years = days / 365.25
        cagr = (final_equity / initial_cash) ** (1 / years) - 1 if final_equity > 0 else -1.0

        daily_returns = equity_curve["Equity"].pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        if len(daily_returns) >= 2 and daily_returns.std(ddof=1) > 0:
            sharpe = sqrt(252) * daily_returns.mean() / daily_returns.std(ddof=1)
        else:
            sharpe = 0.0

        downside = daily_returns[daily_returns < 0]
        if len(downside) >= 2 and downside.std(ddof=1) > 0:
            sortino = sqrt(252) * daily_returns.mean() / downside.std(ddof=1)
        elif daily_returns.mean() > 0 and len(downside) == 0:
            sortino = float("inf")
        else:
            sortino = 0.0

        running_max = equity_curve["Equity"].cummax()
        drawdown = (equity_curve["Equity"] / running_max) - 1
        max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0
    else:
        cagr = sharpe = sortino = max_drawdown = 0.0

    pnls = [t.pnl for t in trades]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    return BacktestMetrics(
        initial_cash=float(initial_cash),
        final_equity=final_equity,
        total_return_pct=total_return * 100,
        cagr_pct=cagr * 100,
        max_drawdown_pct=max_drawdown * 100,
        sharpe=_finite(sharpe, float("inf") if sharpe > 0 else 0.0),
        sortino=_finite(sortino, float("inf") if sortino > 0 else 0.0),
        trades=len(trades),
        win_rate_pct=(sum(1 for x in pnls if x > 0) / len(trades) * 100) if trades else 0.0,
        profit_factor=float(profit_factor),
        expectancy_r=float(np.mean([t.r_multiple for t in trades])) if trades else 0.0,
        avg_trade_return_pct=float(np.mean([t.return_pct for t in trades])) if trades else 0.0,
        avg_holding_days=float(np.mean([t.holding_days for t in trades])) if trades else 0.0,
        max_consecutive_losses=_max_consecutive_losses(pnls),
        exposure_pct=(exposed_days / len(equity_curve) * 100) if len(equity_curve) else 0.0,
    )


def run_event_backtest(
    df: pd.DataFrame,
    *,
    initial_cash: float = 100_000.0,
    risk_pct: float = 0.5,
    stop_atr: float = 2.0,
    target_r: float = 2.0,
    max_hold_days: int = 20,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
) -> EventBacktestResult:
    """Run a single-position, long-only event-driven backtest.

    Rules:
    - SIGNAL is observed only after a bar closes.
    - Entry occurs at the next session open, never on the signal bar.
    - Stop distance uses ATR14 from the signal bar, avoiding look-ahead.
    - Position size risks `risk_pct` of current equity before fees, capped by cash.
    - Only one position can be open at a time.
    - Gap-through stop/target exits at the session open (with sell slippage).
    - If stop and target are both touched intraday, stop is assumed first.
      This deliberately conservative rule avoids optimistic OHLC ambiguity.
    - A time exit occurs at the close once `max_hold_days` is reached.
    """
    required = {"Open", "High", "Low", "Close", "SIGNAL", "ATR14"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Eksik backtest kolonlari: {missing}")
    if initial_cash <= 0:
        raise ValueError("initial_cash pozitif olmali")
    if not 0 < risk_pct <= 100:
        raise ValueError("risk_pct 0 ile 100 arasinda olmali")
    if stop_atr <= 0 or target_r <= 0 or max_hold_days <= 0:
        raise ValueError("stop_atr, target_r ve max_hold_days pozitif olmali")
    if fee_bps < 0 or slippage_bps < 0:
        raise ValueError("fee_bps ve slippage_bps negatif olamaz")

    data = df.sort_index().copy()
    data.index = pd.to_datetime(data.index)
    data = data.dropna(subset=["Open", "High", "Low", "Close"])
    if data.empty:
        metrics = _calculate_metrics(initial_cash, pd.DataFrame(columns=["Equity"]), [], 0)
        return EventBacktestResult(metrics, pd.DataFrame(), pd.DataFrame(columns=["Equity", "Cash", "PositionValue"]))

    fee_rate = fee_bps / 10_000
    slip_rate = slippage_bps / 10_000

    cash = float(initial_cash)
    shares = 0
    entry_price = stop_price = target_price = 0.0
    entry_fee = risk_amount_at_entry = 0.0
    entry_date: pd.Timestamp | None = None
    holding_days = 0

    trades: list[Trade] = []
    equity_rows: list[dict[str, float | pd.Timestamp]] = []
    exposed_days = 0

    def close_position(date: pd.Timestamp, raw_price: float, reason: str) -> None:
        nonlocal cash, shares, entry_price, stop_price, target_price
        nonlocal entry_fee, risk_amount_at_entry, entry_date, holding_days

        exit_price = max(0.01, float(raw_price) * (1 - slip_rate))
        exit_value = exit_price * shares
        exit_fee = exit_value * fee_rate
        cash += exit_value - exit_fee

        invested = entry_price * shares + entry_fee
        pnl = (exit_value - exit_fee) - invested
        return_pct = (pnl / invested * 100) if invested > 0 else 0.0
        r_multiple = (pnl / risk_amount_at_entry) if risk_amount_at_entry > 0 else 0.0

        trades.append(
            Trade(
                entry_date=pd.Timestamp(entry_date),
                exit_date=pd.Timestamp(date),
                entry_price=entry_price,
                exit_price=exit_price,
                shares=shares,
                stop_price=stop_price,
                target_price=target_price,
                pnl=pnl,
                return_pct=return_pct,
                r_multiple=r_multiple,
                holding_days=holding_days,
                exit_reason=reason,
            )
        )

        shares = 0
        entry_price = stop_price = target_price = 0.0
        entry_fee = risk_amount_at_entry = 0.0
        entry_date = None
        holding_days = 0

    for i, (date, row) in enumerate(data.iterrows()):
        date = pd.Timestamp(date)
        opened_today = False

        # A close-of-day signal from t-1 may create an order for today's open.
        if shares == 0 and i > 0:
            prev = data.iloc[i - 1]
            prev_signal = bool(prev["SIGNAL"]) if pd.notna(prev["SIGNAL"]) else False
            prev_atr = float(prev["ATR14"]) if pd.notna(prev["ATR14"]) else np.nan
            if prev_signal and np.isfinite(prev_atr) and prev_atr > 0:
                raw_entry = float(row["Open"])
                candidate_entry = raw_entry * (1 + slip_rate)
                risk_per_share = stop_atr * prev_atr
                candidate_stop = candidate_entry - risk_per_share
                candidate_target = candidate_entry + target_r * risk_per_share

                current_equity = cash
                risk_budget = current_equity * (risk_pct / 100)
                risk_sized_shares = floor(risk_budget / risk_per_share)
                cash_sized_shares = floor(cash / (candidate_entry * (1 + fee_rate)))
                candidate_shares = max(0, min(risk_sized_shares, cash_sized_shares))

                if candidate_shares > 0 and candidate_stop > 0:
                    shares = candidate_shares
                    entry_price = candidate_entry
                    stop_price = candidate_stop
                    target_price = candidate_target
                    entry_fee = entry_price * shares * fee_rate
                    risk_amount_at_entry = risk_per_share * shares
                    cash -= entry_price * shares + entry_fee
                    entry_date = date
                    holding_days = 0
                    opened_today = True

        if shares > 0:
            exposed_days += 1
            holding_days += 1

            open_ = float(row["Open"])
            low = float(row["Low"])
            high = float(row["High"])
            close = float(row["Close"])

            # Overnight gap logic applies only to positions carried into today.
            if not opened_today and open_ <= stop_price:
                close_position(date, open_, "gap_stop")
            elif not opened_today and open_ >= target_price:
                close_position(date, open_, "gap_target")
            elif low <= stop_price and high >= target_price:
                close_position(date, stop_price, "stop_ambiguous")
            elif low <= stop_price:
                close_position(date, stop_price, "stop")
            elif high >= target_price:
                close_position(date, target_price, "target")
            elif holding_days >= max_hold_days:
                close_position(date, close, "time")

        position_value = shares * float(row["Close"]) if shares > 0 else 0.0
        equity_rows.append(
            {
                "Date": date,
                "Equity": cash + position_value,
                "Cash": cash,
                "PositionValue": position_value,
            }
        )

    # Liquidate an open position on the final close so final equity is realized.
    if shares > 0:
        final_date = pd.Timestamp(data.index[-1])
        final_close = float(data.iloc[-1]["Close"])
        close_position(final_date, final_close, "end_of_data")
        equity_rows[-1]["Equity"] = cash
        equity_rows[-1]["Cash"] = cash
        equity_rows[-1]["PositionValue"] = 0.0

    equity_curve = pd.DataFrame(equity_rows).set_index("Date")
    trade_frame = pd.DataFrame([t.__dict__ for t in trades])
    metrics = _calculate_metrics(initial_cash, equity_curve, trades, exposed_days)
    return EventBacktestResult(metrics=metrics, trades=trade_frame, equity_curve=equity_curve)
