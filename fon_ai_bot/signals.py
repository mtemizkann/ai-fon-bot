from __future__ import annotations

from math import sqrt
from statistics import pstdev

from .models import BotConfig, FundRule, FundSnapshot


def _return_over_window(prices: list[float], lookback: int) -> float:
    if len(prices) <= lookback:
        raise ValueError("Not enough price history for lookback window")
    return (prices[-1] / prices[-1 - lookback]) - 1.0


def _daily_returns(prices: list[float]) -> list[float]:
    returns: list[float] = []
    for previous, current in zip(prices, prices[1:]):
        returns.append((current / previous) - 1.0)
    return returns


def _max_drawdown(prices: list[float], lookback: int) -> float:
    window = prices[-lookback:]
    peak = window[0]
    worst = 0.0
    for price in window:
        peak = max(peak, price)
        drawdown = (price / peak) - 1.0
        worst = min(worst, drawdown)
    return abs(worst)


def build_snapshot(rule: FundRule, history: list[tuple], config: BotConfig) -> FundSnapshot:
    dates = [row[0] for row in history]
    prices = [row[1] for row in history]
    if len(prices) < config.strategy.min_history_days:
        raise ValueError(f"{rule.code} icin yeterli veri yok")

    returns = _daily_returns(prices)
    volatility = pstdev(returns[-config.strategy.lookback_short :]) * sqrt(252)
    ret_short = _return_over_window(prices, config.strategy.lookback_short)
    ret_medium = _return_over_window(prices, config.strategy.lookback_medium)
    drawdown = _max_drawdown(prices, config.strategy.lookback_drawdown)
    score = (
        ret_short * config.strategy.weight_short
        + ret_medium * config.strategy.weight_medium
        - volatility * config.strategy.volatility_penalty
        - drawdown * 0.35
    )
    return FundSnapshot(
        code=rule.code,
        as_of=dates[-1],
        price=prices[-1],
        ret_short=ret_short,
        ret_medium=ret_medium,
        volatility=volatility,
        drawdown=drawdown,
        score=score,
    )
