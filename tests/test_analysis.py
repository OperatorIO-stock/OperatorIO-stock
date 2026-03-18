from datetime import datetime, timedelta, timezone

from bot_analyzer.analysis import analyze_asset
from bot_analyzer.data import PricePoint


def _make_series(start: float, step: float, n: int) -> list[PricePoint]:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        PricePoint(timestamp=base + timedelta(days=i), close=start + i * step)
        for i in range(n)
    ]


def test_positive_trend_recommendation_not_avoid():
    prices = _make_series(100, 1, 80)
    result = analyze_asset("TEST", prices)
    assert result.recommendation in {"BUY", "HOLD"}
    assert result.risk_level in {"LOW", "MEDIUM", "HIGH"}


def test_drawdown_metric_non_negative():
    prices = _make_series(100, 1, 30)
    prices[20] = PricePoint(timestamp=prices[20].timestamp, close=90)
    prices[21] = PricePoint(timestamp=prices[21].timestamp, close=88)
    result = analyze_asset("TEST", prices)
    assert result.max_drawdown_pct >= 0


from bot_analyzer.data import BinanceDataProvider


def test_binance_symbol_normalization_supports_usd_variants() -> None:
    assert BinanceDataProvider._normalize_symbol("BTC-USD") == "BTCUSDT"
    assert BinanceDataProvider._normalize_symbol("eth/usd") == "ETHUSDT"
    assert BinanceDataProvider._normalize_symbol("SOLUSDT") == "SOLUSDT"
