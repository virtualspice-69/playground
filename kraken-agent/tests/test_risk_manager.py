import json
import os

import pytest

from src.risk_manager import RiskConfig, RiskManager, STATE_DIR, STATE_FILE


@pytest.fixture(autouse=True)
def clean_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    yield
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


def _manager(**overrides):
    defaults = dict(
        max_daily_drawdown_pct=2.0,
        max_position_size_pct=5.0,
        max_concurrent_positions=3,
        stop_loss_pct=1.5,
        take_profit_pct=3.0,
    )
    defaults.update(overrides)
    return RiskManager(RiskConfig(**defaults))


def test_sync_day_sets_baseline():
    rm = _manager()
    rm.sync_day(10000.0)
    assert rm.current_drawdown_pct(10000.0) == 0.0
    assert rm.current_drawdown_pct(9900.0) == pytest.approx(1.0)


def test_halts_when_drawdown_exceeds_limit():
    rm = _manager(max_daily_drawdown_pct=2.0)
    rm.sync_day(10000.0)
    assert rm.check_and_update_halt(9950.0) is False  # 0.5% dd
    assert rm.check_and_update_halt(9750.0) is True  # 2.5% dd


def test_can_open_new_position_respects_halt_and_concurrency():
    rm = _manager(max_daily_drawdown_pct=2.0, max_concurrent_positions=1)
    rm.sync_day(10000.0)
    assert rm.can_open_new_position(0, 10000.0) is True
    assert rm.can_open_new_position(1, 10000.0) is False  # concurrency limit
    assert rm.can_open_new_position(0, 9700.0) is False  # drawdown halt


def test_position_size_scales_down_with_volatility():
    rm = _manager(max_position_size_pct=5.0)
    low_vol = rm.position_size_base_units(10000.0, price=100.0, atr_pct=0.005)
    high_vol = rm.position_size_base_units(10000.0, price=100.0, atr_pct=0.05)
    assert high_vol < low_vol


def test_stop_and_take_profit_prices_long():
    rm = _manager(stop_loss_pct=1.5, take_profit_pct=3.0)
    assert rm.stop_loss_price(100.0, "long") == pytest.approx(98.5)
    assert rm.take_profit_price(100.0, "long") == pytest.approx(103.0)


def test_stop_and_take_profit_prices_short():
    rm = _manager(stop_loss_pct=1.5, take_profit_pct=3.0)
    assert rm.stop_loss_price(100.0, "short") == pytest.approx(101.5)
    assert rm.take_profit_price(100.0, "short") == pytest.approx(97.0)


def test_state_persists_across_instances():
    rm1 = _manager()
    rm1.sync_day(10000.0)
    rm1.check_and_update_halt(9700.0)

    rm2 = _manager()
    assert rm2.current_drawdown_pct(9700.0) == pytest.approx(3.0)
    assert rm2.check_and_update_halt(9700.0) is True
