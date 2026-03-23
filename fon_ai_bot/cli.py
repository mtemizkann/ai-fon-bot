from __future__ import annotations

import argparse

from .broker import PaperBroker
from .config import load_config
from .data import load_price_history
from .engine import AllocationEngine
from .journal import record_orders, record_portfolio_snapshot
from .reporting import format_report, report_hash
from .risk import update_peak
from .state import load_or_create_portfolio, save_portfolio
from .tefas import load_tefas_snapshots
from .telegram_notifier import TelegramNotifier


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Fon Bot")
    parser.add_argument("--prices", help="CSV fiyat dosyasi")
    parser.add_argument("--config", required=True, help="TOML config dosyasi")
    parser.add_argument(
        "--broker",
        default="advisory",
        choices=["paper", "advisory"],
        help="Broker tipi",
    )
    parser.add_argument(
        "--state",
        required=True,
        help="Portfoy durum dosyasi (json)",
    )
    parser.add_argument(
        "--notify",
        default="none",
        choices=["none", "telegram"],
        help="Rapor bildirim tipi",
    )
    parser.add_argument(
        "--force-notify",
        action="store_true",
        help="Ayni rapor olsa bile bildirimi zorla gonder",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    notifier = TelegramNotifier() if args.notify == "telegram" else None

    portfolio = load_or_create_portfolio(args.state, config)
    update_peak(portfolio)

    engine = AllocationEngine(config)
    if config.source == "tefas":
        try:
            snapshots, tefas_errors = load_tefas_snapshots(config, portfolio)
            report = engine.evaluate_snapshots(snapshots, portfolio)
            if tefas_errors:
                report.warnings.extend(tefas_errors[:5])
        except Exception as exc:
            message = (
                "AI Fon Bot Raporu\n"
                "TEFAS verisi bugun alinamadi.\n"
                f"Sebep: {exc}\n"
                "Bugun islem yapilmadi, mevcut portfoy korunuyor."
            )
            print(message)
            if notifier:
                notifier.send(message)
            save_portfolio(args.state, portfolio)
            return
    else:
        if not args.prices:
            raise ValueError("CSV kaynak kullanimi icin --prices zorunludur")
        prices = load_price_history(args.prices)
        report = engine.evaluate(prices, portfolio)

    print(f"Tarih: {report.as_of.isoformat()}")
    print(f"Portfoy Degeri: {report.portfolio_value:,.2f} TL")
    print(f"Portfoy Dususu: %{report.current_drawdown * 100:.2f}")
    print(f"Risk Freni: {'AKTIF' if report.halted else 'Normal'}")
    print("")
    print("Fon Skorlari:")
    for snapshot in report.snapshots:
        print(
            f"- {snapshot.code}: skor={snapshot.score:.4f} "
            f"kisa={snapshot.ret_short:.2%} orta={snapshot.ret_medium:.2%} "
            f"vol={snapshot.volatility:.2%} dd={snapshot.drawdown:.2%}"
        )

    print("")
    print("Hedef Agirliklar:")
    for code, weight in sorted(report.target_weights.items(), key=lambda item: item[1], reverse=True):
        print(f"- {code}: %{weight * 100:.2f}")

    if not report.orders:
        print("")
        print("Islem yok. Portfoy mevcut halde korunuyor.")
    else:
        print("")
        print("Olusan Emirler:")
        for order in report.orders:
            print(f"- {order.action} {order.code}: {order.amount_try:,.2f} TL | {order.reason}")

    if args.broker == "paper" and report.orders:
        broker = PaperBroker()
        latest_prices = {snapshot.code: snapshot.price for snapshot in report.snapshots}
        broker.execute(portfolio, latest_prices, report.orders)
        record_orders(portfolio, report)
        print("")
        print("Paper Broker Sonrasi:")
        print(f"- Nakit: {portfolio.cash:,.2f} TL")
        for code, position in sorted(portfolio.positions.items()):
            print(
                f"- {code}: birim={position.units:.6f} "
                f"fiyat={position.last_price:.4f} deger={position.market_value:,.2f} TL"
            )
        print(f"- Toplam: {portfolio.total_value():,.2f} TL")
    elif args.broker == "advisory":
        print("")
        print("Advisory Modu:")
        print("- Emirler sadece oneridir; portfoy state'i otomatik islenmedi.")

    record_portfolio_snapshot(portfolio, report)

    if args.notify == "telegram":
        message = format_report(report, portfolio)
        signature = report_hash(report)
        if args.force_notify or signature != portfolio.last_report_hash:
            assert notifier is not None
            notifier.send(message)
            portfolio.last_report_hash = signature
            print("")
            print("Telegram bildirimi gonderildi.")
        else:
            print("")
            print("Telegram bildirimi atlanadi; rapor degismedi.")

    save_portfolio(args.state, portfolio)


if __name__ == "__main__":
    main()
