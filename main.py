"""EntryPoint для MazeBookGenerator - тестирование Phase 4 (batch + preview)."""

import asyncio

from maze_book_generator.application.book_factory import BookSpec
from maze_book_generator.application.book_service import BookService
from maze_book_generator.application.config_presets import PRESETS
from maze_book_generator.container import container
from maze_book_generator.domain.models import DifficultyMode


async def main() -> None:
    """Запускает batch генерацию книг с preview изображениями."""
    # Инициализируем сервис
    service = BookService()

    # Параметры генерации
    number_of_books = 1
    mazes_per_book = 30
    maze_size = (15, 11)
    difficulty_mode = DifficultyMode.KIDS_EASY

    # Выбираем пресет конфигурации книги.
    # Доступные пресеты: en_kids_basic, en_kids_printable, en_school, en_school_printable,
    #                    en_challenge, ru_kids_basic, ru_kids_printable, ru_school,
    #                    ru_school_printable, ru_challenge
    # Для персонализации: personalized("en_kids_basic", child_name="Emma", child_age="6")
    book_config = PRESETS["ru_kids_easy"]

    print(f"Начинаем batch генерацию {number_of_books} книг...")
    print(
        f"Параметры: {mazes_per_book} лабиринтов, размер {maze_size}, режим {difficulty_mode}, "
        f"язык: {book_config.language}"
    )

    # Генерируем batch книг
    spec = BookSpec(
        pages_per_book=mazes_per_book,
        maze_size=maze_size,
        difficulty_mode=difficulty_mode,
        book_config=book_config,
    )
    books = await service.generate_batch(spec, number_of_books=number_of_books)

    print(f"\nГенерация завершена! Создано {len(books)} книг:")
    for book in books:
        print(f"  - Book {book.id}: {book.theme.book_title}")

    # Закрываем хранилище тем (для JSON — no-op)
    container.theme_repository.close()


if __name__ == "__main__":
    asyncio.run(main())