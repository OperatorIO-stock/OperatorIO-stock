from datetime import datetime, timedelta, timezone

from bot_analyzer.ai_strategy import AIStrategyEngine
from bot_analyzer.analysis import analyze_asset
from bot_analyzer.data import BinanceDataProvider, PricePoint


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
    assert 0 <= result.cycle_position_pct <= 100


def test_binance_symbol_normalization_supports_usd_variants() -> None:
    assert BinanceDataProvider._normalize_symbol("BTC-USD") == "BTCUSDT"
    assert BinanceDataProvider._normalize_symbol("eth/usd") == "ETHUSDT"
    assert BinanceDataProvider._normalize_symbol("SOLUSDT") == "SOLUSDT"


def test_resolve_symbol_prefers_usdt_pair() -> None:
    provider = BinanceDataProvider()
    provider._exchange_symbols = ["BTCUSDT", "BTCEUR", "ETHUSDT"]
    assert provider.resolve_symbol("btc") == "BTCUSDT"
    assert provider.resolve_symbol("ETH") == "ETHUSDT"


def test_ai_strategy_fallback_contains_cycle_and_risk_guidance() -> None:
    analysis = analyze_asset("TESTUSDT", _make_series(100, 0.5, 80))
    blueprint = AIStrategyEngine()._build_deterministic_strategy(analysis, "проанализируй test")
    assert blueprint.source == "deterministic-fallback"
    assert any("цикл" in item.lower() for item in blueprint.timing_model)
    assert any("Риск" in item or "риск" in item for item in blueprint.risk_controls)
