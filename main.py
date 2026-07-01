"""EntryPoint для MazeBookGenerator - тестирование Phase 4 (batch + preview)."""

import asyncio

from src.application.book_service import BookService
from src.container import container
from src.domain.models import Difficulty, DifficultyMode


async def main() -> None:
    """Запускает batch генерацию книг с preview изображениями."""
    # Инициализируем сервис
    service = BookService()

    # Параметры генерации
    number_of_books = 1
    pages_per_book = 40
    maze_size = (15, 11)
    difficulty_mode = DifficultyMode.INCREMENTAL
    base_difficulty = Difficulty.MEDIUM
    language = "en"  # "en" или "ru"

    print(f"Начинаем batch генерацию {number_of_books} книг...")
    print(f"Параметры: {pages_per_book} страниц, размер {maze_size}, режим {difficulty_mode}, язык: {language}")

    # Генерируем batch книг
    books = await service.generate_batch(
        number_of_books=number_of_books,
        pages_per_book=pages_per_book,
        maze_size=maze_size,
        difficulty_mode=difficulty_mode,
        base_difficulty=base_difficulty,
        language=language,
    )

    print(f"\nГенерация завершена! Создано {len(books)} книг:")
    for book in books:
        print(f"  - Book {book.id}: {book.theme.book_title}")

    # Закрываем соединение с MongoDB
    container.mongodb_client.close()


if __name__ == "__main__":
    asyncio.run(main())