from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import sleep
from typing import List

import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"


@dataclass
class PricePoint:
    timestamp: datetime
    close: float


class DataLoadError(RuntimeError):
    """Raised when market data cannot be loaded."""


class BinanceDataProvider:
    """Market data provider via Binance public endpoints."""

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
        self._exchange_symbols: list[str] | None = None

    def fetch_close_prices(self, symbol: str, period: str) -> List[PricePoint]:
        if period not in self.PERIOD_TO_LIMIT:
            raise ValueError(f"Unsupported period '{period}'.")

        normalized_symbol = self.resolve_symbol(symbol)
        query = urlencode(
            {
                "symbol": normalized_symbol,
                "interval": "1d",
                "limit": self.PERIOD_TO_LIMIT[period],
            }
        )
        url = f"{BINANCE_KLINES_URL}?{query}"

        payload = self._get_json(url, symbol)

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

    def resolve_symbol(self, user_input: str) -> str:
        normalized = self._normalize_symbol(user_input)
        if normalized.endswith("USDT"):
            return normalized

        base = self._extract_base_asset(user_input)
        if base in {"USD", "USDT"}:
            raise DataLoadError(f"Could not determine base asset from '{user_input}'.")

        candidate = f"{base}USDT"
        try:
            symbols = self._load_exchange_symbols()
        except DataLoadError:
            return candidate

        if candidate in symbols:
            return candidate

        matches = [symbol for symbol in symbols if symbol.startswith(base) and symbol.endswith("USDT")]
        if len(matches) == 1:
            return matches[0]
        if matches:
            preferred = sorted(matches, key=len)[0]
            return preferred

        raise DataLoadError(
            f"Binance symbol for '{user_input}' not found. Try an explicit pair like {base}USDT."
        )

    def _load_exchange_symbols(self) -> list[str]:
        if self._exchange_symbols is not None:
            return self._exchange_symbols

        payload = self._get_json(BINANCE_EXCHANGE_INFO_URL, "exchangeInfo")
        if not isinstance(payload, dict) or "symbols" not in payload:
            raise DataLoadError("Unexpected Binance exchangeInfo response format.")

        self._exchange_symbols = [
            item["symbol"]
            for item in payload["symbols"]
            if item.get("status") == "TRADING"
        ]
        return self._exchange_symbols

    def _get_json(self, url: str, context: str):
        try:
            sleep(self.request_delay_seconds)
            with urlopen(url, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise DataLoadError(f"HTTP {response.status} for {context}.")
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise DataLoadError(f"HTTP {exc.code} for {context}.") from exc
        except URLError as exc:
            raise DataLoadError(f"Network error for {context}: {exc.reason}") from exc

    @staticmethod
    def _extract_base_asset(symbol: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9]", "", symbol).upper()
        if cleaned.endswith("USDT"):
            return cleaned[:-4]
        if cleaned.endswith("USD"):
            return cleaned[:-3]
        return cleaned

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        cleaned = symbol.replace("-", "").replace("/", "").replace(" ", "").upper()
        if cleaned.endswith("USD") and not cleaned.endswith("USDT"):
            return f"{cleaned[:-3]}USDT"
        return cleaned
