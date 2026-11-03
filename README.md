# MazeBookGenerator

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python: 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

Генератор печатных книг с лабиринтами для детей. Создаёт готовые к публикации
PDF-книги: обложка, страницы-задания, страницы-ответы, print-friendly версия —
с AI-темами и иллюстрациями (английский и русский языки).

## Возможности

- 8 форм лабиринтов: прямоугольные, квадратные, треугольные, круглые (полярные),
  хаотичные, ромб, сердце, случайная форма
- 7 уровней сложности и стратегии распределения по страницам
  (FIXED, INCREMENTAL, RANDOM_RANGE, KIDS_EASY, CHALLENGE_HARD, STORY_WAVE)
- AI-тема книги через OpenAI (название, описание, задания для маркетплейсов)
- Иллюстрации: Replicate → Pollinations → Hugging Face (цепочка fallback'ов)
- Локализация EN/RU, готовые пресеты конфигураций книг
- Print-friendly версия PDF для экономной печати

## Установка

```bash
# uv (рекомендуется)
uv sync

# или pip
pip install -e .
```

Опциональные компоненты:

```bash
pip install -e ".[mongodb]"   # хранение тем в MongoDB вместо JSON-файла
```

### Системные зависимости

- **Шрифты DejaVu** — обязательны для PDF (кириллица). Linux:
  `sudo apt install fonts-dejavu`; macOS: `brew install --cask font-dejavu`
- **poppler** — только для превью (`--no-previews` отключает). Linux:
  `sudo apt install poppler-utils`; macOS: `brew install poppler`

Скопируйте `.env.example` в `.env` и заполните API-ключи. Все ключи
опциональны: без иллюстрационных токенов цепочка провайдеров
(Replicate → Pollinations → HF) деградирует до локального placeholder,
а тему без `OPEN_AI_KEY` можно задать флагом `--theme` (офлайн-режим).

| Переменная | Назначение |
|---|---|
| `OPEN_AI_KEY` | OpenAI — генерация темы книги |
| `REPLICATE_API_TOKEN` | Replicate — основной провайдер иллюстраций |
| `HF_TOKEN` | Hugging Face — fallback-провайдер |
| `MONGODB_ENABLED` | `true` — хранить темы в MongoDB |
| `MONGODB_URI` | URI MongoDB (по умолчанию localhost) |

## Использование

```bash
# Одна книга с настройками по умолчанию
mazebook generate

# Пачка книг с выбором пресета и сложности
mazebook generate --books 3 --pages 20 --size 17x13 \
    --preset en_school --difficulty INCREMENTAL

# Воспроизводимая генерация и только PDF (без иллюстраций/превью)
mazebook generate --seed 42 --no-images --no-previews

# Офлайн-режим без OpenAI-ключа: локализованная тема-заглушка
mazebook generate --theme "Приключение в лабиринте" --no-images

# Персонализированная книга
mazebook generate --child-name Emma --child-age 6

# То же через python -m или main.py
python -m maze_book_generator generate --preset ru_kids_easy
python main.py generate
```

| Флаг | По умолчанию | Назначение |
|---|---|---|
| `--books` | 1 | Количество книг в пачке |
| `--pages` | 30 | Лабиринтов в книге |
| `--size` | 15x11 | Размер лабиринта `WxH` |
| `--preset` | ru_kids_easy | Пресет BookConfig |
| `--difficulty` | KIDS_EASY | Стратегия сложности |
| `--seed` | — | Базовый seed (воспроизводимость) |
| `--theme` | — | Название темы без OpenAI (офлайн-режим) |
| `--child-name` / `--child-age` | — | Персонализация обложки |
| `--no-images` | — | Пропустить иллюстрации |
| `--no-previews` | — | Пропустить превью |
| `--no-print-friendly` | — | Отключить ч/б версию PDF |

Результат — в `output/book_N/`: `book.pdf` (+ `book_print_friendly.pdf`),
`illustrations/`, превью, `book_into.txt` с маркетинговыми текстами.

### Пресеты

`en_kids_basic`, `en_kids_printable`, `en_school`, `en_school_printable`,
`en_challenge`, `ru_kids_easy`, `ru_kids_basic`, `ru_kids_printable`,
`ru_school`, `ru_school_printable`, `ru_challenge` — см.
`src/maze_book_generator/application/config_presets.py`.

## Структура проекта

```
src/maze_book_generator/
  domain/           # чистая логика лабиринтов (без I/O)
    maze/           # сетка, маски, carving, solver, polar
    models.py       # Book, BookPage, Theme, BookConfig, Difficulty
  application/      # оркестрация сценариев
    book_service.py # сценарии генерации
    book_factory.py # BookSpec + сборка страниц
    illustration_pipeline.py  # цепочка провайдеров
    marketplace.py  # book_into.txt, book_id
    config_presets.py
  infrastructure/   # I/O и внешние сервисы
    pdf/            # рендеринг PDF (renderer, страницы, декор, drawing/)
    images/         # провайдеры иллюстраций + providers.py
    storage/        # ThemeRepository: JSON по умолчанию, MongoDB опционально
    preview_generator.py
    ai_client.py
  cli.py            # CLI (mazebook)
  settings.py       # все константы и конфигурация
  localization.py   # тексты EN/RU
  container.py      # DI-контейнер
tests/              # pytest (194 теста)
```

## Разработка

```bash
uv sync --group dev
pytest --cov=maze_book_generator --cov-report=term-missing
```

## Лицензия

GPL-3.0 — см. [LICENSE](LICENSE).
