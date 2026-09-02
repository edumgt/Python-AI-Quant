#!/usr/bin/env python3
"""Build an analysis-ready daily VKOSPI/Korea equity-index data set.

Sources
-------
* VKOSPI: Investing.com public historical-data endpoint (instrument 956761).
* KOSPI and KOSPI 200: Yahoo Finance chart endpoint (^KS11, ^KS200).

The output uses dates on which all three indices have observations.  Run this
script again to refresh the data; it overwrites the CSV in this directory.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OUTPUT = Path(__file__).with_name("vkospi_korea_equity_indices_daily.csv")
VKOSPI_URL = "https://api.investing.com/api/financialdata/historical/956761"
YAHOO_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)


def fetch_json(url: str, params: dict[str, str], headers: dict[str, str]) -> dict:
    request = Request(
        f"{url}?{urlencode(params)}",
        headers={"User-Agent": USER_AGENT, **headers},
    )
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def fetch_vkospi() -> dict[str, dict[str, float]]:
    """Return daily OHLC records keyed by ISO date."""
    payload = fetch_json(
        VKOSPI_URL,
        {
            "start-date": "2011-01-01",
            "end-date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "interval": "P1D",
            "time-frame": "Daily",
        },
        {
            "Referer": "https://www.investing.com/indices/kospi-volatility-historical-data",
            "Origin": "https://www.investing.com",
            "domain-id": "www",
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    return {
        item["rowDateTimestamp"][:10]: {
            "open": float(item["last_open"].replace(",", "")),
            "high": float(item["last_max"].replace(",", "")),
            "low": float(item["last_min"].replace(",", "")),
            "close": float(item["last_close"].replace(",", "")),
        }
        for item in payload["data"]
    }


def fetch_yahoo(symbol: str) -> dict[str, dict[str, float]]:
    payload = fetch_json(
        YAHOO_URL.format(symbol),
        {"period1": "1293840000", "period2": str(int(datetime.now(UTC).timestamp()) + 86_400), "interval": "1d"},
        {},
    )["chart"]["result"][0]
    quote = payload["indicators"]["quote"][0]
    records = {}
    for index, timestamp in enumerate(payload["timestamp"]):
        values = {field: quote[field][index] for field in ("open", "high", "low", "close", "volume")}
        if all(value is not None for value in values.values()):
            records[datetime.fromtimestamp(timestamp, UTC).date().isoformat()] = values
    return records


def pct_change(current: float, previous: float) -> float:
    return (current / previous - 1.0) * 100.0


def sample_std(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def main() -> None:
    vkospi = fetch_vkospi()
    kospi = fetch_yahoo("^KS11")
    kospi200 = fetch_yahoo("^KS200")
    dates = sorted(set(vkospi) & set(kospi) & set(kospi200))

    history: list[float] = []
    previous: dict[str, float] | None = None
    rows: list[dict[str, object]] = []
    for date in dates:
        vk, ks, ks200 = vkospi[date], kospi[date], kospi200[date]
        kospi_return = pct_change(ks["close"], previous["kospi_close"]) if previous else None
        kospi200_return = pct_change(ks200["close"], previous["kospi200_close"]) if previous else None
        vkospi_change = pct_change(vk["close"], previous["vkospi_close"]) if previous else None
        if kospi_return is not None:
            history.append(kospi_return / 100.0)
        return_5d = pct_change(ks["close"], rows[-5]["kospi_close"]) if len(rows) >= 5 else None
        realized_vol = sample_std(history[-20:]) * math.sqrt(252.0) * 100.0 if len(history) >= 20 else None
        rows.append(
            {
                "date": date,
                "vkospi_open": vk["open"], "vkospi_high": vk["high"], "vkospi_low": vk["low"], "vkospi_close": vk["close"],
                "kospi_open": ks["open"], "kospi_high": ks["high"], "kospi_low": ks["low"], "kospi_close": ks["close"], "kospi_volume": int(ks["volume"]),
                "kospi200_open": ks200["open"], "kospi200_high": ks200["high"], "kospi200_low": ks200["low"], "kospi200_close": ks200["close"], "kospi200_volume": int(ks200["volume"]),
                "vkospi_change_pct": vkospi_change,
                "kospi_return_pct": kospi_return,
                "kospi200_return_pct": kospi200_return,
                "kospi_5d_return_pct": return_5d,
                "kospi_20d_realized_vol_ann_pct": realized_vol,
                "vkospi_minus_kospi_20d_realized_vol": vk["close"] - realized_vol if realized_vol is not None else None,
            }
        )
        previous = {"vkospi_close": vk["close"], "kospi_close": ks["close"], "kospi200_close": ks200["close"]}

    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows):,} rows to {OUTPUT}")
    print(f"Coverage: {rows[0]['date']} to {rows[-1]['date']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Dataset build failed: {error}", file=sys.stderr)
        raise
