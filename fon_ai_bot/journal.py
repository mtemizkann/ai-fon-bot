from __future__ import annotations

from .models import DecisionReport, Portfolio


def record_portfolio_snapshot(portfolio: Portfolio, report: DecisionReport) -> None:
    entry = {
        "date": report.as_of.isoformat(),
        "portfolio_value": round(portfolio.total_value(), 2),
        "drawdown": round(report.current_drawdown, 6),
        "halted": report.halted,
        "weights": {code: round(weight, 4) for code, weight in report.target_weights.items()},
    }
    history = [item for item in portfolio.performance_history if item.get("date") != entry["date"]]
    history.append(entry)
    portfolio.performance_history = history[-120:]


def record_orders(portfolio: Portfolio, report: DecisionReport) -> None:
    if not report.orders:
        return
    for order in report.orders:
        portfolio.order_history.append(
            {
                "date": report.as_of.isoformat(),
                "code": order.code,
                "action": order.action,
                "amount_try": round(order.amount_try, 2),
                "reason": order.reason,
            }
        )
    portfolio.order_history = portfolio.order_history[-200:]


def summarize_performance(portfolio: Portfolio) -> tuple[str, str]:
    if len(portfolio.performance_history) < 2:
        return ("yeni portfoy", "yeterli gecmis yok")

    latest = portfolio.performance_history[-1]
    previous = portfolio.performance_history[-2]
    daily_change = latest["portfolio_value"] - previous["portfolio_value"]
    start = portfolio.performance_history[0]["portfolio_value"]
    total_change_pct = ((latest["portfolio_value"] / start) - 1.0) if start else 0.0
    return (f"gunluk fark {daily_change:,.2f} TL", f"toplam getiri %{total_change_pct * 100:.2f}")
