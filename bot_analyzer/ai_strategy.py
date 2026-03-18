from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .analysis import AssetAnalysis


@dataclass
class StrategyBlueprint:
    title: str
    summary: str
    methodology: list[str]
    timing_model: list[str]
    risk_controls: list[str]
    source: str


class AIStrategyEngine:
    def __init__(self, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def build_strategy(self, analysis: AssetAnalysis, user_query: Optional[str] = None) -> StrategyBlueprint:
        if self.api_key:
            try:
                return self._build_with_llm(analysis, user_query)
            except RuntimeError:
                pass
        return self._build_deterministic_strategy(analysis, user_query)

    def _build_with_llm(self, analysis: AssetAnalysis, user_query: Optional[str]) -> StrategyBlueprint:
        prompt = self._build_prompt(analysis, user_query)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a quantitative crypto analyst. Build a concrete, risk-aware "
                        "analysis algorithm using trading analysis, trend structure, momentum, "
                        "volatility, drawdown and time-cycle logic. Respond in JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }
        request = Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc

        content = body["choices"][0]["message"]["content"]
        data = json.loads(content)
        return StrategyBlueprint(
            title=data.get("title", f"AI strategy for {analysis.symbol}"),
            summary=data.get("summary", "LLM generated trading plan."),
            methodology=list(data.get("methodology", [])),
            timing_model=list(data.get("timing_model", [])),
            risk_controls=list(data.get("risk_controls", [])),
            source=f"LLM:{self.model}",
        )

    def _build_deterministic_strategy(
        self,
        analysis: AssetAnalysis,
        user_query: Optional[str],
    ) -> StrategyBlueprint:
        cycle_state = {
            "cycle-bottom": "искать разворот после стабилизации и возврата выше SMA20",
            "mid-cycle": "работать по подтвержденному направлению и не догонять импульс",
            "cycle-top": "ждать отката или сильной консолидации перед новым входом",
        }[analysis.cycle_bias]

        methodology = [
            "Определи базовый тренд по структуре close > SMA20 > SMA50 и силе доходности за период.",
            "Сравни 14-дневный импульс с годовой волатильностью, чтобы понять качество движения.",
            "Оцени рыночный риск через VaR 95% и максимальную просадку, затем скорректируй размер позиции.",
        ]
        if analysis.recommendation == "BUY":
            methodology.append("Разрешай вход только при сохранении положительного импульса и отсутствии перекупленности цикла.")
        elif analysis.recommendation == "AVOID":
            methodology.append("Приоритет — защита капитала: новые входы запрещены до нормализации риска и тренда.")
        else:
            methodology.append("Пока сценарий нейтральный: нужен пробой диапазона или перезапуск импульса.")

        timing_model = [
            f"Текущее положение в 30-дневном цикле: {analysis.cycle_position_pct:.1f}% ({analysis.cycle_bias}).",
            f"Для {analysis.symbol} базовое действие: {cycle_state}.",
            "Проверяй вход по схеме 4H -> 1D: младший таймфрейм ищет момент, дневной подтверждает контекст.",
        ]
        if user_query:
            timing_model.append(f"Прямой запрос пользователя учтен в логике сценария: '{user_query.strip()}'.")

        risk_controls = [
            f"Риск-уровень инструмента сейчас: {analysis.risk_level}; рекомендация: {analysis.recommendation}.",
            "Риск на сделку ограничивать 0.5-1.0% капитала при HIGH/MEDIUM risk и до 1.5% при LOW risk.",
            "Если цена закрывается ниже SMA20 при длинной позиции — пересмотреть сценарий; ниже SMA50 — выход обязателен.",
        ]

        return StrategyBlueprint(
            title=f"Adaptive Binance Strategy: {analysis.symbol}",
            summary=(
                "Алгоритм объединяет трендовый анализ, импульс, оценку риска и положение цены "
                "в краткосрочном временном цикле. Если доступен OPENAI_API_KEY, модуль может "
                "автоматически заменить этот шаблон LLM-версией."
            ),
            methodology=methodology,
            timing_model=timing_model,
            risk_controls=risk_controls,
            source="deterministic-fallback",
        )

    @staticmethod
    def _build_prompt(analysis: AssetAnalysis, user_query: Optional[str]) -> str:
        return (
            f"Create a trading-analysis algorithm for {analysis.symbol}. "
            f"Metrics: price={analysis.current_price:.4f}, return={analysis.period_return_pct:.2f}%, "
            f"vol={analysis.annualized_volatility_pct:.2f}%, VaR95={analysis.value_at_risk_95_pct:.2f}%, "
            f"maxDD={analysis.max_drawdown_pct:.2f}%, SMA20={analysis.sma20:.4f}, SMA50={analysis.sma50:.4f}, "
            f"mom14={analysis.momentum_14d_pct:.2f}%, cyclePosition={analysis.cycle_position_pct:.2f}%, "
            f"cycleBias={analysis.cycle_bias}, risk={analysis.risk_level}, rec={analysis.recommendation}. "
            f"User request: {user_query or 'n/a'}. "
            "Return JSON with keys: title, summary, methodology (array), timing_model (array), risk_controls (array)."
        )
