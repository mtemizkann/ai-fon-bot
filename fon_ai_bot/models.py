from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class FundRule:
    code: str
    name: str
    category: str
    min_weight: float
    max_weight: float


@dataclass(slots=True)
class StrategyConfig:
    lookback_short: int
    lookback_medium: int
    lookback_drawdown: int
    min_history_days: int
    weight_short: float
    weight_medium: float
    volatility_penalty: float


@dataclass(slots=True)
class BotConfig:
    starting_cash: float
    cash_buffer_pct: float
    max_position_pct: float
    max_funds: int
    portfolio_drawdown_stop: float
    rebalance_threshold: float
    strategy: StrategyConfig
    universe: list[FundRule]
    source: str = "csv"


@dataclass(slots=True)
class FundSnapshot:
    code: str
    as_of: date
    price: float
    ret_short: float
    ret_medium: float
    volatility: float
    drawdown: float
    score: float
    category: str = ""
    name: str = ""
    risk_value: float = 0.0
    ret_3m: float = 0.0
    ret_6m: float = 0.0
    source: str = ""


@dataclass(slots=True)
class Position:
    code: str
    units: float
    last_price: float

    @property
    def market_value(self) -> float:
        return self.units * self.last_price


@dataclass(slots=True)
class Portfolio:
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    peak_value: float = 0.0
    last_report_hash: str = ""
    order_history: list[dict] = field(default_factory=list)
    performance_history: list[dict] = field(default_factory=list)
    snapshot_cache: dict[str, dict] = field(default_factory=dict)

    def total_value(self) -> float:
        positions_value = sum(position.market_value for position in self.positions.values())
        return self.cash + positions_value

    def to_dict(self) -> dict:
        return {
            "cash": self.cash,
            "peak_value": self.peak_value,
            "last_report_hash": self.last_report_hash,
            "order_history": self.order_history,
            "performance_history": self.performance_history,
            "snapshot_cache": self.snapshot_cache,
            "positions": {
                code: {
                    "code": position.code,
                    "units": position.units,
                    "last_price": position.last_price,
                }
                for code, position in self.positions.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Portfolio":
        positions = {
            code: Position(
                code=item["code"],
                units=float(item["units"]),
                last_price=float(item["last_price"]),
            )
            for code, item in payload.get("positions", {}).items()
        }
        return cls(
            cash=float(payload["cash"]),
            peak_value=float(payload.get("peak_value", 0.0)),
            last_report_hash=str(payload.get("last_report_hash", "")),
            order_history=list(payload.get("order_history", [])),
            performance_history=list(payload.get("performance_history", [])),
            snapshot_cache=dict(payload.get("snapshot_cache", {})),
            positions=positions,
        )


@dataclass(slots=True)
class Order:
    code: str
    action: str
    amount_try: float
    reason: str


@dataclass(slots=True)
class PlaybookItem:
    code: str
    action: str
    amount_try: float
    entry_timing: str
    min_hold_days: int
    review_on: date
    exit_rule: str
    why: str


@dataclass(slots=True)
class DecisionReport:
    as_of: date
    snapshots: list[FundSnapshot]
    target_weights: dict[str, float]
    orders: list[Order]
    portfolio_value: float
    current_drawdown: float
    halted: bool
    playbook: list[PlaybookItem] = field(default_factory=list)
    avoid_codes: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
