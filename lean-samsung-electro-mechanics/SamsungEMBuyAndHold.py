from QuantConnect import Globals, Resolution, SubscriptionTransportMedium
from QuantConnect.Algorithm import QCAlgorithm
from QuantConnect.Data import SubscriptionDataSource
from QuantConnect.Python import PythonData
import os
from datetime import date, datetime, timedelta


class SamsungEMDaily(PythonData):
    """Yahoo Finance daily OHLCV CSV stored under LEAN's data directory."""

    def get_source(self, config, date, is_live):
        source = os.path.join(Globals.data_folder, "samsung_em.csv")
        return SubscriptionDataSource(source, SubscriptionTransportMedium.LOCAL_FILE)

    def reader(self, config, line, date, is_live):
        if not line.strip() or line.startswith("Date"):
            return None

        fields = line.split(",")
        if len(fields) < 6:
            return None

        data = SamsungEMDaily()
        data.symbol = config.symbol
        data.time = datetime.strptime(fields[0], "%Y-%m-%d")
        data.end_time = data.time + timedelta(days=1)
        data.value = float(fields[4])
        return data


class SamsungEMBuyAndHold(QCAlgorithm):
    def initialize(self):
        start = date.fromisoformat(os.getenv("SAMSUNG_EM_START_DATE", "2024-01-01"))
        end = date.fromisoformat(os.getenv("SAMSUNG_EM_END_DATE", "2025-01-01"))
        self.set_start_date(start.year, start.month, start.day)
        self.set_end_date(end.year, end.month, end.day)
        self.set_cash(1_000_000)

        self.samsung_em = self.add_data(SamsungEMDaily, "009150", Resolution.DAILY).symbol
        self.bought = False

    def on_data(self, data):
        if self.samsung_em not in data:
            return

        close = data[self.samsung_em].value
        self.plot("Samsung Electro-Mechanics", "Close", close)

        if not self.bought:
            # Custom Data의 가격 단위로 1주를 매수해 엔진 주문 흐름을 확인합니다.
            self.market_order(self.samsung_em, 1)
            self.bought = True
            self.debug(f"Samsung Electro-Mechanics buy test: {close:,.0f}")
