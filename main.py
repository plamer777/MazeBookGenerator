"""EntryPoint для MazeBookGenerator - тестирование Phase 4 (batch + preview)."""

import asyncio

from src.application.book_service import BookService
from src.application.config_presets import PRESETS, personalized
from src.container import container
from src.domain.models import Difficulty, DifficultyMode


async def main() -> None:
    """Запускает batch генерацию книг с preview изображениями."""
    # Инициализируем сервис
    service = BookService()

    # Параметры генерации
    number_of_books = 1
    mazes_per_book = 30
    maze_size = (15, 11)
    difficulty_mode = DifficultyMode.KIDS_EASY
    base_difficulty = Difficulty.EASY

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
    books = await service.generate_batch(
        number_of_books=number_of_books,
        pages_per_book=mazes_per_book,
        maze_size=maze_size,
        difficulty_mode=difficulty_mode,
        base_difficulty=base_difficulty,
        book_config=book_config,
    )

    print(f"\nГенерация завершена! Создано {len(books)} книг:")
    for book in books:
        print(f"  - Book {book.id}: {book.theme.book_title}")

    # Закрываем соединение с MongoDB
    container.mongodb_client.close()


if __name__ == "__main__":
    asyncio.run(main())