from __future__ import annotations

import html
import re
import ssl
import subprocess
import urllib.parse
import urllib.request
from datetime import date
from urllib.error import URLError

from .models import BotConfig, FundRule, FundSnapshot, Portfolio


def _parse_tr_number(raw: str) -> float:
    cleaned = raw.strip().replace("%", "").replace(".", "").replace(",", ".")
    cleaned = cleaned.replace("\xa0", "").replace(" ", "")
    if not cleaned:
        return 0.0
    return float(cleaned)


def _extract(pattern: str, content: str, label: str) -> str:
    match = re.search(pattern, content, re.S)
    if not match:
        raise ValueError(f"TEFAS sayfasinda alan bulunamadi: {label}")
    return html.unescape(match.group(1)).strip()


def fetch_fund_page(code: str) -> str:
    url = "https://www.tefas.gov.tr/FonAnaliz.aspx?" + urllib.parse.urlencode({"FonKod": code})
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", "ignore")
    except URLError:
        insecure_context = ssl.create_default_context()
        insecure_context.check_hostname = False
        insecure_context.verify_mode = ssl.CERT_NONE
        try:
            with urllib.request.urlopen(request, timeout=30, context=insecure_context) as response:
                return response.read().decode("utf-8", "ignore")
        except URLError:
            pass

    try:
        result = subprocess.run(
            [
                "curl",
                "-fsSL",
                "--retry",
                "3",
                "--retry-delay",
                "2",
                "-A",
                "Mozilla/5.0",
                url,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"sayfa cekilemedi: {exc}") from exc


def fetch_snapshot(rule: FundRule) -> FundSnapshot:
    page = fetch_fund_page(rule.code)

    name = _extract(
        r'LabelFund">([^<]+)</span>',
        page,
        "fon adi",
    )
    price = _parse_tr_number(
        _extract(r"Son Fiyat \(TL\)<br />\s*<br />\s*<span>([^<]+)</span>", page, "son fiyat")
    )
    ret_1m = _parse_tr_number(
        _extract(r"Son 1 Ay Getirisi<br />\s*<span[^>]*>([^<]+)</span>", page, "1 ay getirisi")
    )
    ret_3m = _parse_tr_number(
        _extract(r"Son 3 Ay Getirisi<br />\s*<span[^>]*>([^<]+)</span>", page, "3 ay getirisi")
    )
    ret_6m = _parse_tr_number(
        _extract(r"Son 6 Ay Getirisi<br />\s*<span[^>]*>([^<]+)</span>", page, "6 ay getirisi")
    )
    ret_1y = _parse_tr_number(
        _extract(r"Son 1 Yıl Getirisi<br />\s*<span[^>]*>([^<]+)</span>", page, "1 yil getirisi")
    )
    risk_value = _parse_tr_number(
        _extract(r"Fonun Risk Değeri</td><td class=\"fund-profile-item\">([^<]+)</td>", page, "risk degeri")
    )

    # TEFAS sayfasinda volatilite ve tarihsel drawdown alanlari hazir olmadigi icin,
    # skoru resmi 1/3/6/12 ay getirileri ve risk degeriyle kuruyoruz.
    score = (
        ret_1m * 0.10
        + ret_3m * 0.20
        + ret_6m * 0.30
        + ret_1y * 0.40
        - risk_value * 1.25
    ) / 100.0

    negative_count = sum(1 for item in (ret_1m, ret_3m, ret_6m) if item < 0)
    drawdown_proxy = max(0.0, negative_count * 0.04)
    volatility_proxy = max(0.0, risk_value / 7.0)

    return FundSnapshot(
        code=rule.code,
        as_of=date.today(),
        price=price,
        ret_short=ret_1m / 100.0,
        ret_medium=ret_1y / 100.0,
        volatility=volatility_proxy,
        drawdown=drawdown_proxy,
        score=score,
        category=rule.category,
        name=name,
        risk_value=risk_value,
        ret_3m=ret_3m / 100.0,
        ret_6m=ret_6m / 100.0,
        source="tefas",
    )


def _snapshot_to_cache(snapshot: FundSnapshot) -> dict:
    return {
        "code": snapshot.code,
        "as_of": snapshot.as_of.isoformat(),
        "price": snapshot.price,
        "ret_short": snapshot.ret_short,
        "ret_medium": snapshot.ret_medium,
        "volatility": snapshot.volatility,
        "drawdown": snapshot.drawdown,
        "score": snapshot.score,
        "category": snapshot.category,
        "name": snapshot.name,
        "risk_value": snapshot.risk_value,
        "ret_3m": snapshot.ret_3m,
        "ret_6m": snapshot.ret_6m,
        "source": snapshot.source,
    }


def _snapshot_from_cache(payload: dict) -> FundSnapshot:
    return FundSnapshot(
        code=payload["code"],
        as_of=date.fromisoformat(payload["as_of"]),
        price=float(payload["price"]),
        ret_short=float(payload["ret_short"]),
        ret_medium=float(payload["ret_medium"]),
        volatility=float(payload["volatility"]),
        drawdown=float(payload["drawdown"]),
        score=float(payload["score"]),
        category=str(payload.get("category", "")),
        name=str(payload.get("name", "")),
        risk_value=float(payload.get("risk_value", 0.0)),
        ret_3m=float(payload.get("ret_3m", 0.0)),
        ret_6m=float(payload.get("ret_6m", 0.0)),
        source=str(payload.get("source", "cache")),
    )


def load_tefas_snapshots(config: BotConfig, portfolio: Portfolio | None = None) -> tuple[list[FundSnapshot], list[str]]:
    snapshots: list[FundSnapshot] = []
    errors: list[str] = []
    for rule in config.universe:
        try:
            snapshot = fetch_snapshot(rule)
            snapshots.append(snapshot)
            if portfolio is not None:
                portfolio.snapshot_cache[rule.code] = _snapshot_to_cache(snapshot)
        except Exception as exc:
            cache_payload = portfolio.snapshot_cache.get(rule.code) if portfolio is not None else None
            if cache_payload:
                snapshots.append(_snapshot_from_cache(cache_payload))
                errors.append(f"{rule.code}: canli veri yerine cache kullanildi")
                continue
            errors.append(f"{rule.code}: {exc}")
            continue

    if not snapshots:
        joined = "; ".join(errors) if errors else "bilinmeyen hata"
        raise ValueError(f"TEFAS verisi alinamadi: {joined}")
    return snapshots, errors
