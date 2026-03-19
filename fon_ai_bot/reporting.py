from __future__ import annotations

import hashlib
import json

from .models import DecisionReport, Portfolio


def format_report(report: DecisionReport, portfolio: Portfolio) -> str:
    status = "AKTIF" if report.halted else "Normal"
    lines = [
        f"AI Fon Bot Raporu | {report.as_of.isoformat()}",
        f"Portfoy: {report.portfolio_value:,.2f} TL",
        f"Dusukten Tepe Kaybi: %{report.current_drawdown * 100:.2f}",
        f"Risk Freni: {status}",
        "",
        "Hedef Agirliklar:",
    ]

    for code, weight in sorted(report.target_weights.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"- {code}: %{weight * 100:.2f}")

    lines.append("")
    lines.append("En Guclu Fonlar:")
    for snapshot in report.snapshots[:3]:
        lines.append(
            f"- {snapshot.code} | skor {snapshot.score:.4f} | "
            f"30g {snapshot.ret_short:.2%} | 90g {snapshot.ret_medium:.2%}"
        )

    lines.append("")
    if report.orders:
        lines.append("Bugunku Eylem:")
        for order in report.orders:
            lines.append(f"- {order.action} {order.code}: {order.amount_try:,.2f} TL")
    else:
        lines.append("Bugunku Eylem:")
        lines.append("- Islem yok, mevcut dagilim korunuyor.")

    lines.append("")
    lines.append("Pozisyonlar:")
    if portfolio.positions:
        for code, position in sorted(portfolio.positions.items()):
            lines.append(f"- {code}: {position.market_value:,.2f} TL")
    else:
        lines.append("- Henuz pozisyon yok")

    return "\n".join(lines)


def report_hash(report: DecisionReport) -> str:
    payload = {
        "date": report.as_of.isoformat(),
        "halted": report.halted,
        "orders": [(order.code, order.action, round(order.amount_try, 2)) for order in report.orders],
        "weights": sorted((code, round(weight, 4)) for code, weight in report.target_weights.items()),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
