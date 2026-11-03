"""Финальная страница книги с коллажем и напутствием."""

from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from maze_book_generator.domain.models import Book
from maze_book_generator.infrastructure.pdf import cover, images, text
from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.params import TextBlock
from maze_book_generator.settings import WATERMARK_ALPHA


def render_outro_page(ctx: RenderContext, c: canvas.Canvas, book: Book) -> None:
    """
    Рендерит последнюю страницу с коллажем иллюстраций и напутствием.

    Args:
        c: Canvas для рисования
        book: Объект книги
    """
    _, _, accent = cover.cover_palette(book.theme.book_title)

    # --- Фон ---
    bg = (1.0, 1.0, 1.0) if ctx.print_friendly else (0.95, 0.95, 1.0)
    c.setFillColorRGB(*bg)
    c.rect(0, 0, ctx.page_width, ctx.page_height, fill=1, stroke=0)

    # --- Коллаж изображений ---
    if not ctx.print_friendly:
        illustrations_dir = Path(book.output_dir) / "illustrations"
        collage_seed = book.id * 1009 + sum(ord(ch) for ch in book.theme.book_title)
        images.render_image_collage(ctx, 
            c,
            illustrations_dir,
            alpha=WATERMARK_ALPHA,
            seed=collage_seed,
        )

    # --- Полупрозрачная плашка под текстом ---
    # padding — симметричный внутренний отступ от рамки до контента сверху и снизу
    padding = 7 * mm
    content_h = 36 * mm  # высота зоны контента (заголовок + тело текста)
    box_h = content_h + 2 * padding
    box_margin = 30 * mm
    # Центр плашки совпадает с центром страницы
    center_y = ctx.page_height / 2
    box_bottom = center_y - box_h / 2
    # Верхняя граница контента: верх плашки минус padding
    content_top = box_bottom + box_h - padding

    c.saveState()
    c.setFillColorRGB(1, 1, 1)
    c.setFillAlpha(0.85)
    c.roundRect(box_margin, box_bottom,
                ctx.page_width - 2 * box_margin, box_h,
                radius=8 * mm, fill=1, stroke=0)
    c.restoreState()

    # --- Рамка плашки ---
    c.setStrokeColorRGB(*accent)
    c.setLineWidth(2.0)
    c.roundRect(box_margin, box_bottom,
                ctx.page_width - 2 * box_margin, box_h,
                radius=8 * mm, fill=0, stroke=1)

    # --- Текст напутствия ---
    # Заголовок прижат к верху контентной зоны
    title_font_size = 24
    title_y = content_top - title_font_size * 0.4  # baseline чуть ниже верхней границы
    c.setFillColorRGB(*accent)
    c.setFont(ctx.font_bold, title_font_size)
    title = (
        ctx.texts.format("outro_heading_personal", name=ctx.config.child_name)
        if ctx.config.child_name
        else ctx.texts.get("outro_heading")
    )
    tw = c.stringWidth(title, ctx.font_bold, title_font_size)
    c.drawString((ctx.page_width - tw) / 2, title_y, title)

    # Тело текста начинается через один интервал ниже заголовка
    body_start_y = title_y - 9 * mm
    c.setFillColorRGB(0.3, 0.3, 0.3)
    outro_text = ctx.texts.get("outro_body")
    text.draw_centered_wrapped_text(ctx, c, TextBlock(
        text=outro_text,
        font_name=ctx.font,
        font_size=14,
        start_y=body_start_y,
        max_width=ctx.page_width - 90 * mm,
        line_height=5.5 * mm,
        max_height=content_h - title_font_size * 0.4 - 9 * mm,
        min_font_size=11,
    ))

    # --- Подпись в правом нижнем углу страницы ---
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

