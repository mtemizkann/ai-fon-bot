from __future__ import annotations

from .models import Order, Portfolio, Position


class PaperBroker:
    def execute(self, portfolio: Portfolio, prices: dict[str, float], orders: list[Order]) -> None:
        for order in orders:
            price = prices[order.code]
            if order.action == "BUY":
                budget = min(order.amount_try, portfolio.cash)
                if budget <= 0:
                    continue
                units = budget / price
                position = portfolio.positions.get(order.code)
                if position:
                    position.units += units
                    position.last_price = price
                else:
                    portfolio.positions[order.code] = Position(
                        code=order.code,
                        units=units,
                        last_price=price,
                    )
                portfolio.cash -= budget
            elif order.action == "SELL":
                position = portfolio.positions.get(order.code)
                if not position:
                    continue
                gross = min(order.amount_try, position.market_value)
                units = gross / price
                position.units -= units
                position.last_price = price
                portfolio.cash += gross
                if position.units <= 1e-8:
                    del portfolio.positions[order.code]

        for code, position in list(portfolio.positions.items()):
            if code in prices:
                position.last_price = prices[code]
