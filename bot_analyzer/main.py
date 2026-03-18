from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analysis import analyze_asset
from .data import DataLoadError, YahooFinanceDataProvider
from .report import build_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Бот-аналитик акций и криптомонет с оценкой рисков."
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        required=True,
        help="Список тикеров (например: AAPL MSFT BTC-USD ETH-USD)",
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    provider = YahooFinanceDataProvider()

    analyses = []
    failed = []

    for symbol in args.symbols:
        try:
            prices = provider.fetch_close_prices(symbol, args.period)
            analyses.append(analyze_asset(symbol, prices))
        except (DataLoadError, ValueError) as exc:
            failed.append((symbol, str(exc)))

    if not analyses:
        print("Не удалось загрузить данные ни по одному инструменту.", file=sys.stderr)
        for symbol, reason in failed:
            print(f"- {symbol}: {reason}", file=sys.stderr)
        return 1

    report = build_report(analyses, args.period)
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
