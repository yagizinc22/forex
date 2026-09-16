from __future__ import annotations

from dataclasses import dataclass
from math import floor, sqrt

import numpy as np
import pandas as pd

from app.scanner.score import compute_setup_score


@dataclass(frozen=True)
class PortfolioMetrics:
    initial_cash: float
    final_equity: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe: float
    sortino: float
    rebalances: int
    transactions: int
    cumulative_turnover_pct: float
    avg_holdings: float
    exposure_pct: float


@dataclass
class PortfolioBacktestResult:
    metrics: PortfolioMetrics
    equity_curve: pd.DataFrame
    transactions: pd.DataFrame
    selections: pd.DataFrame


def _score_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_index().copy()
    out.index = pd.to_datetime(out.index)
    if "SETUP_SCORE" not in out.columns:
        out["SETUP_SCORE"] = out.apply(compute_setup_score, axis=1)
    return out


def _ratio_metrics(equity: pd.Series) -> tuple[float, float, float, float]:
    if len(equity) < 2:
        return 0.0, 0.0, 0.0, 0.0

    days = max((equity.index[-1] - equity.index[0]).days, 1)
    years = days / 365.25
    total_return = (float(equity.iloc[-1]) / float(equity.iloc[0])) - 1
    cagr = (float(equity.iloc[-1]) / float(equity.iloc[0])) ** (1 / years) - 1 if equity.iloc[-1] > 0 else -1.0

    daily = equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    sharpe = 0.0
    sortino = 0.0
    if len(daily) >= 2 and daily.std(ddof=1) > 0:
        sharpe = sqrt(252) * daily.mean() / daily.std(ddof=1)
    downside = daily[daily < 0]
    if len(downside) >= 2 and downside.std(ddof=1) > 0:
        sortino = sqrt(252) * daily.mean() / downside.std(ddof=1)
    elif len(daily) and daily.mean() > 0 and len(downside) == 0:
        sortino = float("inf")

    running_max = equity.cummax()
    drawdown = (equity / running_max) - 1
    max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0
    return total_return * 100, cagr * 100, max_drawdown * 100, float(sharpe), float(sortino)


def run_cross_sectional_backtest(
    data_by_symbol: dict[str, pd.DataFrame],
    *,
    initial_cash: float = 100_000.0,
    top_n: int = 5,
    rebalance_days: int = 5,
    min_score: float = 60.0,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
) -> PortfolioBacktestResult:
    """Backtest an equal-weight, long-only cross-sectional portfolio.

    Methodology:
    - Scores are observed only after each rebalance signal day's close.
    - Ranked targets are executed on the next common session open.
    - Holdings are equal-weighted across available targets.
    - Sells are executed before buys; cash cannot go negative and leverage is not used.
    - Missing close prices are forward-filled only for mark-to-market. A symbol without
      an actual open on an execution day cannot be newly traded that day.

    The function deliberately accepts a symbol->DataFrame mapping so callers can
    provide a point-in-time universe. Passing today's constituents over old history
    creates survivorship bias and is not a research-grade historical universe.
    """
    if initial_cash <= 0:
        raise ValueError("initial_cash pozitif olmali")
    if top_n <= 0 or rebalance_days <= 0:
        raise ValueError("top_n ve rebalance_days pozitif olmali")
    if not 0 <= min_score <= 100:
        raise ValueError("min_score 0-100 arasinda olmali")
    if fee_bps < 0 or slippage_bps < 0:
        raise ValueError("fee_bps ve slippage_bps negatif olamaz")

    prepared: dict[str, pd.DataFrame] = {}
    required = {"Open", "Close"}
    for symbol, frame in data_by_symbol.items():
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{symbol} eksik kolonlar: {sorted(missing)}")
        scored = _score_frame(frame).dropna(subset=["Open", "Close"])
        if not scored.empty:
            prepared[symbol.upper()] = scored

    if not prepared:
        empty_curve = pd.DataFrame(columns=["Equity", "Cash", "Holdings", "Exposure"])
        metrics = PortfolioMetrics(initial_cash, initial_cash, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0.0, 0.0, 0.0)
        return PortfolioBacktestResult(metrics, empty_curve, pd.DataFrame(), pd.DataFrame())

    all_dates = sorted(set().union(*(set(frame.index) for frame in prepared.values())))
    dates = pd.DatetimeIndex(all_dates)
    if len(dates) < 2:
        raise ValueError("Portfoy backtest icin en az 2 ortak piyasa tarihi gerekli")

    close_marks = {
        symbol: frame["Close"].reindex(dates).ffill()
        for symbol, frame in prepared.items()
    }

    fee_rate = fee_bps / 10_000
    slip_rate = slippage_bps / 10_000
    cash = float(initial_cash)
    positions: dict[str, int] = {}
    pending_targets: list[str] | None = None
    pending_signal_date: pd.Timestamp | None = None

    equity_rows: list[dict[str, object]] = []
    transaction_rows: list[dict[str, object]] = []
    selection_rows: list[dict[str, object]] = []
    rebalance_count = 0
    traded_notional = 0.0
    exposed_days = 0
    holdings_sum = 0

    for i, date in enumerate(dates):
        date = pd.Timestamp(date)

        # Execute yesterday's/last signal-date ranking at today's open.
        if pending_targets is not None:
            executable_targets = [
                s for s in pending_targets
                if date in prepared[s].index and pd.notna(prepared[s].at[date, "Open"])
            ]

            # Mark current equity using today's open where available, otherwise last close.
            open_mark: dict[str, float] = {}
            for symbol in set(positions) | set(executable_targets):
                if symbol in prepared and date in prepared[symbol].index and pd.notna(prepared[symbol].at[date, "Open"]):
                    open_mark[symbol] = float(prepared[symbol].at[date, "Open"])
                else:
                    mark = close_marks.get(symbol, pd.Series(dtype=float)).get(date, np.nan)
                    if pd.notna(mark):
                        open_mark[symbol] = float(mark)

            pretrade_equity = cash + sum(shares * open_mark.get(symbol, 0.0) for symbol, shares in positions.items())
            target_value = pretrade_equity / len(executable_targets) if executable_targets else 0.0

            desired: dict[str, int] = {}
            for symbol in executable_targets:
                raw_open = float(prepared[symbol].at[date, "Open"])
                buy_price = raw_open * (1 + slip_rate)
                desired[symbol] = max(0, floor(target_value / (buy_price * (1 + fee_rate))))

            # Sell removals/reductions first.
            for symbol in list(positions):
                current = positions.get(symbol, 0)
                target_shares = desired.get(symbol, 0)
                if current <= target_shares:
                    continue
                if symbol not in prepared or date not in prepared[symbol].index or pd.isna(prepared[symbol].at[date, "Open"]):
                    continue
                qty = current - target_shares
                raw_open = float(prepared[symbol].at[date, "Open"])
                price = raw_open * (1 - slip_rate)
                notional = price * qty
                fee = notional * fee_rate
                cash += notional - fee
                traded_notional += notional
                positions[symbol] = target_shares
                if positions[symbol] == 0:
                    positions.pop(symbol, None)
                transaction_rows.append({
                    "date": date, "signal_date": pending_signal_date, "symbol": symbol,
                    "side": "SELL", "shares": qty, "price": price,
                    "notional": notional, "fee": fee,
                })

            # Buy additions, capped by remaining cash.
            for symbol in executable_targets:
                current = positions.get(symbol, 0)
                target_shares = desired.get(symbol, 0)
                if target_shares <= current:
                    continue
                raw_open = float(prepared[symbol].at[date, "Open"])
                price = raw_open * (1 + slip_rate)
                max_affordable = floor(cash / (price * (1 + fee_rate)))
                qty = max(0, min(target_shares - current, max_affordable))
                if qty == 0:
                    continue
                notional = price * qty
                fee = notional * fee_rate
                cash -= notional + fee
                traded_notional += notional
                positions[symbol] = current + qty
                transaction_rows.append({
                    "date": date, "signal_date": pending_signal_date, "symbol": symbol,
                    "side": "BUY", "shares": qty, "price": price,
                    "notional": notional, "fee": fee,
                })

            rebalance_count += 1
            pending_targets = None
            pending_signal_date = None

        # End-of-day mark to market.
        position_value = 0.0
        valid_positions = 0
        for symbol, shares in positions.items():
            mark = close_marks[symbol].get(date, np.nan)
            if pd.notna(mark):
                position_value += shares * float(mark)
                valid_positions += 1
        equity = cash + position_value
        if positions:
            exposed_days += 1
        holdings_sum += len(positions)
        equity_rows.append({
            "Date": date,
            "Equity": equity,
            "Cash": cash,
            "Holdings": len(positions),
            "Exposure": position_value / equity if equity > 0 else 0.0,
        })

        # Observe cross-sectional scores at close and queue next-open rebalance.
        if i < len(dates) - 1 and i % rebalance_days == 0:
            candidates: list[tuple[str, float]] = []
            for symbol, frame in prepared.items():
                if date not in frame.index:
                    continue
                score = frame.at[date, "SETUP_SCORE"]
                if pd.notna(score) and float(score) >= min_score:
                    candidates.append((symbol, float(score)))
            candidates.sort(key=lambda x: (-x[1], x[0]))
            selected = candidates[:top_n]
            pending_targets = [s for s, _ in selected]
            pending_signal_date = date
            for rank, (symbol, score) in enumerate(selected, start=1):
                selection_rows.append({
                    "signal_date": date,
                    "rank": rank,
                    "symbol": symbol,
                    "setup_score": score,
                })

    curve = pd.DataFrame(equity_rows).set_index("Date")
    tx = pd.DataFrame(transaction_rows)
    selections = pd.DataFrame(selection_rows)

    total_return, cagr, max_dd, sharpe, sortino = _ratio_metrics(curve["Equity"])
    avg_equity = float(curve["Equity"].mean()) if not curve.empty else initial_cash
    metrics = PortfolioMetrics(
        initial_cash=float(initial_cash),
        final_equity=float(curve["Equity"].iloc[-1]),
        total_return_pct=total_return,
        cagr_pct=cagr,
        max_drawdown_pct=max_dd,
        sharpe=sharpe,
        sortino=sortino,
        rebalances=rebalance_count,
        transactions=len(tx),
        cumulative_turnover_pct=(traded_notional / avg_equity * 100) if avg_equity > 0 else 0.0,
        avg_holdings=(holdings_sum / len(curve)) if len(curve) else 0.0,
        exposure_pct=(exposed_days / len(curve) * 100) if len(curve) else 0.0,
    )
    return PortfolioBacktestResult(metrics, curve, tx, selections)
