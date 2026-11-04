"""Передние страницы книги: содержание и вводная страница с правилами."""

import math

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from maze_book_generator.domain.models import Book
from maze_book_generator.infrastructure.pdf import cover, text
from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.drawing import markers
from maze_book_generator.infrastructure.pdf.params import TextBlock


def render_contents_page(ctx: RenderContext, c: canvas.Canvas, book: Book) -> None:
    """Рендерит страницу "What's Inside / Что внутри"."""
    _, _, accent = cover.cover_palette(cover.book_title(ctx, book))
    bg = (1.0, 1.0, 1.0) if ctx.print_friendly else (0.98, 0.98, 1.0)
    c.setFillColorRGB(*bg)
    c.rect(0, 0, ctx.page_width, ctx.page_height, fill=1, stroke=0)

    margin = 16 * mm
    c.setStrokeColorRGB(*accent)
    c.setLineWidth(2.0)
    c.roundRect(
        margin,
        margin,
        ctx.page_width - 2 * margin,
        ctx.page_height - 2 * margin,
        radius=6 * mm,
        fill=0,
        stroke=1,
    )

    title = ctx.texts.get("contents_heading")
    c.setFillColorRGB(*accent)
    c.setFont(ctx.font_bold, 26)
    tw = c.stringWidth(title, ctx.font_bold, 26)
    c.drawString((ctx.page_width - tw) / 2, ctx.page_height - 38 * mm, title)

    lines = [
        ctx.texts.format("contents_theme", value=ctx.config.theme_name or book.theme.book_title),
        ctx.texts.format("contents_language", value=cover.book_language_label(ctx)),
        ctx.texts.format("contents_mazes", count=cover.book_maze_count(ctx, book)),
        ctx.texts.get("contents_answers"),
        ctx.texts.get("contents_printable"),
    ]
    if ctx.config.difficulty_label:
        lines.append(ctx.texts.format("contents_difficulty", value=ctx.config.difficulty_label))
    if ctx.config.child_name:
        lines.append(ctx.texts.format("contents_child", name=ctx.config.child_name))
    if ctx.config.child_age:
        lines.append(ctx.texts.format("contents_child_age", age=ctx.config.child_age))

    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.setFont(ctx.font, 14)
    y = ctx.page_height - 58 * mm
    for line in lines:
        c.drawString(34 * mm, y, f"• {line}")
        y -= 8 * mm



def render_intro_page(ctx: RenderContext, c: canvas.Canvas, book: Book) -> None:
    """
    Рендерит страницу с введением и правилами (страница 2 книги).

    Простой минималистичный дизайн с дружелюбным локализованным текстом.

    Args:
        ctx: Контекст рендеринга (палитра, размеры страницы, print_friendly)
        c: Canvas для рисования
        book: Объект книги
    """
    _, _, accent = cover.cover_palette(book.theme.book_title)

    # --- Фон ---
    bg = (1.0, 1.0, 1.0) if ctx.print_friendly else (0.98, 0.98, 1.0)
    c.setFillColorRGB(*bg)
    c.rect(0, 0, ctx.page_width, ctx.page_height, fill=1, stroke=0)

    # --- Простая рамка ---
    margin = 15 * mm
    c.setStrokeColorRGB(*accent)
    c.setLineWidth(2.0)
    c.rect(margin, margin, ctx.page_width - 2 * margin, ctx.page_height - 2 * margin, fill=0, stroke=1)

    # --- Заголовок ---
    c.setFillColorRGB(*accent)
    c.setFont(ctx.font_bold, 28)
    title = ctx.texts.get("intro_heading")
    tw = c.stringWidth(title, ctx.font_bold, 28)
    c.drawString((ctx.page_width - tw) / 2, ctx.page_height - 40 * mm, title)

    # --- Текст правил ---
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.setFont(ctx.font, 14)

    intro_text = ctx.texts.get("intro_body")
    text.draw_centered_wrapped_text(ctx, c, TextBlock(
        text=intro_text,
        font_name=ctx.font,
        font_size=14,
        start_y=ctx.page_height - 65 * mm,
        max_width=ctx.page_width - 70 * mm,
        line_height=6 * mm,
        max_height=ctx.page_height - 110 * mm,
        min_font_size=11,
    ))

    render_intro_legend(ctx, c, accent, margin)

    # --- Декоративный элемент внизу ---
    c.setStrokeColorRGB(*accent)
    c.setLineWidth(1.5)
    c.line(margin + 20 * mm, margin + 15 * mm, ctx.page_width - margin - 20 * mm, margin + 15 * mm)



def render_intro_legend(ctx: RenderContext, c: canvas.Canvas, accent: tuple[float, float, float], margin: float) -> None:
    """Рисует компактную легенду START/FINISH на странице инструкции."""
    legend_title = ctx.texts.get("intro_legend_title")
    start_label = ctx.texts.get("intro_legend_start")
    finish_label = ctx.texts.get("intro_legend_finish")

    base_y = margin + 30 * mm
    c.setFillColorRGB(*accent)
    c.setFont(ctx.font_bold, 14)
    c.drawString(margin + 16 * mm, base_y + 11 * mm, legend_title)

    marker_size = 3.3 * mm
    start_x = margin + 24 * mm
    finish_x = margin + 86 * mm

    markers.draw_triangle_marker(c, start_x, base_y + 3 * mm, marker_size, angle=math.pi / 2, color=(0, 0.75, 0))
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.setFont(ctx.font_bold, 11)
    c.drawString(start_x + 7 * mm, base_y + 1 * mm, start_label)

    markers.draw_triangle_marker(c, finish_x, base_y + 3 * mm, marker_size, angle=-math.pi / 2, color=(0.9, 0, 0))
    c.drawString(finish_x + 7 * mm, base_y + 1 * mm, finish_label)

