"""Контекст рендеринга PDF: геометрия страницы, шрифты, тексты и конфигурация."""

from __future__ import annotations

from dataclasses import dataclass

from reportlab.lib.units import mm

from maze_book_generator.domain.models import BookConfig
from maze_book_generator.localization import BookTexts, Language
from maze_book_generator.settings import settings


@dataclass(frozen=True, slots=True)
class RenderContext:
    """Неизменяемые параметры рендеринга, общие для всех страниц и элементов PDF."""

    page_width: float
    page_height: float
    margin: float
    cell_size: float
    texts: BookTexts
    config: BookConfig
    print_friendly: bool
    font: str = "DejaVuSans"
    font_bold: str = "DejaVuSans-Bold"

    @classmethod
    def create(
        cls,
        language: Language = "en",
        book_config: BookConfig | None = None,
        print_friendly: bool = False,
    ) -> RenderContext:
        """Создаёт контекст с параметрами страницы из settings."""
        return cls(
            page_width=settings.PDF_PAGE_WIDTH * mm,
            page_height=settings.PDF_PAGE_HEIGHT * mm,
            margin=settings.PDF_MARGIN * mm,
            cell_size=settings.DEFAULT_CELL_SIZE * mm,
            texts=BookTexts(language),
            config=book_config or BookConfig(language=language),
            print_friendly=print_friendly,
        )
