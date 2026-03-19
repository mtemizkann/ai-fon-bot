from __future__ import annotations

from .models import BotConfig, DecisionReport, FundSnapshot, Order, Portfolio
from .risk import current_drawdown, risk_halt_triggered, update_peak
from .signals import build_snapshot


class AllocationEngine:
    def __init__(self, config: BotConfig) -> None:
        self.config = config

    def evaluate(self, price_history: dict[str, list[tuple]], portfolio: Portfolio) -> DecisionReport:
        snapshots: list[FundSnapshot] = []

        for rule in self.config.universe:
            if rule.code not in price_history:
                continue
            snapshots.append(build_snapshot(rule, price_history[rule.code], self.config))

        return self.evaluate_snapshots(snapshots, portfolio)

    def evaluate_snapshots(
        self,
        snapshots: list[FundSnapshot],
        portfolio: Portfolio,
    ) -> DecisionReport:
        universe_map = {rule.code: rule for rule in self.config.universe}

        if not snapshots:
            raise ValueError("Analiz icin uygun fon verisi bulunamadi")

        latest_prices = {item.code: item.price for item in snapshots}
        for position in portfolio.positions.values():
            if position.code in latest_prices:
                position.last_price = latest_prices[position.code]

        update_peak(portfolio)
        halted = risk_halt_triggered(portfolio, self.config)
        drawdown_now = current_drawdown(portfolio)

        target_weights = self._build_target_weights(snapshots, halted)
        orders = self._rebalance_orders(portfolio, latest_prices, target_weights, universe_map)

        return DecisionReport(
            as_of=max(item.as_of for item in snapshots),
            snapshots=sorted(snapshots, key=lambda item: item.score, reverse=True),
            target_weights=target_weights,
            orders=orders,
            portfolio_value=portfolio.total_value(),
            current_drawdown=drawdown_now,
            halted=halted,
        )

    def _build_target_weights(
        self, snapshots: list[FundSnapshot], halted: bool
    ) -> dict[str, float]:
        cash_code = next(
            (rule.code for rule in self.config.universe if rule.category == "cash"),
            None,
        )
        if halted:
            return {cash_code: 1.0} if cash_code else {}

        eligible = [
            snapshot
            for snapshot in snapshots
            if snapshot.ret_short > 0 and snapshot.ret_medium > 0 and snapshot.drawdown < 0.12
        ]

        eligible.sort(key=lambda item: item.score, reverse=True)
        selected = eligible[: self.config.max_funds]

        target_weights: dict[str, float] = {}
        reserved_cash = self.config.cash_buffer_pct
        tradable_budget = max(0.0, 1.0 - reserved_cash)

        if not selected:
            return {cash_code: 1.0} if cash_code else {}

        raw_total = sum(max(item.score, 0.0) for item in selected)
        if raw_total <= 0:
            return {cash_code: 1.0} if cash_code else {}

        for snapshot in selected:
            rule = next(rule for rule in self.config.universe if rule.code == snapshot.code)
            weight = tradable_budget * (max(snapshot.score, 0.0) / raw_total)
            weight = min(weight, self.config.max_position_pct, rule.max_weight)
            if weight >= 0.02:
                target_weights[snapshot.code] = weight

        current_sum = sum(target_weights.values())
        leftover = max(0.0, 1.0 - current_sum)
        if cash_code:
            target_weights[cash_code] = target_weights.get(cash_code, 0.0) + leftover
        return target_weights

    def _rebalance_orders(
        self,
        portfolio: Portfolio,
        prices: dict[str, float],
        target_weights: dict[str, float],
        universe_map: dict[str, object],
    ) -> list[Order]:
        total_value = portfolio.total_value()
        current_weights = {
            code: (position.market_value / total_value) if total_value else 0.0
            for code, position in portfolio.positions.items()
        }
        current_weights["CASH"] = (portfolio.cash / total_value) if total_value else 1.0

        orders: list[Order] = []

        for code, position in portfolio.positions.items():
            target = target_weights.get(code, 0.0)
            diff = current_weights.get(code, 0.0) - target
            if diff > self.config.rebalance_threshold:
                orders.append(
                    Order(
                        code=code,
                        action="SELL",
                        amount_try=round(diff * total_value, 2),
                        reason="Target agirligin uzerinde kaldigi icin azalt",
                    )
                )

        simulated_cash = portfolio.cash + sum(
            order.amount_try for order in orders if order.action == "SELL"
        )

        for code, target in target_weights.items():
            if code not in prices:
                continue
            current = current_weights.get(code, 0.0)
            diff = target - current
            if diff > self.config.rebalance_threshold:
                budget = min(round(diff * total_value, 2), simulated_cash)
                if budget <= 0:
                    continue
                orders.append(
                    Order(
                        code=code,
                        action="BUY",
                        amount_try=budget,
                        reason="Skor ve hedef agirlik sinyali nedeniyle al",
                    )
                )
                simulated_cash -= budget
        return orders
