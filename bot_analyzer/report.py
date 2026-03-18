from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

from .analysis import AssetAnalysis


def _fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def _fmt(value: float) -> str:
    return f"{value:.2f}"


def build_report(analyses: Iterable[AssetAnalysis], period: str) -> str:
    items: List[AssetAnalysis] = list(analyses)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines: List[str] = [
        "=" * 72,
        "ОТЧЕТ ИНВЕСТИЦИОННОГО БОТА (АКЦИИ + КРИПТО)",
        "=" * 72,
        f"Дата формирования: {now}",
        f"Анализируемый период: {period}",
        f"Количество инструментов: {len(items)}",
        "",
        "СВОДКА:",
        "-" * 72,
        "Символ      Цена        Доходн.      Волатильн.   MaxDD      Риск    Реком.",
    ]

    for a in items:
        lines.append(
            f"{a.symbol:<10}  {_fmt(a.current_price):>10}  {_fmt_pct(a.period_return_pct):>10}  "
            f"{_fmt_pct(a.annualized_volatility_pct):>10}  {_fmt_pct(-a.max_drawdown_pct):>8}  "
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
                f"Риск-уровень: {a.risk_level}",
                f"Рекомендация: {a.recommendation}",
                "Причины:",
            ]
        )
        lines.extend([f"  - {reason}" for reason in a.rationale])
        lines.append("")

    lines.extend(
        [
            "Примечание: отчет носит аналитический характер и не является",
            "индивидуальной инвестиционной рекомендацией.",
        ]
    )

    return "\n".join(lines)
