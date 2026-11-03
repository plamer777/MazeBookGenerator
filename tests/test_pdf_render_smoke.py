"""Smoke-тесты реального рендеринга PDF: проверяют, что книга собирается
до валидного PDF-файла без исключений на всех формах и конфигурациях."""

from pathlib import Path

import pytest
from PIL import Image

from maze_book_generator.application.config_presets import PRESETS
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

ALL_SHAPES = list(MazeShape)


def _make_book(
    shapes: list[MazeShape],
    config: BookConfig,
    tmp_path: Path,
    with_images: bool = False,
) -> Book:
    """Собирает маленькую книгу из реальных лабиринтов заданных форм."""
    generator = MazeGenerator(seed=42)
    pages: list[BookPage] = []

    for idx, shape in enumerate(shapes, start=1):
        maze = generator.generate(10, 8, Difficulty.MEDIUM, shape)

        image_path = None
        if with_images:
            image_path = str(tmp_path / f"illustration_{idx}.png")
            Image.new("RGB", (120, 90), color=(240, 230, 200)).save(image_path)

        pages.append(BookPage(
            maze=maze,
            title=f"Maze {idx}",
            prompt=f"Task {idx}",
            page_number=idx,
            image_path=image_path,
        ))
        pages.append(BookPage(
            maze=maze,
            title=f"Maze {idx}",
            prompt="Answer Key",
            page_number=idx,
            image_path=image_path,
            is_solution=True,
        ))

    theme = Theme(
        book_title="Smoke Test Book",
        book_description="Test description",
        page_prompts=[PagePrompt(task=f"Task {i}", heroes=[]) for i in range(len(shapes))],
        image_keywords=[["maze"] for _ in shapes],
    )
    return Book(id=1, theme=theme, pages=pages, output_dir=str(tmp_path), config=config)


def _assert_valid_pdf(path: Path) -> None:
    """Проверяет, что файл существует и начинается с PDF-сигнатуры."""
    assert path.exists()
    data = path.read_bytes()
    assert data[:5] == b"%PDF-"
    assert len(data) > 1000


@pytest.mark.parametrize("shape", ALL_SHAPES)
def test_render_book_all_shapes(tmp_path: Path, shape: MazeShape) -> None:
    """Каждая форма лабиринта должна рендериться в валидный PDF."""
    config = BookConfig(language="en")
    book = _make_book([shape], config, tmp_path)
    output = tmp_path / f"book_{shape.value}.pdf"

    PDFRenderer(language="en", book_config=config).render_book(book, output)

    _assert_valid_pdf(output)


def test_render_book_print_friendly(tmp_path: Path) -> None:
    """Print-friendly вариант должен рендериться для grid и polar форм."""
    config = BookConfig(language="en")
    book = _make_book([MazeShape.RECTANGULAR, MazeShape.CIRCULAR], config, tmp_path)
    output = tmp_path / "book_print.pdf"

    PDFRenderer(language="en", book_config=config, print_friendly=True).render_book(book, output)

    _assert_valid_pdf(output)


def test_render_book_with_illustrations(tmp_path: Path) -> None:
    """Страницы с image_path должны рендерить watermark и коллаж outro."""
    config = BookConfig(language="en")
    book = _make_book(
        [MazeShape.RECTANGULAR, MazeShape.CIRCULAR],
        config,
        tmp_path,
        with_images=True,
    )
    output = tmp_path / "book_images.pdf"

    PDFRenderer(language="en", book_config=config).render_book(book, output)

    _assert_valid_pdf(output)


def test_render_book_russian_language(tmp_path: Path) -> None:
    """Русская локализация должна рендериться без ошибок шрифтов."""
    config = BookConfig(language="ru", subtitle="Книга лабиринтов", age_range="4-5")
    book = _make_book([MazeShape.RECTANGULAR], config, tmp_path)
    output = tmp_path / "book_ru.pdf"

    PDFRenderer(language="ru", book_config=config).render_book(book, output)

    _assert_valid_pdf(output)


def test_render_book_personalized_cover(tmp_path: Path) -> None:
    """Обложка с именем ребёнка и возрастом должна рендериться."""
    config = BookConfig(
        language="en",
        title="Custom Book Title That Is Fairly Long",
        child_name="Emma",
        child_age="6",
        age_range="4-7 years",
    )
    book = _make_book([MazeShape.DIAMOND], config, tmp_path)
    output = tmp_path / "book_personalized.pdf"

    PDFRenderer(language="en", book_config=config).render_book(book, output)

    _assert_valid_pdf(output)


def test_render_book_without_contents_page(tmp_path: Path) -> None:
    """Книга без contents-страницы должна рендериться."""
    config = BookConfig(language="en", include_contents_page=False)
    book = _make_book([MazeShape.SQUARE], config, tmp_path)
    output = tmp_path / "book_no_contents.pdf"

    PDFRenderer(language="en", book_config=config).render_book(book, output)

    _assert_valid_pdf(output)


@pytest.mark.parametrize("preset_name", sorted(PRESETS))
def test_render_book_each_preset(tmp_path: Path, preset_name: str) -> None:
    """Каждый пресет конфигурации должен рендериться в валидный PDF."""
    config = PRESETS[preset_name]
    book = _make_book([MazeShape.RECTANGULAR], config, tmp_path)
    output = tmp_path / f"book_{preset_name}.pdf"

    PDFRenderer(language=config.language, book_config=config).render_book(book, output)

    _assert_valid_pdf(output)
