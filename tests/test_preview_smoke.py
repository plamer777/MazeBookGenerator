"""Smoke-тесты PreviewGenerator: генерация preview-пакета из реального book.pdf."""

from pathlib import Path

import pytest
from PIL import Image

from maze_book_generator.domain.maze import MazeGenerator
from maze_book_generator.domain.models import (
    Book,
    BookConfig,
    BookPage,
    Difficulty,
    MazeShape,
    PagePrompt,
    Theme,
)
from maze_book_generator.infrastructure.pdf_renderer import PDFRenderer
from maze_book_generator.infrastructure.preview_generator import PreviewGenerator


def _render_book(tmp_path: Path, language: str = "en") -> Path:
    """Рендерит маленькую книгу и возвращает директорию с book.pdf."""
    generator = MazeGenerator(seed=42)
    maze = generator.generate(10, 8, Difficulty.MEDIUM, MazeShape.RECTANGULAR)

    image_path = tmp_path / "illustration_1.png"
    Image.new("RGB", (120, 90), color=(240, 230, 200)).save(image_path)

    pages = [
        BookPage(
            maze=maze, title="Maze 1", prompt="Task 1",
            page_number=1, image_path=str(image_path),
        ),
        BookPage(
            maze=maze, title="Maze 1", prompt="Answer Key",
            page_number=1, image_path=str(image_path), is_solution=True,
        ),
    ]
    theme = Theme(
        book_title="Preview Book",
        book_description="desc",
        page_prompts=[PagePrompt(task="Task 1", heroes=[])],
        image_keywords=[["maze"]],
    )
    config = BookConfig(language=language)
    book = Book(id=1, theme=theme, pages=pages, output_dir=str(tmp_path), config=config)

    PDFRenderer(language=language, book_config=config).render_book(
        book, tmp_path / "book.pdf"
    )
    return tmp_path


@pytest.mark.parametrize("language", ["en", "ru"])
def test_generate_previews_full_pack(tmp_path: Path, language: str) -> None:
    """Полный пакет preview должен содержать валидные PNG-файлы."""
    book_dir = _render_book(tmp_path, language)

    paths = PreviewGenerator().generate_previews(book_dir, maze_count=1, language=language)

    assert len(paths) >= 4  # spread + collage + answer + promo (cover/page mini при наличии)
    for path in paths:
        assert path.exists()
        with Image.open(path) as img:
            assert img.format == "PNG"
            assert img.width > 0
            assert img.height > 0


def test_generate_previews_without_pdf(tmp_path: Path) -> None:
    """Без book.pdf превью должны строиться на заглушках без падения."""
    paths = PreviewGenerator().generate_previews(tmp_path, maze_count=0, language="en")

    # spread и collage генерируются всегда (на заглушках)
    assert len(paths) >= 2
    for path in paths:
        assert path.exists()
