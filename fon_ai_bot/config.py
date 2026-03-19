from __future__ import annotations

import tomllib
from pathlib import Path

from .models import BotConfig, FundRule, StrategyConfig


def load_config(path: str | Path) -> BotConfig:
    with Path(path).open("rb") as handle:
        raw = tomllib.load(handle)

    strategy_raw = raw["strategy"]
    strategy = StrategyConfig(
        lookback_short=int(strategy_raw["lookback_short"]),
        lookback_medium=int(strategy_raw["lookback_medium"]),
        lookback_drawdown=int(strategy_raw["lookback_drawdown"]),
        min_history_days=int(strategy_raw["min_history_days"]),
        weight_short=float(strategy_raw["weight_short"]),
        weight_medium=float(strategy_raw["weight_medium"]),
        volatility_penalty=float(strategy_raw["volatility_penalty"]),
    )

    universe = [
        FundRule(
            code=item["code"],
            name=item["name"],
            category=item["category"],
            min_weight=float(item["min_weight"]),
            max_weight=float(item["max_weight"]),
        )
        for item in raw["universe"]
    ]

    return BotConfig(
        starting_cash=float(raw["starting_cash"]),
        cash_buffer_pct=float(raw["cash_buffer_pct"]),
        max_position_pct=float(raw["max_position_pct"]),
        max_funds=int(raw["max_funds"]),
        portfolio_drawdown_stop=float(raw["portfolio_drawdown_stop"]),
        rebalance_threshold=float(raw["rebalance_threshold"]),
        strategy=strategy,
        universe=universe,
    )
