import pytest

from app.risk.position_sizing import position_size


def test_position_size_basic():
    result = position_size(100_000, 0.5, 100, 95)
    assert result["risk_budget"] == 500
    assert result["risk_per_share"] == 5
    assert result["shares"] == 100
    assert result["position_value"] == 10_000
    assert result["portfolio_allocation_pct"] == 10


def test_position_size_rejects_zero_stop_distance():
    with pytest.raises(ValueError):
        position_size(100_000, 0.5, 100, 100)
