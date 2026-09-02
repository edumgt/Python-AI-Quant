"""A no-look-ahead 20/60-day trend signal backtest for Hyundai Motor Custom Data."""

from __future__ import annotations

import os
from collections import deque
from datetime import date, datetime, timedelta

from QuantConnect import Globals, Resolution, SubscriptionTransportMedium
from QuantConnect.Algorithm import QCAlgorithm
from QuantConnect.Data import SubscriptionDataSource
from QuantConnect.Python import PythonData


class HyundaiDaily(PythonData):
    def get_source(self, config, date, is_live):
        return SubscriptionDataSource(
            os.path.join(Globals.data_folder, "hyundai.csv"),
            SubscriptionTransportMedium.LOCAL_FILE,
        )

    def reader(self, config, line, date, is_live):
        if not line.strip() or line.startswith("Date"):
            return None
        fields = line.split(",")
        if len(fields) < 6:
            return None
        data = HyundaiDaily()
        data.symbol = config.symbol
        data.time = datetime.strptime(fields[0], "%Y-%m-%d")
        data.end_time = data.time + timedelta(days=1)
        data.value = float(fields[4])
        return data


class HyundaiTrendBacktest(QCAlgorithm):
    """Long only when 20-day average is above 60-day average; otherwise hold cash."""

    def initialize(self):
        start = date.fromisoformat(os.getenv("HYUNDAI_TEST_START_DATE", "2026-01-01"))
        # The Compose variable is exclusive to match the downloader and report.
        end_exclusive = date.fromisoformat(os.getenv("HYUNDAI_TEST_END_DATE", "2026-07-01"))
        end = end_exclusive - timedelta(days=1)
        self.set_start_date(start.year, start.month, start.day)
        self.set_end_date(end.year, end.month, end.day)
        self.set_cash(100_000_000)
        self.hyundai = self.add_data(HyundaiDaily, "005380", Resolution.DAILY).symbol
        self.closes = deque(maxlen=60)
        self.last_signal = None
        # Feed 90 calendar days (at least 60 KRX daily bars) without trading. This lets
        # the first 2026 signal use only information available at the end of 2025.
        self.set_warm_up(90, Resolution.DAILY)

    def on_data(self, data):
        if self.hyundai not in data:
            return
        close = float(data[self.hyundai].value)
        self.closes.append(close)
        if self.is_warming_up or len(self.closes) < 60:
            return

        values = list(self.closes)
        fast = sum(values[-20:]) / 20
        slow = sum(values) / 60
        long_signal = fast > slow
        current_quantity = self.portfolio[self.hyundai].quantity
        desired_quantity = int((self.portfolio.total_portfolio_value * 0.95) / close) if long_signal else 0
        delta = desired_quantity - current_quantity
        if delta:
            self.market_order(self.hyundai, delta)

        signal = "UP" if long_signal else "DOWN"
        if signal != self.last_signal:
            self.debug(f"Trend signal {signal}: close={close:,.0f}, SMA20={fast:,.0f}, SMA60={slow:,.0f}")
            self.last_signal = signal
