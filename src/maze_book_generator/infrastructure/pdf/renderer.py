"""Фасад рендерера PDF: сборка документа книги из отдельных страниц."""

from pathlib import Path

from reportlab.pdfgen import canvas

from maze_book_generator.domain.models import Book, BookConfig
from maze_book_generator.infrastructure.pdf import cover, front_pages, maze_pages, outro
from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.fonts import register_fonts
from maze_book_generator.localization import Language


class PDFRenderer:
    """Рендерер PDF документов с лабиринтами."""

    def __init__(
        self,
        language: Language = "en",
        book_config: BookConfig | None = None,
        print_friendly: bool = False,
    ) -> None:
        """Инициализация рендерера: регистрация шрифтов и контекст страницы."""
        register_fonts()
        self._ctx = RenderContext.create(language, book_config, print_friendly)

    @property
    def ctx(self) -> RenderContext:
        """Контекст рендеринга (геометрия, тексты, конфигурация)."""
        return self._ctx

    def render_book(self, book: Book, output_path: Path) -> None:
        """
        Рендерит полную книгу в PDF файл.

        Args:
            book: Объект книги с лабиринтами
            output_path: Путь для сохранения PDF
        """
        ctx = self._ctx
        c = canvas.Canvas(str(output_path), pagesize=(ctx.page_width, ctx.page_height))

        # Обложка
        cover.render_cover(ctx, c, book)
        c.showPage()

        if ctx.config.include_contents_page:
            front_pages.render_contents_page(ctx, c, book)
            c.showPage()

        # Страница с введением и правилами
        front_pages.render_intro_page(ctx, c, book)
        c.showPage()

        # Страницы с лабиринтами
        for page in book.pages:
            if page.is_solution:
                maze_pages.render_solution_page(ctx, c, page, book.theme.book_title)
            else:
                maze_pages.render_maze_page(ctx, c, page, book.theme.book_title)
            c.showPage()

        # Последняя страница с коллажем и напутствием
        outro.render_outro_page(ctx, c, book)

        c.save()
