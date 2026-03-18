from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

from .ai_strategy import StrategyBlueprint
from .analysis import AssetAnalysis


def _fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def _fmt(value: float) -> str:
    return f"{value:.2f}"


def build_report(
    analyses: Iterable[AssetAnalysis],
    period: str,
    strategies: dict[str, StrategyBlueprint] | None = None,
) -> str:
    items: List[AssetAnalysis] = list(analyses)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    strategies = strategies or {}

    lines: List[str] = [
        "=" * 72,
        "ОТЧЕТ BINANCE CRYPTO ANALYZER",
        "=" * 72,
        f"Дата формирования: {now}",
        f"Анализируемый период: {period}",
        f"Количество инструментов: {len(items)}",
        "",
        "СВОДКА:",
        "-" * 72,
        "Символ      Цена        Доходн.      Волатильн.   Цикл      Риск    Реком.",
    ]

    for a in items:
        lines.append(
            f"{a.symbol:<10}  {_fmt(a.current_price):>10}  {_fmt_pct(a.period_return_pct):>10}  "
            f"{_fmt_pct(a.annualized_volatility_pct):>10}  {a.cycle_position_pct:>6.1f}%  "
            f"{a.risk_level:<6}  {a.recommendation:<5}"
        )

    lines.extend(["", "ДЕТАЛИ ПО ИНСТРУМЕНТАМ:", "-" * 72])

    for a in items:
        lines.extend(
            [
                f"[{a.symbol}]",
                f"Текущая цена: {_fmt(a.current_price)}",
                f"Доходность за период: {_fmt_pct(a.period_return_pct)}",
                f"Годовая волатильность: {_fmt_pct(a.annualized_volatility_pct)}",
                f"VaR 95% (1 день): {_fmt_pct(-a.value_at_risk_95_pct)}",
                f"Максимальная просадка: {_fmt_pct(-a.max_drawdown_pct)}",
                f"SMA20 / SMA50: {_fmt(a.sma20)} / {_fmt(a.sma50)}",
                f"Импульс (14 дней): {_fmt_pct(a.momentum_14d_pct)}",
                f"Положение в 30-дневном цикле: {a.cycle_position_pct:.1f}% ({a.cycle_bias})",
                f"Риск-уровень: {a.risk_level}",
                f"Рекомендация: {a.recommendation}",
                "Причины:",
            ]
        )
        lines.extend([f"  - {reason}" for reason in a.rationale])

        strategy = strategies.get(a.symbol)
        if strategy:
            lines.extend(
                [
                    "AI / Strategy Blueprint:",
                    f"  Источник: {strategy.source}",
                    f"  Название: {strategy.title}",
                    f"  Суть: {strategy.summary}",
                    "  Методология:",
                ]
            )
            lines.extend([f"    - {item}" for item in strategy.methodology])
            lines.append("  Тайминг и циклы:")
            lines.extend([f"    - {item}" for item in strategy.timing_model])
            lines.append("  Контроль риска:")
            lines.extend([f"    - {item}" for item in strategy.risk_controls])
        lines.append("")

    lines.extend(
        [
            "Примечание: отчет носит аналитический характер и не является",
            "индивидуальной инвестиционной рекомендацией.",
        ]
    )

    return "\n".join(lines)
