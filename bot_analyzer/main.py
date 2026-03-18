from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .ai_strategy import AIStrategyEngine
from .analysis import analyze_asset
from .data import BinanceDataProvider, DataLoadError
from .report import build_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Бот-аналитик криптовалют с оценкой рисков."
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Список символов Binance или названий монет (например: BTCUSDT pepe BTC-USD)",
    )
    parser.add_argument(
        "--query",
        help="Прямой запрос на анализ одной монеты, например: 'проанализируй pepe'",
    )
    parser.add_argument(
        "--period",
        default="6mo",
        choices=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        help="Период анализа",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Путь к файлу для сохранения отчета",
    )
    parser.add_argument(
        "--with-ai",
        action="store_true",
        help="Добавить AI/strategy blueprint. Использует OPENAI_API_KEY при наличии, иначе fallback-алгоритм.",
    )
    args = parser.parse_args()
    if not args.symbols and not args.query:
        parser.error("Нужно передать --symbols или --query.")
    return args


def _extract_symbol_from_query(query: str) -> str:
    tokens = [token.strip(" ,.!?\t\n\r") for token in query.split()]
    meaningful = [token for token in tokens if token]
    if not meaningful:
        raise ValueError("Пустой запрос для анализа.")
    return meaningful[-1]


def main() -> int:
    args = parse_args()
    provider = BinanceDataProvider()
    strategy_engine = AIStrategyEngine() if args.with_ai else None

    requested_symbols = list(args.symbols or [])
    if args.query:
        requested_symbols.append(_extract_symbol_from_query(args.query))

    analyses = []
    strategies = {}
    failed = []

    for requested_symbol in requested_symbols:
        try:
            resolved_symbol = provider.resolve_symbol(requested_symbol)
            prices = provider.fetch_close_prices(resolved_symbol, args.period)
            analysis = analyze_asset(resolved_symbol, prices)
            analyses.append(analysis)
            if strategy_engine:
                strategies[analysis.symbol] = strategy_engine.build_strategy(analysis, args.query)
        except (DataLoadError, ValueError) as exc:
            failed.append((requested_symbol, str(exc)))

    if not analyses:
        print("Не удалось загрузить данные ни по одному инструменту.", file=sys.stderr)
        for symbol, reason in failed:
            print(f"- {symbol}: {reason}", file=sys.stderr)
        return 1

    report = build_report(analyses, args.period, strategies)
    print(report)

    if args.output:
        args.output.write_text(report, encoding="utf-8")

    if failed:
        print("\nПредупреждения:", file=sys.stderr)
        for symbol, reason in failed:
            print(f"- {symbol}: {reason}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
