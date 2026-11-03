"""Подготовка директорий вывода книг."""

from pathlib import Path

from maze_book_generator.settings import settings


def book_output_dir(book_id: int) -> Path:
    """Создаёт (при необходимости) и возвращает папку output/book_N."""
    path = settings.OUTPUT_DIR / f"book_{book_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_dir(path: Path) -> Path:
    """Создаёт директорию (с родителями) и возвращает её путь."""
    path.mkdir(parents=True, exist_ok=True)
    return path
