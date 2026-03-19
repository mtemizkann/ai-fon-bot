from __future__ import annotations

from .models import BotConfig, Portfolio


def update_peak(portfolio: Portfolio) -> None:
    current = portfolio.total_value()
    portfolio.peak_value = max(portfolio.peak_value, current)


def current_drawdown(portfolio: Portfolio) -> float:
    if portfolio.peak_value <= 0:
        return 0.0
    return max(0.0, 1.0 - (portfolio.total_value() / portfolio.peak_value))


def risk_halt_triggered(portfolio: Portfolio, config: BotConfig) -> bool:
    return current_drawdown(portfolio) >= config.portfolio_drawdown_stop
