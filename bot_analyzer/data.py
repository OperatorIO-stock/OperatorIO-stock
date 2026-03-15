from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


@dataclass
class PricePoint:
    timestamp: datetime
    close: float


class DataLoadError(RuntimeError):
    """Raised when market data cannot be loaded."""


class YahooFinanceDataProvider:
    """Simple market data provider via Yahoo Finance chart endpoint."""

    PERIOD_TO_RANGE = {
        "1mo": "1mo",
        "3mo": "3mo",
        "6mo": "6mo",
        "1y": "1y",
        "2y": "2y",
        "5y": "5y",
    }

    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch_close_prices(self, symbol: str, period: str) -> List[PricePoint]:
        if period not in self.PERIOD_TO_RANGE:
            raise ValueError(f"Unsupported period '{period}'.")

        query = urlencode({"range": self.PERIOD_TO_RANGE[period], "interval": "1d"})
        url = f"{YAHOO_CHART_URL.format(symbol=symbol)}?{query}"

        try:
            with urlopen(url, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise DataLoadError(f"HTTP {response.status} for symbol {symbol}.")
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise DataLoadError(f"HTTP {exc.code} for symbol {symbol}.") from exc
        except URLError as exc:
            raise DataLoadError(f"Network error for symbol {symbol}: {exc.reason}") from exc
        result = payload.get("chart", {}).get("result")
        if not result:
            error = payload.get("chart", {}).get("error")
            raise DataLoadError(f"No data for {symbol}: {error or 'unknown error'}")

        entry = result[0]
        timestamps = entry.get("timestamp") or []
        closes = (
            entry.get("indicators", {})
            .get("quote", [{}])[0]
            .get("close", [])
        )

        points: List[PricePoint] = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            points.append(
                PricePoint(
                    timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
                    close=float(close),
                )
            )

        if len(points) < 30:
            raise DataLoadError(
                f"Not enough data for {symbol}. Need >=30 points, got {len(points)}."
            )

        return points
