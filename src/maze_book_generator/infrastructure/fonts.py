"""Поиск системных шрифтов по списку кандидатных путей."""

from pathlib import Path

from maze_book_generator.settings import (
    FONT_DEJAVU_BOLD_CANDIDATES,
    FONT_DEJAVU_REGULAR_CANDIDATES,
)


def find_font_path(candidates: list[str]) -> str | None:
    """Возвращает первый существующий путь из кандидатов или None."""
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    return None


def find_dejavu_regular() -> str | None:
    """Ищет DejaVuSans.ttf среди кандидатных путей."""
    return find_font_path(FONT_DEJAVU_REGULAR_CANDIDATES)


def find_dejavu_bold() -> str | None:
    """Ищет DejaVuSans-Bold.ttf среди кандидатных путей."""
    return find_font_path(FONT_DEJAVU_BOLD_CANDIDATES)
