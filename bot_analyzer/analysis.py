from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean, quantiles, stdev
from typing import List

from .data import PricePoint


TRADING_DAYS_PER_YEAR = 252


@dataclass
class AssetAnalysis:
    symbol: str
    current_price: float
    period_return_pct: float
    annualized_volatility_pct: float
    value_at_risk_95_pct: float
    max_drawdown_pct: float
    sma20: float
    sma50: float
    momentum_14d_pct: float
    cycle_position_pct: float
    cycle_bias: str
    risk_level: str
    recommendation: str
    rationale: List[str]


def _daily_returns(closes: List[float]) -> List[float]:
    return [(closes[i] / closes[i - 1]) - 1 for i in range(1, len(closes))]


def _max_drawdown_pct(closes: List[float]) -> float:
    peak = closes[0]
    max_dd = 0.0
    for price in closes:
        peak = max(peak, price)
        drawdown = (price - peak) / peak
        max_dd = min(max_dd, drawdown)
    return abs(max_dd) * 100


def _cycle_position_pct(closes: List[float], lookback: int = 30) -> float:
    window = closes[-lookback:]
    low = min(window)
    high = max(window)
    if high == low:
        return 50.0
    return (window[-1] - low) / (high - low) * 100


def analyze_asset(symbol: str, prices: List[PricePoint]) -> AssetAnalysis:
    closes = [p.close for p in prices]
    rets = _daily_returns(closes)

    period_return = (closes[-1] / closes[0] - 1) * 100
    vol = stdev(rets) * sqrt(TRADING_DAYS_PER_YEAR) * 100 if len(rets) > 1 else 0.0

    q = quantiles(rets, n=20, method="inclusive")
    var95 = abs(q[0]) * 100

    dd = _max_drawdown_pct(closes)
    sma20 = mean(closes[-20:])
    sma50 = mean(closes[-50:])
    momentum14 = (closes[-1] / closes[-15] - 1) * 100
    cycle_position = _cycle_position_pct(closes)

    risk_points = 0
    rationale: List[str] = []

    if vol > 45:
        risk_points += 2
        rationale.append("Высокая волатильность повышает риск.")
    elif vol > 30:
        risk_points += 1
        rationale.append("Умеренно высокая волатильность.")

    if dd > 30:
        risk_points += 2
        rationale.append("Глубокая историческая просадка.")
    elif dd > 20:
        risk_points += 1
        rationale.append("Заметная просадка в периоде.")

    if var95 > 4:
        risk_points += 1
        rationale.append("Повышенный дневной VaR (95%).")

    trend_positive = closes[-1] > sma20 > sma50
    if trend_positive:
        rationale.append("Положительный тренд (цена выше SMA20 и SMA50).")
    else:
        risk_points += 1
        rationale.append("Тренд не подтвержден долгосрочно.")

    if cycle_position >= 75:
        cycle_bias = "cycle-top"
        risk_points += 1
        rationale.append("Цена находится в верхней части 30-дневного цикла: возможна фиксация прибыли.")
    elif cycle_position <= 25:
        cycle_bias = "cycle-bottom"
        rationale.append("Цена находится в нижней части 30-дневного цикла: рынок ищет основание.")
    else:
        cycle_bias = "mid-cycle"
        rationale.append("Цена находится в середине 30-дневного цикла без экстремума.")

    if risk_points <= 1:
        risk_level = "LOW"
    elif risk_points <= 3:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    if trend_positive and momentum14 > 0 and risk_level != "HIGH" and cycle_position < 85:
        recommendation = "BUY"
        rationale.append("Импульс, тренд и цикл поддерживают сценарий покупки.")
    elif risk_level == "HIGH" or period_return < -10:
        recommendation = "AVOID"
        rationale.append("Риск/доходность не в пользу входа сейчас.")
    else:
        recommendation = "HOLD"
        rationale.append("Нейтральная конфигурация: лучше наблюдать.")

    return AssetAnalysis(
        symbol=symbol,
        current_price=closes[-1],
        period_return_pct=period_return,
        annualized_volatility_pct=vol,
        value_at_risk_95_pct=var95,
        max_drawdown_pct=dd,
        sma20=sma20,
        sma50=sma50,
        momentum_14d_pct=momentum14,
        cycle_position_pct=cycle_position,
        cycle_bias=cycle_bias,
        risk_level=risk_level,
        recommendation=recommendation,
        rationale=rationale,
    )
