# MOEX Code Loader

Python-инструментарий для загрузки, обработки и анализа фьючерсных данных Московской биржи (MOEX). Проект скачивает историю по фьючерсным контрактам, склеивает их в непрерывные ряды и строит сводные графики для контроля качества данных.

Это развитие проекта `moex_data_loader`: та же логика загрузки/склейки, но управляемая единым `config.yaml`, плюс набор юнит-тестов и черновой модуль для тестирования торговых стратегий (`strategy/`).

## Возможности

- **Загрузка данных**: скачивание исторических свечей с MOEX API (`apimoex`) с retry и экспоненциальным backoff
- **Склейка непрерывных контрактов**: автоматический выбор даты ролловера на основе анализа объёмов
- **Сводки и визуализация**: графики покрытия данных по тикерам/месяцам и графики ролловеров
- **Таймфреймы**: 1-минутные и 5-минутные ряды
- **Конфигурация через `config.yaml`**: каждый этап пайплайна (загрузка/сводка/склейка/тесты) включается и настраивается независимо
- **Тесты**: юнит-тесты на `unittest` для `utilities.py`, `moex_futures_data_loader.py`, `moex_futures_merge.py` — без сетевых вызовов, на заглушках

## Структура проекта

```
moex_code_loader/
├── config.yaml                    # Единая конфигурация всех этапов пайплайна
├── moex_futures_data_loader.py    # Загрузка исторических данных
├── moex_futures_merge.py          # Склейка непрерывных контрактов
├── load_summary.py                # Сводки и визуализация покрытия данных
├── update_data.py                 # Запуск всего пайплайна по порядку
├── utilities.py                   # Вспомогательные функции (список тикеров)
├── requirements.txt               # Зависимости
├── tests/                         # Юнит-тесты + сетевые заглушки (tests/stubs)
├── strategy/                      # Черновики walk-forward тестирования стратегий
├── TESTS_README.md                # Подробности о тестах и их ограничениях
├── MOEX/                          # Исходные данные по контрактам (CSV)
├── continous/                     # Непрерывные ряды
├── merge_summary/                 # Графики и csv по ролловерам
└── load_summary/                  # Графики покрытия данных
```

## Установка

```bash
git clone <repository-url>
cd moex_code_loader
pip install -r requirements.txt
```

## Конфигурация (`config.yaml`)

Все параметры пайплайна вынесены в `config.yaml`:

```yaml
general:
  data_folder: "MOEX"
  continuous_folder: "continous"
  summary_of_merging_folder: "merge_summary"
  summary_of_loading_folder: "load_summary"
  years: [2026]
  months: ["F", "G", "H"]

load:
  enabled: false        # включить/выключить загрузку данных
  max_retries: 7
  base_delay: 5

summary:
  enabled: false        # включить/выключить построение сводок
  monthly_months: ["F","G","J","K","N","Q","V","X"]
  quarterly_months: ["H","M","U","Z"]

merge:
  enabled: true         # включить/выключить склейку
  output_suffixes: ["_1min.csv", "_5min.csv"]
  force_recreate: false

test:
  enabled: true         # включить/выключить прогон тестов через update_data.py
```

Каждый скрипт (`moex_futures_data_loader.py`, `load_summary.py`, `moex_futures_merge.py`) при прямом запуске сам читает `config.yaml` и проверяет свой флаг `enabled` — если `false`, скрипт завершается сразу без действий. Это удобно, если нужно перезапустить только один этап пайплайна.

## Использование

### Запуск всего пайплайна

```bash
python update_data.py
```

Выполняет по очереди (останавливаясь при первой ошибке):
1. `moex_futures_data_loader.py` — загрузка данных
2. `load_summary.py` — сводки
3. `moex_futures_merge.py` — склейка непрерывных контрактов
4. `tests/test_data_loader.py`, `tests/test_merge_algorithm.py`, `tests/test_utilities.py` — юнит-тесты

Какие шаги реально выполнят работу, а какие сразу выйдут — определяется флагами `enabled` в `config.yaml`.

### Отдельные этапы

```bash
python moex_futures_data_loader.py   # загрузка данных (если load.enabled: true)
python load_summary.py               # сводки (если summary.enabled: true)
python moex_futures_merge.py         # склейка (если merge.enabled: true)
```

## Тесты

```bash
cd moex_code_loader
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

Тесты не требуют сети — `apimoex`, `moexalgo`, `tqdm` подменены лёгкими заглушками в `tests/stubs/`. Подробное описание покрытия, архитектурных изменений под тесты и известного ограничения алгоритма ролловера — в [TESTS_README.md](TESTS_README.md).

Текущий статус: **все 12 тестов проходят**.

## Данные

### Исходные данные (`MOEX/`)
- CSV на каждый фьючерсный контракт: `{ticker}{month}{year}.csv`
- Колонки: `begin, open, high, low, close, volume, value, log_ret`

### Непрерывные ряды (`continous/`)
- `{ticker}_1min.csv`, `{ticker}_5min.csv`

### Сводки
- `load_summary/summary_check_monthly.png`, `summary_check_quarterly.png` — покрытие данных
- `merge_summary/{ticker}_rolls.png`, `{ticker}_rolls.csv` — анализ объёмов и даты ролловеров

## Модуль стратегий (`strategy/`)

Черновой код для walk-forward тестирования простой MA-стратегии на непрерывных рядах:
- `WOF_strategy.py` — walk-forward оптимизация параметров (sharpe / total return / max drawdown) через `skfolio.model_selection.WalkForward`
- `strategy_ma.py` — пример стратегии на пересечении скользящих средних, строит графики в `strategy/graphs_and_stats/`

## Зависимости

- `pandas>=1.5.0`, `numpy>=1.21.0`, `matplotlib>=3.5.0`, `requests>=2.28.0`
- `apimoex>=1.2.0`, `moexalgo>=1.0.0` — клиенты MOEX API
- `tqdm>=4.60.0` — прогресс-бары
- `urllib3>=1.26.0` — retry-стратегии для HTTP
- `pyyaml>=6.0.3` — чтение `config.yaml`
- `skfolio>=0.20.1`