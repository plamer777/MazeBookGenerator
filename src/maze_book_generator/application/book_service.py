"""Сервис генерации книг с лабиринтами."""

import math
from pathlib import Path

from maze_book_generator.container import container
from maze_book_generator.domain.maze import MazeGenerator
from maze_book_generator.domain.models import (
    Book,
    BookConfig,
    BookPage,
    Difficulty,
    DifficultyMode,
    MazeShape,
    Theme,
)
from maze_book_generator.infrastructure.hf_client import HFClient
from maze_book_generator.infrastructure.pdf_renderer import PDFRenderer
from maze_book_generator.infrastructure.pollinations_client import PollinationsClient
from maze_book_generator.infrastructure.replicate_client import ReplicateClient
from maze_book_generator.localization import BookTexts, Language
from maze_book_generator.settings import (
    BATCH_SIZE_VARIATION,
    BATCH_SIZE_VARIATION_THRESHOLD,
    BOOK_SEED_STRIDE,
    RANDOM_SEED_MAX,
    RANDOM_SEED_MIN,
    STORY_WAVE_AMPLITUDE,
    STORY_WAVE_TREND_SLOPE,
    settings,
)
from maze_book_generator.utils import create_rng


class BookService:
    """Сервис для генерации книг с лабиринтами с умными стратегиями сложности."""

    def __init__(self) -> None:
        """Инициализация сервиса с зависимостями из контейнера."""
        self._maze_generator = container.maze_generator
        self._pdf_renderer = container.pdf_renderer
        self._ai_client = container.ai_client
        self._mongodb_client = container.mongodb_client
        self._image_generator = container.image_generator
        self._preview_generator = container.preview_generator
        self._hf_client: HFClient = container.hf_client
        self._pollinations_client: PollinationsClient = container.pollinations_client
        self._replicate_client: ReplicateClient = container.replicate_client
        # Собственный RNG сервиса — не делит состояние с глобальным random
        # и с генераторами лабиринтов (у каждого свой seed).
        self._rng = create_rng()

    async def generate_book_with_ai_theme(
        self,
        book_id: int,
        pages_per_book: int,
        maze_size: tuple[int, int],
        difficulty_mode: DifficultyMode,
        base_difficulty: Difficulty = Difficulty.MEDIUM,
        language: Language = "en",
        book_config: BookConfig | None = None,
    ) -> Book:
        """
        Генерирует книгу с AI-генерированной темой и проверкой дедупликации.
        """
        effective_language = self._resolve_language(language, book_config)
        used_titles = self._mongodb_client.get_used_titles()
        age_range = (
            book_config.age_range if book_config and book_config.age_range
            else book_config.target_age if book_config and book_config.target_age
            else ("4-7 years" if effective_language == "en" else "4-7 лет")
        )
        theme = await self._ai_client.generate_theme(
            pages_per_book,
            used_titles=used_titles,
            language=effective_language,
            book_title_hint=book_config.title if book_config else None,
            theme_hint=book_config.theme_name if book_config else None,
            age_range=age_range,
            print_friendly=book_config.generate_print_friendly_version if book_config else False,
        )
        self._mongodb_client.save_theme(theme.book_title)

        return self.generate_book(
            book_id=book_id,
            theme=theme,
            pages_per_book=pages_per_book,
            maze_size=maze_size,
            difficulty_mode=difficulty_mode,
            base_difficulty=base_difficulty,
            language=effective_language,
            book_config=book_config,
        )

    def generate_book(
        self,
        book_id: int,
        theme: Theme,
        pages_per_book: int,
        maze_size: tuple[int, int],
        difficulty_mode: DifficultyMode,
        base_difficulty: Difficulty = Difficulty.MEDIUM,
        language: Language = "en",
        book_config: BookConfig | None = None,
    ) -> Book:
        """
        Генерирует книгу с лабиринтами на основе выбранной когнитивной стратегии.
        """
        effective_language = self._resolve_language(language, book_config)
        t = BookTexts(effective_language)
        answer_key_prompt = t.get("answer_key_prompt")
        effective_config = self._build_book_config(
            pages_per_book=pages_per_book,
            language=effective_language,
            theme=theme,
            base_difficulty=base_difficulty,
            config=book_config,
        )

        width, height = maze_size
        pages: list[BookPage] = []

        for page_num in range(1, pages_per_book + 1):
            # 1. Определяем сложность для конкретной страницы
            difficulty = self._get_page_difficulty(
                difficulty_mode,
                page_num,
                pages_per_book,
                base_difficulty,
            )

            # 2. Определяем форму лабиринта с учетом выбранной стратегии (адаптивно)
            shape = self._get_page_shape(page_num, pages_per_book, difficulty_mode)

            # Генерируем лабиринт
            maze = self._maze_generator.generate(width, height, difficulty, shape)

            # Получаем промпт для страницы
            prompt = self._get_page_prompt(theme, page_num - 1)

            # Создаём страницу с лабиринтом
            page = BookPage(
                maze=maze,
                title=f"Maze {page_num}",
                prompt=prompt,
                page_number=page_num,
                difficulty_label=self._difficulty_to_label(difficulty, t),
            )
            pages.append(page)

            # Создаём страницу с ответом
            solution_page = BookPage(
                maze=maze,
                title=f"Maze {page_num}",
                prompt=answer_key_prompt,
                page_number=page_num,
                is_solution=True,
                difficulty_label=page.difficulty_label,
            )
            pages.append(solution_page)

        output_dir = str(settings.OUTPUT_DIR / f"book_{book_id}")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        self._save_marketplace_info(
            output_dir=Path(output_dir),
            theme=theme,
            language=effective_language,
        )

        return Book(
            id=book_id,
            theme=theme,
            pages=pages,
            output_dir=output_dir,
            config=effective_config,
        )

    def _save_marketplace_info(self, output_dir: Path, theme: Theme, language: Language) -> None:
        """Сохраняет маркетинговые title/description в файл book_into.txt."""
        title = theme.marketplace_title or theme.book_title
        description = theme.marketplace_description or theme.book_description

        if language == "ru":
            content = (
                f"Заголовок для маркетплейса:\n{title}\n\n"
                f"Описание для маркетплейса:\n{description}\n"
            )
        else:
            content = (
                f"Marketplace title:\n{title}\n\n"
                f"Marketplace description:\n{description}\n"
            )

        info_path = output_dir / "book_into.txt"
        info_path.write_text(content, encoding="utf-8")

    def render_book_to_pdf(
        self,
        book: Book,
        language: Language = "en",
        book_config: BookConfig | None = None,
    ) -> Path:
        """Рендерит книгу в PDF файл."""
        effective_config = book_config or book.config
        effective_language = self._resolve_language(language, effective_config)
        output_path = Path(book.output_dir) / "book.pdf"
        renderer = PDFRenderer(language=effective_language, book_config=effective_config)
        renderer.render_book(book, output_path)

        if effective_config.generate_print_friendly_version:
            print_output_path = Path(book.output_dir) / "book_print_friendly.pdf"
            print_renderer = PDFRenderer(
                language=effective_language,
                book_config=effective_config,
                print_friendly=True,
            )
            print_renderer.render_book(book, print_output_path)

        return output_path

    def generate_page_illustrations(self, book: Book) -> list[Path | None]:
        """
        Генерирует иллюстрации и прокидывает пути в BookPage.

        Провайдеры по порядку: Replicate -> Pollinations -> Hugging Face.
        Использует image_keywords из Theme для каждой страницы.
        Пары страниц (maze + solution) используют одинаковую иллюстрацию.
        """
        keywords_per_page = book.theme.image_keywords or []
        unique_pages = [p for p in book.pages if not p.is_solution]
        unique_keywords = [
            keywords_per_page[p.page_number - 1]
            if p.page_number - 1 < len(keywords_per_page)
            else ["maze", "adventure"]
            for p in unique_pages
        ]
        book_dir = Path(book.output_dir)

        # 1. Основной провайдер — Replicate (качество + скорость)
        paths = self._replicate_client.generate_book_illustrations(
            image_keywords=unique_keywords,
            book_dir=book_dir,
        )

        # 2. Fallback — Pollinations для страниц, где Replicate вернул None
        failed_indices = [i for i, p in enumerate(paths) if p is None]
        if failed_indices:
            pollinations_keywords = [unique_keywords[i] for i in failed_indices]
            pollinations_paths = self._pollinations_client.generate_book_illustrations(
                image_keywords=pollinations_keywords,
                book_dir=book_dir,
            )
            for list_idx, original_idx in enumerate(failed_indices):
                paths[original_idx] = pollinations_paths[list_idx]

        # 3. Последний fallback — HF для оставшихся неуспешных
        failed_indices = [i for i, p in enumerate(paths) if p is None]
        if failed_indices:
            hf_keywords = [unique_keywords[i] for i in failed_indices]
            hf_paths = self._hf_client.generate_book_illustrations(
                image_keywords=hf_keywords,
                book_dir=book_dir,
            )
            for list_idx, original_idx in enumerate(failed_indices):
                paths[original_idx] = hf_paths[list_idx]

        for page, path in zip(unique_pages, paths, strict=True):
            if path is not None:
                str_path = str(path)
                page.image_path = str_path
                # Страница-ответ с тем же номером тоже получает путь
                for sol_page in book.pages:
                    if sol_page.page_number == page.page_number and sol_page.is_solution:
                        sol_page.image_path = str_path

        return paths

    async def generate_book_complete(
        self,
        book_id: int,
        pages_per_book: int,
        maze_size: tuple[int, int],
        difficulty_mode: DifficultyMode,
        base_difficulty: Difficulty = Difficulty.MEDIUM,
        language: Language = "en",
        book_config: BookConfig | None = None,
    ) -> Book:
        """Генерирует полную книгу со всеми медиа-файлами и превью."""
        effective_language = self._resolve_language(language, book_config)
        book = await self.generate_book_with_ai_theme(
            book_id=book_id,
            pages_per_book=pages_per_book,
            maze_size=maze_size,
            difficulty_mode=difficulty_mode,
            base_difficulty=base_difficulty,
            language=effective_language,
            book_config=book_config,
        )

        self.generate_page_illustrations(book)
        self.render_book_to_pdf(book, language=effective_language, book_config=book_config)
        self.generate_previews(book, language=effective_language)

        return book

    def generate_previews(self, book: Book, language: Language = "en") -> list[Path]:
        """Генерирует маркетинговые preview изображения для книги."""
        effective_language = self._resolve_language(language, book.config)
        output_dir = Path(book.output_dir)
        maze_count = sum(1 for p in book.pages if not p.is_solution)
        return self._preview_generator.generate_previews(
            output_dir, maze_count=maze_count, language=effective_language
        )

    async def generate_batch(
        self,
        number_of_books: int,
        pages_per_book: int,
        maze_size: tuple[int, int],
        difficulty_mode: DifficultyMode,
        base_seed: int | None = None,
        language: Language = "en",
        book_config: BookConfig | None = None,
    ) -> list[Book]:
        """
        Генерирует пачку книг в batch режиме с гарантированной уникальностью структур.

        Сложность и размер ротируются по книгам (EASY/MEDIUM/HARD), чтобы пачка
        была разнообразной — поэтому единой base_difficulty здесь нет.

        Args:
            number_of_books: Количество книг
            pages_per_book: Количество страниц
            maze_size: Базовый размер лабиринта
            difficulty_mode: Стратегия изменения сложности
            base_seed: Опциональный seed. Если None — каждый перезапуск скрипта абсолютно рандомен.
            language: Язык текста книги (ru или en)
            book_config: Опциональный конфиг с дополнительными параметрами для генерации книги
        """
        books: list[Book] = []
        if number_of_books <= 0 or pages_per_book <= 0:
            print("Кол-во книг и страниц в каждой книге должно быть больше 0")
            return books

        for local_idx in range(1, number_of_books + 1):
            book_id = self._next_free_book_id(settings.OUTPUT_DIR)
            print(f"Генерация книги {local_idx}/{number_of_books} (папка book_{book_id})...")

            size_variations = [
                (maze_size[0] - BATCH_SIZE_VARIATION, maze_size[1] - BATCH_SIZE_VARIATION) if maze_size[0] > BATCH_SIZE_VARIATION_THRESHOLD else maze_size,  # EASY
                (maze_size[0], maze_size[1]),  # MEDIUM
                (maze_size[0] + BATCH_SIZE_VARIATION, maze_size[1] + BATCH_SIZE_VARIATION),  # HARD
            ]
            current_maze_size = size_variations[(local_idx - 1) % len(size_variations)]

            difficulties = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
            current_difficulty = difficulties[(local_idx - 1) % len(difficulties)]

            # РЕШЕНИЕ ПРОБЛЕМЫ ПОВТОРОВ:
            # Если base_seed передан — генерируем воспроизводимую цепочку.
            # Если нет — берем случайное число, исключая повторение лабиринтов при перезапусках.
            current_seed = (
                base_seed + book_id * BOOK_SEED_STRIDE
                if base_seed is not None
                else self._rng.randint(RANDOM_SEED_MIN, RANDOM_SEED_MAX)
            )

            self._maze_generator = MazeGenerator(seed=current_seed)

            book = await self.generate_book_complete(
                book_id=book_id,
                pages_per_book=pages_per_book,
                maze_size=current_maze_size,
                difficulty_mode=difficulty_mode,
                base_difficulty=current_difficulty,
                language=language,
                book_config=book_config,
            )
            books.append(book)
            print(f"Книга {local_idx} завершена: {book.theme.book_title} [папка book_{book_id}] (seed: {current_seed})")

        return books

    @staticmethod
    def _next_free_book_id(output_dir: Path) -> int:
        """
        Возвращает следующий свободный номер папки book_N в директории вывода.

        Сканирует все естественные числа в существующих поддиректориях book_* и возвращает
        максимальный существующий + 1. Если папок нет — возвращает 1.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        existing: list[int] = []
        for entry in output_dir.iterdir():
            if entry.is_dir() and entry.name.startswith("book_"):
                suffix = entry.name[len("book_"):]
                if suffix.isdigit():
                    existing.append(int(suffix))
        return max(existing, default=0) + 1

    def _difficulty_to_label(self, difficulty: Difficulty, texts: BookTexts) -> str:
        """Возвращает локализованный читаемый уровень сложности."""
        if difficulty.level <= 2:
            return texts.get("difficulty_easy")
        if difficulty.level <= 4:
            return texts.get("difficulty_medium")
        return texts.get("difficulty_hard")

    def _build_book_config(
        self,
        pages_per_book: int,
        language: Language,
        theme: Theme,
        base_difficulty: Difficulty,
        config: BookConfig | None,
    ) -> BookConfig:
        """Собирает итоговую конфигурацию книги с безопасными дефолтами."""
        effective_language = self._resolve_language(language, config)
        t = BookTexts(effective_language)

        if config is None:
            return BookConfig(
                language=effective_language,
                title=theme.book_title,
                subtitle=t.get("subtitle"),
                theme_name=theme.book_title,
                maze_count=pages_per_book,
                difficulty_label=self._difficulty_to_label(base_difficulty, t),
            )

        return BookConfig(
            language=effective_language,
            title=config.title or theme.book_title,
            subtitle=config.subtitle or t.get("subtitle"),
            theme_name=config.theme_name or theme.book_title,
            age_range=config.age_range,
            target_age=config.target_age,
            child_name=config.child_name,
            child_age=config.child_age,
            maze_count=config.maze_count or pages_per_book,
            include_contents_page=config.include_contents_page,
            show_start_finish_labels=config.show_start_finish_labels,
            generate_print_friendly_version=config.generate_print_friendly_version,
            difficulty_label=config.difficulty_label or self._difficulty_to_label(base_difficulty, t),
        )

    @staticmethod
    def _resolve_language(language: Language, config: BookConfig | None) -> Language:
        """Определяет итоговый язык: приоритет у BookConfig, параметр language — fallback."""
        return config.language if config else language

    # ------------------------------------------------------------------
    # Внутренние алгоритмы распределения сложности и геометрии
    # ------------------------------------------------------------------

    def _get_page_difficulty(
        self,
        mode: DifficultyMode,
        page_num: int,
        total_pages: int,
        base_difficulty: Difficulty,
    ) -> Difficulty:
        """Реализует расширенные когнитивные стратегии распределения сложности."""
        # Безопасное приведение к строке для поддержки и Enum, и кастомных конфигураций
        mode_str = mode.name if hasattr(mode, "name") else str(mode)

        all_levels = [
            Difficulty.L1, Difficulty.L2, Difficulty.L3, Difficulty.L4,
            Difficulty.L5, Difficulty.L6, Difficulty.L7,
        ]

        if mode_str == "FIXED":
            selected = base_difficulty

        elif mode_str == "INCREMENTAL":
            progress = (page_num - 1) / max(total_pages - 1, 1)
            index = round(progress * (len(all_levels) - 1))
            selected = all_levels[index]

        elif mode_str == "RANDOM_RANGE":
            selected = self._rng.choice(all_levels)

        elif mode_str == "KIDS_EASY":
            # Стратегия для малышей: строго самые простые и понятные структуры
            selected = self._rng.choice([Difficulty.L1, Difficulty.L2])

        elif mode_str == "CHALLENGE_HARD":
            # Стратегия для продвинутых детей: только хардкор
            selected = self._rng.choice([Difficulty.L5, Difficulty.L6, Difficulty.L7])

        elif mode_str == "STORY_WAVE":
            # Волнообразная нагрузка с общим восходящим трендом (предотвращает утомление)
            progress = (page_num - 1) / max(total_pages - 1, 1)
            base_idx = progress * STORY_WAVE_TREND_SLOPE  # Базовый тренд медленно растет
            wave_modifier = math.sin(page_num * STORY_WAVE_AMPLITUDE) * STORY_WAVE_AMPLITUDE  # Периодические колебания вверх-вниз

            index = max(0, min(6, round(base_idx + wave_modifier + STORY_WAVE_AMPLITUDE)))
            selected = all_levels[index]

        else:
            selected = base_difficulty

        return selected

    def _get_page_shape(self, page_num: int, total_pages: int, mode: DifficultyMode) -> MazeShape:
        """Подбирает оптимальную форму лабиринта, соответствующую когнитивной нагрузке."""
        mode_str = mode.name if hasattr(mode, "name") else str(mode)

        if mode_str in ("KIDS_EASY", "KIDS_SIMPLE"):
            # Для малышей убираем запутывающие сетки (круглые, треугольные, хаотичные).
            # Оставляем только простые и хорошо читаемые формы.
            return self._rng.choice([MazeShape.RECTANGULAR, MazeShape.SQUARE, MazeShape.DIAMOND])

        if mode_str in ("CHALLENGE_HARD", "MEGA_HARD"):
            # Для экспертов сразу выкатываем сложные альтернативные топологии
            complex_shapes = [
                MazeShape.TRIANGULAR,
                MazeShape.CIRCULAR,
                MazeShape.CHAOTIC,
                MazeShape.RANDOM,
                MazeShape.DIAMOND,
                MazeShape.HEART,
            ]
            return complex_shapes[(page_num - 1) % len(complex_shapes)]

        if mode_str == "INCREMENTAL":
            # Эволюция форм: от простых к сложным по мере пролистывания книги
            progress = (page_num - 1) / max(total_pages - 1, 1)
            if progress < 0.35:
                return self._rng.choice([MazeShape.RECTANGULAR, MazeShape.SQUARE, MazeShape.DIAMOND])
            if progress < 0.70:
                return self._rng.choice([MazeShape.SQUARE, MazeShape.CIRCULAR, MazeShape.TRIANGULAR, MazeShape.DIAMOND])
            return self._rng.choice(
                [
                    MazeShape.CIRCULAR,
                    MazeShape.TRIANGULAR,
                    MazeShape.CHAOTIC,
                    MazeShape.RANDOM,
                    MazeShape.DIAMOND,
                    MazeShape.HEART,
                ]
            )

        # Дефолтное классическое чередование для FIXED и RANDOM_RANGE
        shapes = [
            MazeShape.RECTANGULAR,
            MazeShape.SQUARE,
            MazeShape.TRIANGULAR,
            MazeShape.CIRCULAR,
            MazeShape.RANDOM,
            MazeShape.CHAOTIC,
            MazeShape.DIAMOND,
            MazeShape.HEART,
        ]
        return shapes[(page_num - 1) % len(shapes)]

    def _get_page_prompt(self, theme: Theme, index: int) -> str:
        """Получает текст задания для страницы из темы."""
        if index < len(theme.page_prompts):
            return theme.page_prompts[index].task
        return f"Find the path through maze {index + 1}"