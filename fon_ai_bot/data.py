from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path


PriceSeries = dict[str, list[tuple[date, float]]]


def load_price_history(path: str | Path) -> PriceSeries:
    series: PriceSeries = defaultdict(list)
    with Path(path).open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            series[row["fund_code"]].append(
                (date.fromisoformat(row["date"]), float(row["price"]))
            )

    for values in series.values():
        values.sort(key=lambda item: item[0])
    return dict(series)
