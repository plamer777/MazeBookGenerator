"""Маркетплейс-артефакты книги: book_into.txt и распределение book_id."""

from __future__ import annotations

from pathlib import Path

from maze_book_generator.domain.models import Theme
from maze_book_generator.localization import Language


def save_marketplace_info(output_dir: Path, theme: Theme, language: Language) -> None:
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


def next_free_book_id(output_dir: Path) -> int:
    """
    Возвращает следующий свободный номер папки book_N в директории вывода.

    Сканирует поддиректории book_* и возвращает максимальный суффикс + 1.
    Если папок нет — возвращает 1.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = [
        int(suffix)
        for entry in output_dir.iterdir()
        if entry.is_dir()
        and entry.name.startswith("book_")
        and (suffix := entry.name[len("book_"):]).isdigit()
    ]
    return max(existing, default=0) + 1
