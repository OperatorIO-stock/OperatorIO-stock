from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import sleep
from typing import List

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


@dataclass
class PricePoint:
    timestamp: datetime
    close: float


class DataLoadError(RuntimeError):
    """Raised when market data cannot be loaded."""


class BinanceDataProvider:
    """Market data provider via Binance kline endpoint."""

    PERIOD_TO_LIMIT = {
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1000,
    }

    def __init__(self, timeout_seconds: int = 10, request_delay_seconds: float = 0.2) -> None:
        self.timeout_seconds = timeout_seconds
        self.request_delay_seconds = request_delay_seconds

    def fetch_close_prices(self, symbol: str, period: str) -> List[PricePoint]:
        if period not in self.PERIOD_TO_LIMIT:
            raise ValueError(f"Unsupported period '{period}'.")

        normalized_symbol = self._normalize_symbol(symbol)
        query = urlencode(
            {
                "symbol": normalized_symbol,
                "interval": "1d",
                "limit": self.PERIOD_TO_LIMIT[period],
            }
        )
        url = f"{BINANCE_KLINES_URL}?{query}"

        try:
            sleep(self.request_delay_seconds)
            with urlopen(url, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise DataLoadError(f"HTTP {response.status} for symbol {symbol}.")
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise DataLoadError(f"HTTP {exc.code} for symbol {symbol}.") from exc
        except URLError as exc:
            raise DataLoadError(f"Network error for symbol {symbol}: {exc.reason}") from exc

        if isinstance(payload, dict) and payload.get("code"):
            raise DataLoadError(payload.get("msg", f"No data for {symbol}."))

        points = [
            PricePoint(
                timestamp=datetime.fromtimestamp(entry[0] / 1000, tz=timezone.utc),
                close=float(entry[4]),
            )
            for entry in payload
        ]

        if len(points) < 30:
            raise DataLoadError(
                f"Not enough data for {symbol}. Need >=30 points, got {len(points)}."
            )

        return points

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        cleaned = symbol.replace("-", "").replace("/", "").upper()
        if cleaned.endswith("USD") and not cleaned.endswith("USDT"):
            return f"{cleaned[:-3]}USDT"
        return cleaned
