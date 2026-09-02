"""Download Hyundai Motor daily OHLCV data for a local LEAN Custom Data feed."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def unix_timestamp(value: str) -> int:
    parsed = date.fromisoformat(value)
    return int(datetime.combine(parsed, time.min, tzinfo=timezone.utc).timestamp())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    query = urlencode({
        "period1": unix_timestamp(args.start),
        "period2": unix_timestamp(args.end),
        "interval": "1d",
        "events": "history",
    })
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/005380.KS?{query}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    rows = zip(result["timestamp"], quote["open"], quote["high"], quote["low"], quote["close"], quote["volume"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
        for timestamp, open_, high, low, close, volume in rows:
            if None in (open_, high, low, close, volume):
                continue
            day = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
            writer.writerow([day, open_, high, low, close, volume])
            written += 1

    if written == 0:
        raise RuntimeError("No Hyundai Motor price rows were downloaded")
    print(f"Downloaded {written} Hyundai Motor daily bars to {output}")


if __name__ == "__main__":
    main()
