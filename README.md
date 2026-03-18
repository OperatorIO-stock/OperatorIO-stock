# Investment Analyst Bot (Python)

Бот для анализа криптовалют в стиле профессионального аналитика.

## Что умеет
- Загружает историю цен из Binance API (без API-ключа).
- Добавляет небольшую задержку между HTTP-запросами, чтобы не спамить API.
- Считает ключевые метрики:
  - доходность за период;
  - волатильность (годовая);
  - VaR 95%;
  - максимальная просадка;
  - тренд (SMA20/SMA50);
  - импульс за 14 дней.
- Формирует рекомендации:
  - `BUY` / `HOLD` / `AVOID`;
  - риск-профиль: `LOW` / `MEDIUM` / `HIGH`.
- Генерирует подробный текстовый отчет по каждому инструменту и сводную таблицу.

## Установка
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск
```bash
python -m bot_analyzer.main --symbols BTCUSDT ETHUSDT SOLUSDT --period 6mo
```

Пример сохранения отчета в файл:
```bash
python -m bot_analyzer.main --symbols BTCUSDT ETH-USD --period 1y --output report.txt
```

## Параметры
- `--symbols` список тикеров (обязательно).
- `--period` период: `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`.
- `--output` путь к файлу для сохранения отчета.

## Примечания
- Используйте торговые пары Binance, например `BTCUSDT`, `ETHUSDT`, `SOLUSDT`.
- Форматы `BTC-USD`, `BTC/USD` и `BTCUSD` автоматически нормализуются в `BTCUSDT`.
- Инструмент не дает инвестиционных гарантий; это аналитическая поддержка принятия решений.
