from __future__ import annotations

import hashlib
import json

from .journal import summarize_performance
from .models import DecisionReport, Portfolio


def _fmt_pct(value: float) -> str:
    return f"%{value * 100:.2f}"


def format_report(report: DecisionReport, portfolio: Portfolio) -> str:
    status = "AKTIF" if report.halted else "Normal"
    action_title = "Bugun Yapilacaklar"
    if report.halted:
        action_title = "Acil Risk Modu"
    lines = [
        f"AI Fon Bot | {report.as_of.isoformat()}",
        f"Portfoy Degeri: {report.portfolio_value:,.2f} TL",
        f"Portfoy Dususu: {_fmt_pct(report.current_drawdown)}",
        f"Risk Freni: {status}",
        "",
        action_title + ":",
    ]

    if report.orders:
        for order in report.orders:
            verb = {"BUY": "AL", "SELL": "SAT"}.get(order.action, order.action)
            lines.append(f"- {verb} {order.code}: {order.amount_try:,.2f} TL")
    else:
        lines.append("- Islem yok, mevcut dagilim korunuyor.")

    lines.append("")
    lines.append("Hedef Dagilim:")
    for code, weight in sorted(report.target_weights.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"- {code}: {_fmt_pct(weight)}")

    lines.append("")
    lines.append("En Guclu Fonlar:")
    for snapshot in report.snapshots[:3]:
        lines.append(
            f"- {snapshot.code}: skor {snapshot.score:.3f} | "
            f"1A {snapshot.ret_short:.2%} | 3A {snapshot.ret_3m:.2%} | 1Y {snapshot.ret_medium:.2%}"
        )

    lines.append("")
    perf_day, perf_total = summarize_performance(portfolio)
    lines.append("Performans:")
    lines.append(f"- {perf_day}")
    lines.append(f"- {perf_total}")

    if report.insights:
        lines.append("")
        lines.append("Yorum:")
        for item in report.insights:
            lines.append(f"- {item}")

    if report.warnings:
        lines.append("")
        lines.append("Uyarilar:")
        for item in report.warnings:
            lines.append(f"- {item}")

    lines.append("")
    lines.append("Mevcut Pozisyonlar:")
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
        "warnings": report.warnings,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
