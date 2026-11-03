# MazeBookGenerator

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
- Локализация EN/RU, пресеты конфигураций книг
- Print-friendly версия PDF для печати

## Установка

```bash
# uv (рекомендуется)
uv sync

# или pip
pip install -e .
```

Скопируйте `.env.example` в `.env` и заполните API-ключи (опционально —
без них используются fallback-данные).

## Использование

```bash
mazebook generate --books 1 --pages 30 --size 15x11 \
    --preset ru_kids_easy --difficulty KIDS_EASY
```

Результат — в `output/book_N/`: `book.pdf`, иллюстрации, preview,
`book_into.txt` с маркетинговыми текстами.

## Разработка

```bash
pytest --cov=maze_book_generator --cov-report=term-missing
quality-gate all
```

## Лицензия

GPL-3.0 — см. [LICENSE](LICENSE).
