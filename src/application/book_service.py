"""Сервис генерации книг с лабиринтами."""

import math
import random
from pathlib import Path
from typing import Tuple

from src.container import container
from src.domain.maze_generator import MazeGenerator
from src.domain.models import (
    Book,
    BookPage,
    Difficulty,
    DifficultyMode,
    MazeShape,
    PagePrompt,
    Theme,
)
from src.infrastructure.hf_client import HFClient
from src.settings import settings


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

    async def generate_book_with_ai_theme(
        self,
        book_id: int,
        pages_per_book: int,
        maze_size: Tuple[int, int],
        difficulty_mode: DifficultyMode,
        base_difficulty: Difficulty = Difficulty.MEDIUM,
    ) -> Book:
        """
        Генерирует книгу с AI-генерированной темой и проверкой дедупликации.
        """
        used_titles = self._mongodb_client.get_used_titles()
        theme = await self._ai_client.generate_theme(pages_per_book, used_titles=used_titles)
        self._mongodb_client.save_theme(theme.book_title)

        return self.generate_book(
            book_id=book_id,
            theme=theme,
            pages_per_book=pages_per_book,
            maze_size=maze_size,
            difficulty_mode=difficulty_mode,
            base_difficulty=base_difficulty,
        )

    def generate_book(
        self,
        book_id: int,
        theme: Theme,
        pages_per_book: int,
        maze_size: Tuple[int, int],
        difficulty_mode: DifficultyMode,
        base_difficulty: Difficulty = Difficulty.MEDIUM,
    ) -> Book:
        """
        Генерирует книгу с лабиринтами на основе выбранной когнитивной стратегии.
        """
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
            )
            pages.append(page)

            # Создаём страницу с ответом
            solution_page = BookPage(
                maze=maze,
                title=f"Maze {page_num}",
                prompt="Answer Key",
                page_number=page_num,
            )
            pages.append(solution_page)

        output_dir = str(settings.OUTPUT_DIR / f"book_{book_id}")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        return Book(
            id=book_id,
            theme=theme,
            pages=pages,
            output_dir=output_dir,
        )

    def render_book_to_pdf(self, book: Book) -> Path:
        """Рендерит книгу в PDF файл."""
        output_path = Path(book.output_dir) / "book.pdf"
        self._pdf_renderer.render_book(book, output_path)
        return output_path

    def generate_page_illustrations(self, book: Book) -> list[Path | None]:
        """
        Генерирует иллюстрации через Hugging Face и прокидывает пути в BookPage.

        Использует image_keywords из Theme для каждой страницы.
        Пары страниц (maze + solution) используют одинаковую иллюстрацию.
        """
        keywords_per_page = book.theme.image_keywords or []
        unique_pages = [p for p in book.pages if p.prompt != "Answer Key"]
        unique_keywords = [
            keywords_per_page[p.page_number - 1]
            if p.page_number - 1 < len(keywords_per_page)
            else ["maze", "adventure"]
            for p in unique_pages
        ]
        print(f'Keywords: {keywords_per_page}, {unique_keywords}')
        paths = self._hf_client.generate_book_illustrations(
            image_keywords=unique_keywords,
            book_dir=Path(book.output_dir),
        )
        print(f'Image paths: {paths}')
        for page, path in zip(unique_pages, paths):
            if path is not None:
                str_path = str(path)
                page.image_path = str_path
                # Страница-ответ с тем же номером тоже получает путь
                for sol_page in book.pages:
                    if sol_page.page_number == page.page_number and sol_page.prompt == "Answer Key":
                        sol_page.image_path = str_path

        return paths

    async def generate_book_complete(
        self,
        book_id: int,
        pages_per_book: int,
        maze_size: Tuple[int, int],
        difficulty_mode: DifficultyMode,
        base_difficulty: Difficulty = Difficulty.MEDIUM,
    ) -> Book:
        """Генерирует полную книгу со всеми медиа-файлами и превью."""
        book = await self.generate_book_with_ai_theme(
            book_id=book_id,
            pages_per_book=pages_per_book,
            maze_size=maze_size,
            difficulty_mode=difficulty_mode,
            base_difficulty=base_difficulty,
        )

        self.generate_page_illustrations(book)
        self.render_book_to_pdf(book)
        self.generate_previews(book)

        return book

    def generate_previews(self, book: Book) -> list[Path]:
        """Генерирует маркетинговые preview изображения для книги."""
        output_dir = Path(book.output_dir)
        return self._preview_generator.generate_previews(output_dir)

    async def generate_batch(
        self,
        number_of_books: int,
        pages_per_book: int,
        maze_size: Tuple[int, int],
        difficulty_mode: DifficultyMode,
        base_difficulty: Difficulty = Difficulty.MEDIUM,
        base_seed: int | None = None,
    ) -> list[Book]:
        """
        Генерирует пачку книг в batch режиме с гарантированной уникальностью структур.

        Args:
            number_of_books: Количество книг
            pages_per_book: Количество страниц
            maze_size: Базовый размер лабиринта
            difficulty_mode: Стратегия изменения сложности
            base_difficulty: Начальная сложность
            base_seed: Опциональный seed. Если None — каждый перезапуск скрипта абсолютно рандомен.
        """
        books: list[Book] = []

        for book_id in range(1, number_of_books + 1):
            print(f"Генерация книги {book_id}/{number_of_books}...")

            size_variations = [
                (maze_size[0] - 2, maze_size[1] - 2) if maze_size[0] > 12 else maze_size,  # EASY
                (maze_size[0], maze_size[1]),  # MEDIUM
                (maze_size[0] + 2, maze_size[1] + 2),  # HARD
            ]
            current_maze_size = size_variations[(book_id - 1) % len(size_variations)]

            difficulties = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
            current_difficulty = difficulties[(book_id - 1) % len(difficulties)]

            # РЕШЕНИЕ ПРОБЛЕМЫ ПОВТОРОВ:
            # Если base_seed передан — генерируем воспроизводимую цепочку.
            # Если нет — берем случайное число, исключая повторение лабиринтов при перезапусках.
            if base_seed is not None:
                current_seed = base_seed + book_id * 1337
            else:
                current_seed = random.randint(1, 999999999)

            self._maze_generator = MazeGenerator(seed=current_seed)

            book = await self.generate_book_complete(
                book_id=book_id,
                pages_per_book=pages_per_book,
                maze_size=current_maze_size,
                difficulty_mode=difficulty_mode,
                base_difficulty=current_difficulty,
            )
            books.append(book)
            print(f"Книга {book_id} завершена: {book.theme.book_title} (seed: {current_seed})")

        return books

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
            return base_difficulty

        elif mode_str == "INCREMENTAL":
            progress = (page_num - 1) / max(total_pages - 1, 1)
            index = round(progress * (len(all_levels) - 1))
            return all_levels[index]

        elif mode_str == "RANDOM_RANGE":
            return random.choice(all_levels)

        elif mode_str == "KIDS_EASY":
            # Стратегия для малышей: строго самые простые и понятные структуры
            return random.choice([Difficulty.L1, Difficulty.L2])

        elif mode_str == "CHALLENGE_HARD":
            # Стратегия для продвинутых детей: только хардкор
            return random.choice([Difficulty.L5, Difficulty.L6, Difficulty.L7])

        elif mode_str == "STORY_WAVE":
            # Волнообразная нагрузка с общим восходящим трендом (предотвращает утомление)
            progress = (page_num - 1) / max(total_pages - 1, 1)
            base_idx = progress * 3.5  # Базовый тренд медленно растет
            wave_modifier = math.sin(page_num * 1.5) * 1.5  # Периодические колебания вверх-вниз

            index = max(0, min(6, round(base_idx + wave_modifier + 1.5)))
            return all_levels[index]

        return base_difficulty

    def _get_page_shape(self, page_num: int, total_pages: int, mode: DifficultyMode) -> MazeShape:
        """Подбирает оптимальную форму лабиринта, соответствующую когнитивной нагрузке."""
        mode_str = mode.name if hasattr(mode, "name") else str(mode)

        if mode_str in ("KIDS_EASY", "KIDS_SIMPLE"):
            # Для малышей убираем запутывающие сетки (круглые, треугольные, хаотичные).
            # Оставляем только простые и хорошо читаемые формы.
            return random.choice([MazeShape.RECTANGULAR, MazeShape.SQUARE, MazeShape.DIAMOND])

        elif mode_str in ("CHALLENGE_HARD", "MEGA_HARD"):
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

        elif mode_str == "INCREMENTAL":
            # Эволюция форм: от простых к сложным по мере пролистывания книги
            progress = (page_num - 1) / max(total_pages - 1, 1)
            if progress < 0.35:
                return random.choice([MazeShape.RECTANGULAR, MazeShape.SQUARE, MazeShape.DIAMOND])
            elif progress < 0.70:
                return random.choice([MazeShape.SQUARE, MazeShape.CIRCULAR, MazeShape.TRIANGULAR, MazeShape.DIAMOND])
            else:
                return random.choice(
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