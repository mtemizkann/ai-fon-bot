from __future__ import annotations

import json
from pathlib import Path

from .models import BotConfig, Portfolio


def load_or_create_portfolio(path: str | Path, config: BotConfig) -> Portfolio:
    state_path = Path(path)
    if not state_path.exists():
        return Portfolio(
            cash=config.starting_cash,
            peak_value=config.starting_cash,
            last_report_hash="",
        )

    with state_path.open("r", encoding="utf-8") as handle:
        return Portfolio.from_dict(json.load(handle))


def save_portfolio(path: str | Path, portfolio: Portfolio) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(portfolio.to_dict(), handle, indent=2)
