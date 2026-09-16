from __future__ import annotations

import math


def position_size(portfolio_value: float, risk_pct: float, entry: float, stop: float) -> dict:
    if portfolio_value <= 0:
        raise ValueError("portfolio_value pozitif olmali")
    if not (0 < risk_pct <= 100):
        raise ValueError("risk_pct 0 ile 100 arasinda olmali")
    if entry <= 0 or stop <= 0:
        raise ValueError("entry ve stop pozitif olmali")

    risk_per_share = abs(entry - stop)
    if risk_per_share == 0:
        raise ValueError("entry ve stop ayni olamaz")

    risk_budget = portfolio_value * (risk_pct / 100)
    shares = math.floor(risk_budget / risk_per_share)
    position_value = shares * entry

    return {
        "risk_budget": risk_budget,
        "risk_per_share": risk_per_share,
        "shares": shares,
        "position_value": position_value,
        "portfolio_allocation_pct": (position_value / portfolio_value) * 100,
    }
