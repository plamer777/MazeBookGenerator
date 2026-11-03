"""Сервис генерации книг с лабиринтами — оркестрация сценариев.

Сборка страниц и стратегии сложности — в book_factory,
маркетплейс-артефакты — в marketplace, иллюстрации — в illustration_pipeline.
"""

import logging
from dataclasses import replace
from pathlib import Path

from maze_book_generator.application.book_factory import (
    BookSpec,
    build_book_config,
    build_pages,
    resolve_language,
)
from maze_book_generator.application.illustration_pipeline import (
    IllustrationPipeline,
    assign_illustration_paths,
)
from maze_book_generator.application.marketplace import (
    next_free_book_id,
    save_marketplace_info,
)
from maze_book_generator.container import container
from maze_book_generator.domain.maze import MazeGenerator
from maze_book_generator.domain.models import (
    Book,
    BookConfig,
    Difficulty,
    Theme,
)
from maze_book_generator.infrastructure.ai_client import ThemeHints
from maze_book_generator.infrastructure.pdf import PDFRenderer
from maze_book_generator.localization import BookTexts, Language
from maze_book_generator.settings import (
    BATCH_SIZE_VARIATION,
    BATCH_SIZE_VARIATION_THRESHOLD,
    BOOK_SEED_STRIDE,
    RANDOM_SEED_MAX,
    RANDOM_SEED_MIN,
    settings,
)
from maze_book_generator.utils import create_rng

logger = logging.getLogger(__name__)


class BookService:
    """Сервис для генерации книг с лабиринтами с умными стратегиями сложности."""

    def __init__(self) -> None:
        """Инициализация сервиса с зависимостями из контейнера."""
        self._maze_generator = container.maze_generator
        self._ai_client = container.ai_client
        self._theme_repository = container.theme_repository
        self._preview_generator = container.preview_generator
        # Цепочка провайдеров иллюстраций: основной -> fallback -> последний шанс
        self._illustrations = IllustrationPipeline(
            [
                container.replicate_client,
                container.pollinations_client,
                container.hf_client,
            ]
        )
        # Собственный RNG сервиса — не делит состояние с глобальным random
        # и с генераторами лабиринтов (у каждого свой seed).
        self._rng = create_rng()

    async def generate_book_with_ai_theme(
        self,
        book_id: int,
        spec: BookSpec,
    ) -> Book:
        """Генерирует книгу с AI-генерированной темой и проверкой дедупликации."""
        effective_language = resolve_language(spec.language, spec.book_config)
        theme = await self._ai_client.generate_theme(
            spec.pages_per_book,
            used_titles=self._theme_repository.get_used_titles(),
            language=effective_language,
            hints=ThemeHints(
                book_title_hint=spec.book_config.title if spec.book_config else None,
                theme_hint=spec.book_config.theme_name if spec.book_config else None,
                age_range=self._age_range(spec.book_config, effective_language),
                print_friendly=spec.book_config.generate_print_friendly_version
                if spec.book_config
                else False,
            ),
        )
        self._theme_repository.save_theme(theme.book_title)

        return self.generate_book(book_id=book_id, theme=theme, spec=spec)

    @staticmethod
    def _age_range(config: BookConfig | None, language: Language) -> str:
        """Возвращает возрастной диапазон из конфига или локализованный дефолт."""
        if config and config.age_range:
            return config.age_range
        if config and config.target_age:
            return config.target_age
        return "4-7 years" if language == "en" else "4-7 лет"

    def generate_book(
        self,
        book_id: int,
        theme: Theme,
        spec: BookSpec,
    ) -> Book:
        """Генерирует книгу с лабиринтами на основе выбранной когнитивной стратегии."""
        effective_language = resolve_language(spec.language, spec.book_config)
        texts = BookTexts(effective_language)
        effective_config = build_book_config(
            pages_per_book=spec.pages_per_book,
            language=effective_language,
            theme=theme,
            base_difficulty=spec.base_difficulty,
            config=spec.book_config,
        )

        pages = build_pages(self._maze_generator, theme, spec, self._rng, texts)

        output_dir = str(settings.OUTPUT_DIR / f"book_{book_id}")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        save_marketplace_info(Path(output_dir), theme, effective_language)

        return Book(
            id=book_id,
            theme=theme,
            pages=pages,
            output_dir=output_dir,
            config=effective_config,
        )

    def render_book_to_pdf(
        self,
        book: Book,
        language: Language = "en",
        book_config: BookConfig | None = None,
    ) -> Path:
        """Рендерит книгу в PDF файл."""
        effective_config = book_config or book.config
        effective_language = resolve_language(language, effective_config)
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

        paths = self._illustrations.generate(unique_keywords, Path(book.output_dir))
        assign_illustration_paths(book, paths)
        return paths

    async def generate_book_complete(
        self,
        book_id: int,
        spec: BookSpec,
        *,
        with_illustrations: bool = True,
        with_previews: bool = True,
    ) -> Book:
        """Генерирует полную книгу со всеми медиа-файлами и превью."""
        effective_language = resolve_language(spec.language, spec.book_config)
        book = await self.generate_book_with_ai_theme(book_id=book_id, spec=spec)

        if with_illustrations:
            self.generate_page_illustrations(book)
        self.render_book_to_pdf(
            book, language=effective_language, book_config=spec.book_config
        )
        if with_previews:
            self.generate_previews(book, language=effective_language)

        return book

    def generate_previews(self, book: Book, language: Language = "en") -> list[Path]:
        """Генерирует маркетинговые preview изображения для книги."""
        effective_language = resolve_language(language, book.config)
        output_dir = Path(book.output_dir)
        maze_count = sum(1 for p in book.pages if not p.is_solution)
        return self._preview_generator.generate_previews(
            output_dir, maze_count=maze_count, language=effective_language
        )

    async def generate_batch(
        self,
        spec: BookSpec,
        number_of_books: int,
        base_seed: int | None = None,
        *,
        with_illustrations: bool = True,
        with_previews: bool = True,
    ) -> list[Book]:
        """
        Генерирует пачку книг в batch режиме с гарантированной уникальностью структур.

        Сложность и размер ротируются по книгам (EASY/MEDIUM/HARD), чтобы пачка
        была разнообразной — поэтому base_difficulty из spec игнорируется.

        Args:
            spec: Параметры генерации одной книги
            number_of_books: Количество книг
            base_seed: Опциональный seed. Если None — каждый запуск рандомен.

        Returns:
            Список сгенерированных книг
        """
        books: list[Book] = []
        if number_of_books <= 0 or spec.pages_per_book <= 0:
            print("Кол-во книг и страниц в каждой книге должно быть больше 0")
            return books

        width, height = spec.maze_size
        size_variations = [
            (width - BATCH_SIZE_VARIATION, height - BATCH_SIZE_VARIATION)
            if width > BATCH_SIZE_VARIATION_THRESHOLD
            else spec.maze_size,
            spec.maze_size,
            (width + BATCH_SIZE_VARIATION, height + BATCH_SIZE_VARIATION),
        ]
        difficulties = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]

        for local_idx in range(1, number_of_books + 1):
            book_id = next_free_book_id(settings.OUTPUT_DIR)
            print(f"Генерация книги {local_idx}/{number_of_books} (папка book_{book_id})...")

            # РЕШЕНИЕ ПРОБЛЕМЫ ПОВТОРОВ:
            # Если base_seed передан — генерируем воспроизводимую цепочку.
            # Если нет — берем случайное число, исключая повторы при перезапусках.
            current_seed = (
                base_seed + book_id * BOOK_SEED_STRIDE
                if base_seed is not None
                else self._rng.randint(RANDOM_SEED_MIN, RANDOM_SEED_MAX)
            )
            self._maze_generator = MazeGenerator(seed=current_seed)

            book_spec = replace(
                spec,
                maze_size=size_variations[(local_idx - 1) % len(size_variations)],
                base_difficulty=difficulties[(local_idx - 1) % len(difficulties)],
            )
            book = await self.generate_book_complete(
                book_id=book_id,
                spec=book_spec,
                with_illustrations=with_illustrations,
                with_previews=with_previews,
            )
            books.append(book)
            print(
                f"Книга {local_idx} завершена: {book.theme.book_title} "
                f"[папка book_{book_id}] (seed: {current_seed})"
            )

        return books
