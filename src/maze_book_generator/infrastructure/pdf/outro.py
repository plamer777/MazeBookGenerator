"""Финальная страница книги с коллажем и напутствием."""

from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from maze_book_generator.domain.models import Book
from maze_book_generator.infrastructure.pdf import cover, images, text
from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.params import Rect, TextBlock
from maze_book_generator.settings import IMAGE_STORAGE_SUBDIR, WATERMARK_ALPHA


def render_outro_page(ctx: RenderContext, c: canvas.Canvas, book: Book) -> None:
    """
    Рендерит последнюю страницу с коллажем иллюстраций и напутствием.

    Args:
        ctx: Контекст рендеринга (палитра, размеры страницы, print_friendly)
        c: Canvas для рисования
        book: Объект книги
    """
    _, _, accent = cover.cover_palette(book.theme.book_title)

    bg = (1.0, 1.0, 1.0) if ctx.print_friendly else (0.95, 0.95, 1.0)
    c.setFillColorRGB(*bg)
    c.rect(0, 0, ctx.page_width, ctx.page_height, fill=1, stroke=0)

    if not ctx.print_friendly:
        illustrations_dir = Path(book.output_dir) / IMAGE_STORAGE_SUBDIR
        collage_seed = book.id * 1009 + sum(ord(ch) for ch in book.theme.book_title)
        images.render_image_collage(
            ctx, c, illustrations_dir,
            alpha=WATERMARK_ALPHA, seed=collage_seed,
        )

    # Полупрозрачная плашка по центру с текстом напутствия
    box_margin = 30 * mm
    box_h = 36 * mm + 14 * mm
    plaque = Rect(box_margin, ctx.page_height / 2 - box_h / 2,
                  ctx.page_width - 2 * box_margin, box_h)

    _draw_outro_plaque(c, accent, plaque)
    title_y = _draw_outro_title(ctx, c, accent, plaque.y + plaque.height - 7 * mm)
    _draw_outro_body(ctx, c, title_y)
    _draw_outro_signature(ctx, c, accent, book)



def _draw_outro_plaque(c: canvas.Canvas,
    accent: tuple[float, float, float],
    plaque: Rect,
) -> None:
    """Рисует полупрозрачную плашку с акцентной рамкой под текст outro."""
    c.saveState()
    c.setFillColorRGB(1, 1, 1)
    c.setFillAlpha(0.85)
    c.roundRect(plaque.x, plaque.y, plaque.width, plaque.height,
                radius=8 * mm, fill=1, stroke=0)
    c.restoreState()

    c.setStrokeColorRGB(*accent)
    c.setLineWidth(2.0)
    c.roundRect(plaque.x, plaque.y, plaque.width, plaque.height,
                radius=8 * mm, fill=0, stroke=1)



def _draw_outro_title(ctx: RenderContext,
    c: canvas.Canvas,
    accent: tuple[float, float, float],
    content_top: float,
) -> float:
    """Рисует заголовок напутствия. Возвращает baseline заголовка."""
    title_font_size = 24
    title_y = content_top - title_font_size * 0.4
    c.setFillColorRGB(*accent)
    c.setFont(ctx.font_bold, title_font_size)
    title = (
        ctx.texts.format("outro_heading_personal", name=ctx.config.child_name)
        if ctx.config.child_name
        else ctx.texts.get("outro_heading")
    )
    tw = c.stringWidth(title, ctx.font_bold, title_font_size)
    c.drawString((ctx.page_width - tw) / 2, title_y, title)
    return title_y


def _draw_outro_body(ctx: RenderContext, c: canvas.Canvas, title_y: float) -> None:
    """Рисует многострочный текст напутствия под заголовком."""
    c.setFillColorRGB(0.3, 0.3, 0.3)
    text.draw_centered_wrapped_text(ctx, c, TextBlock(
        text=ctx.texts.get("outro_body"),
        font_name=ctx.font,
        font_size=14,
        start_y=title_y - 9 * mm,
        max_width=ctx.page_width - 90 * mm,
        line_height=5.5 * mm,
        max_height=36 * mm - 24 * 0.4 - 9 * mm,
        min_font_size=11,
    ))



def _draw_outro_signature(ctx: RenderContext,
    c: canvas.Canvas,
    accent: tuple[float, float, float],
    book: Book,
) -> None:
    """Рисует подпись с названием книги в правом нижнем углу."""
    signature = ctx.texts.format("outro_signature", book_title=cover.book_title(ctx, book))
    sig_font_size = 10
    sig_margin = 10 * mm
    c.saveState()
    c.setFillColorRGB(*accent)
    c.setFillAlpha(0.65)
    c.setFont(ctx.font, sig_font_size)
    sw = c.stringWidth(signature, ctx.font, sig_font_size)
    c.drawString(ctx.page_width - sig_margin - sw, sig_margin, signature)
    c.restoreState()
