# План рефакторинга MazeBookGenerator → публикация на GitHub

Дата аудита: 2026-11-03. Инструмент: `quality-gate` 0.2.0 (Codex-Quality-Checker),
конфиг `quality-gate.toml` (permanent, tracked), отчёты `.quality-gate/reports/`.

## Принятые решения

| Вопрос | Решение |
|---|---|
| Раскладка пакета | `src/maze_book_generator/` (канонический src-layout) |
| Имя пакета/проекта | `maze_book_generator` / `maze-book-generator` |
| Python floor | `>=3.12` (pyright target 3.12) |
| Лицензия | GPL-3.0 |
| Тесты | миграция unittest → pytest (+pytest-asyncio) |
| MongoDB | `ThemeRepository` Protocol + JSON-fallback по умолчанию |
| CLI | argparse (stdlib), дефолты из текущего main.py |
| Шумные правила | `RUF002`, `RUF003` → ignore (русские docstrings по AGENTS.md) |

## Исходные метрики (baseline до рефакторинга)

- ruff: 822 findings (366 production / 456 tests)
- constants: 15 CFG001/CFG002
- pylint: 11 (2× too-many-lines, 9× too-many-public-methods, 1× duplicate-code)
- pyright / import_linter / semgrep: 0
- Тесты: 162 проходят, но 4 async-теста `test_ai_client.py` молча не выполняются
- `output/` трекается в git (~8.5MB бинарных артефактов)
- Нет: README, LICENSE, .env.example, CLI, упаковки (pip install невозможен)

## Принципы (Чистый код)

- Одна функция — одно действие; >3 параметров → dataclass/params-object
- Dispatch через `dict[Enum, Strategy]` вместо `elif`-цепочек
- Говорящие имена констант вместо магических чисел и комментариев-костылей
- Никакого глобального изменяемого состояния (`random.seed()` запрещён — только `random.Random`)
- Зависимости только через `Container` (AGENTS.md §2.4)
- Русский язык в комментариях и docstrings (AGENTS.md §1)

## Целевая структура

```
src/maze_book_generator/
  __init__.py
  __main__.py                 # python -m maze_book_generator
  cli.py                      # argparse: generate + флаги
  settings.py                 # Settings + ВСЕ константы
  localization.py             # BookTexts + TEXTS (allowed_file для constants)
  container.py                # Container (фабрики, ленивые property)
  domain/
    models.py                 # dataclasses/enums (StrEnum, builtin generics)
    page_plan.py              # стратегии сложности и формы (из book_service)
    maze/
      __init__.py             # re-export MazeGenerator
      generator.py            # фасад: generate(), dispatch по формам,
                              # тонкие _generate_* оркестраторы grid-форм
      masks.py                # фабрики масок форм (вкл. хаотичную
                              # connected-маску)
      carving.py              # DFS-прорезание, петли, bias по сложности,
                              # chaotic-shortcuts
      solver.py               # BFS-решение, валидация
      polar.py                # полярная генерация + PolarTopologyService
                              # (отдельная топология: граф, не сетка)
  application/
    book_service.py           # только оркестрация сценариев
    book_factory.py           # сборка Book/BookPage
    illustration_pipeline.py  # цепочка провайдеров Replicate→Pollinations→HF
    marketplace.py            # book_into.txt, распределение book_id
    config_presets.py
  infrastructure/
    pdf/
      __init__.py             # re-export PDFRenderer
      context.py              # RenderContext dataclass
      fonts.py                # регистрация DejaVu (пути из settings)
      renderer.py             # render_book — сборка canvas
      cover.py                # обложка (раскатать 44-locals монстра)
      front_pages.py          # contents + intro
      maze_pages.py           # страницы лабиринт/ответ
      decorations.py          # рамки, орнаменты
      images.py               # watermark + коллаж
      outro.py
      drawing/
        grid.py               # rect/square/triangular/masked/chaotic
        polar.py              # дуги, сегменты, polar path
        markers.py            # start/end маркеры, подписи
    preview/
      generator.py            # PreviewGenerator (509 строк — допустимо одним файлом)
    images/
      providers.py            # IllustrationProvider Protocol + rate-limit helper
      replicate.py pollinations.py hf.py
      placeholder.py          # ImageGenerator (PIL-заглушки)
    storage/
      theme_repository.py     # Protocol + JsonThemeRepository + MongoThemeRepository
tests/                        # pytest, зеркалит структуру src
```

## Этапы

### Этап 0 — Гигиена репозитория
- ✅ Корень переименован `PythonProject` → `MazeBookGenerator`,
  service name в `quality-gate.toml` → `maze-book-generator`
- `git rm -r --cached output` (файлы остаются на диске)
- `AGENTS.md` остаётся локальным (игнорируется, в git не коммитим) —
  файл рабочего процесса разработки, не часть продукта
- `LICENSE` (GPL-3.0), `.env.example`, `README.md`-скелет
- pyproject: ✅ `name = "maze-book-generator"`, description, authors,
  `license = "GPL-3.0-only"`, `readme`, `requires-python = ">=3.12"`,
  `[project.scripts] mazebook`, hatchling wheel config

### Этап 1 — Страховочная сеть (pytest)
- dev-зависимости: `pytest`, `pytest-asyncio`, `pytest-cov`
- `tests/__init__.py` не нужен для pytest — удалить pycache-мусор
- unittest.TestCase → функции/fixtures; async → `@pytest.mark.asyncio`
  (чинит 4 мёртвых async-теста); PT009/PT027 закроются сами
- Покрытие: `pytest --cov=maze_book_generator --cov-report=term-missing
  --cov-fail-under=80`; порог **≥80%** — если стартовый процент ниже,
  добить тестами до порога на этом же этапе; badge в README (quality-gate
  coverage-gate ещё не реализован — Stage 7 roadmap, считаем сами)
- Верификация: `pytest` зелёный, `quality-gate audit`

### Этап 2 — Пакет + механические правки (один «шумный» коммит)
- `git mv src src/maze_book_generator` (+`__init__.py`), замена `from src.` → `from maze_book_generator.`
- `Dict/Set/Tuple/Optional` → builtins/`|`; `str+Enum` → `StrEnum`; F401/F841; I001;
  `zip(strict=True)`; `utcnow()`→`now(UTC)`; `assert`→исключения; SIM/RET/PERF/E701
- `quality-gate.toml`: `ignore += ["RUF002", "RUF003"]`
- `quality-gate audit --update-baseline` → закоммитить baseline
- Верификация: pytest зелёный

### Этап 3 — Константы + RNG
- В settings: `DEJAVU_FONT_*`, `HF_API_BASE`, `HTTP_TIMEOUT`, `POLLINATIONS_BASE_URL`,
  геометрия/цвета preview. `src/.../localization.py` → `constant_policy.allowed_files`
- `MazeGenerator(seed)` → `self._rng = random.Random(seed)`; весь `random.*` → `self._rng.*`
  (убирает глобальную мутацию RNG и ~35 S311)
- Магические числа → константы: `MAZE_GRID_SCALE_MIN/MAX` (0.45/2.0), `BOOK_SEED_STRIDE` (1337),
  `RANDOM_SEED_MAX` (999999999), `SIZE_VARIATION` (±2), `LARGE_MAZE_THRESHOLD` (12),
  `WAVE_TREND_SLOPE`/`WAVE_AMPLITUDE` (3.5/1.5), `FALLBACK_IMAGE_KEYWORDS`
- Верификация: `quality-gate changed` — 0 новых findings; CFG001/002 → 0

### Этап 4 — Domain-декомпозиция
- Разнести `maze_generator.py` по структуре выше; `MazeGenerator` держит `rng`,
  dispatch по `MazeShape`. Принцип разделения: **одна топология = один пайплайн** —
  все grid-формы (включая CHAOTIC) это «маска → прорезание → петли → солвер»
  и различаются только фабрикой маски; хаотичная логика (`_create_chaotic_connected_mask`,
  `_add_chaotic_shortcuts`) уходит в `masks.py`/`carving.py`. Polar — отдельная
  топология (граф соединений, не сетка) и остаётся в `polar.py`
- `PolarTopologyService` → `domain/maze/polar.py` (рядом с потребителем);
  13 public methods → сгруппировать/убавить до ≤12
- `_get_page_difficulty` + `_get_page_shape` → `domain/page_plan.py`:
  `PagePlanStrategy` Protocol, реализации per DifficultyMode, `dict` dispatch
- assert→исключения; PLR0914/1702 рассасываются декомпозицией
- Верификация: pytest зелёный (генерация идентична по seed!), `quality-gate all` —
  C0302 для maze_generator снят

### Этап 5 — PDF-декомпозиция
- `RenderContext` dataclass (геометрия, шрифты, texts, config, print_friendly)
- Разнести pdf_renderer по таблице; `_render_cover` (44 locals/102 stmts) →
  `_draw_cover_background` / `_fit_title_layout` / `_draw_maze_preview` / `_draw_cover_labels`
- `MazeDrawParams` dataclass для сигнатур 7–9 аргументов (PLR0913/0917)
- Верификация: PDF побайтово/визуально сопоставим на фиксированном seed;
  pytest зелёный; pylint C0302 снят, C901/PLR09xx → 0

### Этап 6 — Application + провода
- book_service → оркестрация; сборка страниц → book_factory;
  `_save_marketplace_info`/`_next_free_book_id` → marketplace.py
- `IllustrationPipeline`: единый цикл «заполнить None по цепочке провайдеров»;
  общий `generate_batch_with_rate_limit` в providers.py (убирает дубль R0801)
- `ThemeRepository`: JsonThemeRepository по умолчанию (`output/used_themes.json`),
  MongoThemeRepository при доступном MONGODB_URI; выбор в Container
- `except Exception` → конкретные типы + logger; `try/except/pass` → `contextlib.suppress`
  только осознанно; неиспользуемые аргументы — замкнуть или убрать
- Верификация: pytest зелёный, `quality-gate all`

### Этап 7 — CLI + финал
- `cli.py`: `mazebook generate --books 1 --pages 30 --size 15x11
  --preset ru_kids_easy --difficulty KIDS_EASY --seed N --no-images --no-print-friendly`
- `main.py` → тонкий shim `cli.main()`; `__main__.py` для `python -m`
- README: установка (uv/pip), quickstart CLI, пресеты, структура, license badge
- Добить docstrings публичных API; `quality-gate all` → baseline commit → push

### Этап 8 — Независимая приёмка (reviewer-агент)
- После зелёного `quality-gate all` + pytest + coverage ≥80% запускается
  **независимый reviewer-агент** (read-only: `subagent_explore` или
  `ao review trigger`), который проверяет без права правки:
  - соответствие кода этому плану и принципам Чистого кода
    (имена, длина функций, dispatch вместо elif-цепочек, отсутствие
    глобального состояния)
  - архитектуру: domain/application/infrastructure не смешаны,
    зависимости через Container, константы в settings.py
  - полноту README, LICENSE, .env.example, CLI-справки
  - отсутствие секретов/артефактов в tracked-файлах
  - регрессию генерации по фиксированному seed
- Reviewer только **собирает замечания** списком; исправления вносит
  отдельный воркер. Цикл «замечания → фикс → повторное ревью» до чистого
  заключения

## Правила приёмки (для оркестратора/воркеров)

1. Каждый этап = отдельный коммит; pytest зелёный обязателен
2. `quality-gate changed` после каждого шага — ноль НОВЫХ findings (ratchet)
3. baseline обновляется только на этапе 2 и в финале
4. Генерация по фиксированному seed до/после этапов 4–5 должна давать
   идентичные лабиринты (регрессионный тест, не только линтер)
5. Нельзя расширять exclude/baseline ради сокрытия находки — только перенос/исправление
6. Покрытие тестами ≥80% (`--cov-fail-under=80` в CI/приёмке). При
   декомпозиции тесты либо следуют за кодом, либо пишутся новые на
   выделенные модули — порог держать на каждом этапе, не только в финале
