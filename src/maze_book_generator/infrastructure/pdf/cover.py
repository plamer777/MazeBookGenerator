"""Рендеринг обложки книги: палитра, заголовок, информационный блок."""

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from maze_book_generator.domain.models import Book
from maze_book_generator.infrastructure.pdf import decorations, text
from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.utils import format_count_with_plural_ru


def cover_palette(seed: str) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    """
    Генерирует детерминированную палитру из 3 цветов по строке-ключу.

    Возвращает (bg_top, bg_bottom, accent) — цвета фона и акцента.

    Args:
        seed: Строка-источник (например, название книги)

    Returns:
        Кортеж из трёх RGB-цветов (0..1)
    """
    palettes = [
        ((0.10, 0.15, 0.35), (0.20, 0.30, 0.55), (0.95, 0.70, 0.10)),  # синий + золото
        ((0.08, 0.28, 0.15), (0.15, 0.42, 0.28), (0.95, 0.65, 0.05)),  # зелёный + золото
        ((0.38, 0.08, 0.12), (0.55, 0.15, 0.20), (1.00, 0.55, 0.05)),  # бордо + яркий оранже
        ((0.12, 0.22, 0.42), (0.25, 0.42, 0.62), (1.00, 0.55, 0.10)),  # стальной + оранжевый
        ((0.22, 0.08, 0.42), (0.38, 0.18, 0.58), (0.95, 0.40, 0.85)),  # фиолетовый + мажента
    ]
    idx = sum(ord(ch) for ch in seed) % len(palettes)
    return palettes[idx]



def book_title(ctx: RenderContext, book: Book) -> str:
    """Возвращает отображаемое название книги с учётом BookConfig."""
    return ctx.config.title or book.theme.book_title



def book_subtitle(ctx: RenderContext) -> str:
    """Возвращает подзаголовок книги с учётом BookConfig."""
    return ctx.config.subtitle or ctx.texts.get("subtitle")



def book_maze_count(ctx: RenderContext, book: Book) -> int:
    """Возвращает количество лабиринтов в книге."""
    if ctx.config.maze_count is not None:
        return ctx.config.maze_count
    return sum(1 for page in book.pages if not page.is_solution)



def book_age_label(ctx: RenderContext) -> str | None:
    """Возвращает подпись возрастного диапазона для обложки/contents."""
    age_value = ctx.config.age_range or ctx.config.target_age
    if not age_value:
        return None
    return ctx.texts.format("cover_age", age=age_value)



def cover_mazes_label(ctx: RenderContext, count: int) -> str:
    """Возвращает подпись количества лабиринтов для обложки с учетом локали."""
    if ctx.config.language == "ru":
        return format_count_with_plural_ru(
            count=count,
            forms=("лабиринт", "лабиринта", "лабиринтов"),
            text_case="lower",
        )
    return ctx.texts.format("cover_mazes", count=count)



def book_language_label(ctx: RenderContext) -> str:
    """Возвращает локализованное имя языка книги."""
    return ctx.texts.get("cover_language")



def fit_cover_title_layout(ctx: RenderContext,
    c: canvas.Canvas,
    title: str,
    max_width: float,
    max_lines: int = 5,
    *,
    max_title_block_height: float | None = None,
) -> tuple[int, list[str]]:
    """Подбирает размер шрифта и переносы строк для заголовка обложки."""
    min_size = 18
    for font_size in range(34, min_size - 1, -1):
        lines = text.wrap_text_to_width(c, title, ctx.font_bold, font_size, max_width)
        line_height = font_size * 1.2
        title_block_h = len(lines) * line_height
        if len(lines) <= max_lines and (
            max_title_block_height is None or title_block_h <= max_title_block_height
        ):
            return font_size, lines

    fallback_lines = text.wrap_text_to_width(c, title, ctx.font_bold, min_size, max_width)
    return min_size, fallback_lines



def render_cover(ctx: RenderContext, c: canvas.Canvas, book: Book) -> None:
    """
    Рендерит обложку книги.

    Структура (сверху вниз):
    - Цветной фон (двухцветный вертикальный градиент через полосы)
    - Паттерн-полоса из лабиринтных ячеек вверху и внизу
    - Рамка-меандр по периметру
    - Название книги с тенью по центру
    - Подзаголовок «Maze Book»

    Args:
        c: Canvas для рисования
        book: Объект книги
    """
    title = book_title(ctx, book)
    bg_top, bg_bottom, accent = cover_palette(title)
    cover_accent = (0.0, 0.0, 0.0) if ctx.print_friendly else accent

    _draw_cover_background(ctx, c, bg_top, bg_bottom, accent)
    decorations.render_meander_border(ctx, c, cover_accent)
    _draw_cover_text_block(ctx, c, book, title, cover_accent)

    if not ctx.print_friendly:
        decorations.render_corner_ornaments(ctx, c, accent)



def _draw_cover_background(ctx: RenderContext,
    c: canvas.Canvas,
    bg_top: tuple[float, float, float],
    bg_bottom: tuple[float, float, float],
    accent: tuple[float, float, float],
) -> None:
    """Рисует фон обложки: градиент и лабиринтные полосы (или белый лист)."""
    if ctx.print_friendly:
        c.setFillColorRGB(1, 1, 1)
        c.rect(0, 0, ctx.page_width, ctx.page_height, fill=1, stroke=0)
        return

    # Вертикальный псевдо-градиент через горизонтальные полосы
    num_strips = 60
    strip_h = ctx.page_height / num_strips
    for i in range(num_strips):
        t = i / num_strips
        r = bg_top[0] + (bg_bottom[0] - bg_top[0]) * t
        g = bg_top[1] + (bg_bottom[1] - bg_top[1]) * t
        b = bg_top[2] + (bg_bottom[2] - bg_top[2]) * t
        c.setFillColorRGB(r, g, b)
        c.rect(0, ctx.page_height - (i + 1) * strip_h, ctx.page_width, strip_h + 0.5, fill=1, stroke=0)

    # Лабиринтный паттерн: полосы сверху и снизу
    band_h = 28 * mm
    cell = 7 * mm
    decorations.render_maze_band(ctx, c, y_bottom=ctx.page_height - band_h, band_h=band_h, cell=cell, accent=accent)
    decorations.render_maze_band(ctx, c, y_bottom=0, band_h=band_h, cell=cell, accent=accent)



def _cover_info_lines(ctx: RenderContext, maze_count: int) -> list[str]:
    """Собирает строки информационного блока обложки."""
    info_lines = [cover_mazes_label(ctx, maze_count)]
    age_label = book_age_label(ctx)
    if age_label:
        info_lines.insert(0, age_label)
    if ctx.config.child_name:
        info_lines.append(ctx.texts.format("cover_for_child", name=ctx.config.child_name))
    if ctx.config.child_age:
        info_lines.append(ctx.texts.format("cover_child_age", age=ctx.config.child_age))
    return info_lines



def _fit_cover_box(ctx: RenderContext,
    c: canvas.Canvas,
    title: str,
    info_lines: list[str],
) -> tuple[int, list[str], float, float, float]:
    """Подбирает размер заголовка и высоту центральной рамки обложки.

    Returns:
        (title_size, title_lines, box_h, content_h, gaps_sum) для компоновки.
    """
    box_w = ctx.page_width - 44 * mm
    title_max_w = box_w - 20 * mm

    base_box_h = 84 * mm
    padding_y = 8 * mm
    subtitle_line_h = 16 * 1.25
    info_line_h = 5.2 * mm
    gap_title_subtitle = 5 * mm
    gap_subtitle_info = 3.8 * mm if info_lines else 0
    info_block_h = len(info_lines) * info_line_h if info_lines else 0

    title_size, title_lines = fit_cover_title_layout(ctx, c, title, title_max_w)
    content_h = (
        len(title_lines) * title_size * 1.2
        + gap_title_subtitle + subtitle_line_h
        + gap_subtitle_info + info_block_h
    )
    box_h = max(base_box_h, content_h + 2 * padding_y)
    max_box_h = ctx.page_height - (62 * mm if not ctx.print_friendly else 46 * mm)

    if box_h > max_box_h:
        available_title_h = max(
            20 * mm,
            max_box_h - 2 * padding_y - gap_title_subtitle - subtitle_line_h - gap_subtitle_info - info_block_h,
        )
        title_size, title_lines = fit_cover_title_layout(
            ctx, c, title, title_max_w,
            max_title_block_height=available_title_h,
        )
        content_h = (
            len(title_lines) * title_size * 1.2
            + gap_title_subtitle + subtitle_line_h
            + gap_subtitle_info + info_block_h
        )
        box_h = min(max_box_h, max(base_box_h, content_h + 2 * padding_y))

    return title_size, title_lines, box_h, content_h



def _draw_cover_text_block(ctx: RenderContext,
    c: canvas.Canvas,
    book: Book,
    title: str,
    cover_accent: tuple[float, float, float],
) -> None:
    """Рисует центральный текстовый блок обложки: плашка, заголовок, подзаголовок, инфо."""
    subtitle = book_subtitle(ctx)
    info_lines = _cover_info_lines(ctx, book_maze_count(ctx, book))
    title_size, title_lines, box_h, content_h = _fit_cover_box(ctx, c, title, info_lines)

    center_y = ctx.page_height / 2
    box_margin = 22 * mm
    box_w = ctx.page_width - 2 * box_margin

    if not ctx.print_friendly:
        c.saveState()
        c.setFillColorRGB(0, 0, 0)
        c.setFillAlpha(0.45)
        c.rect(box_margin, center_y - box_h / 2, box_w, box_h, fill=1, stroke=0)
        c.restoreState()

    # Тонкие линии-акценты над и под плашкой
    c.setStrokeColorRGB(*cover_accent)
    c.setLineWidth(0.9 if ctx.print_friendly else 1.5)
    c.line(box_margin, center_y + box_h / 2, ctx.page_width - box_margin, center_y + box_h / 2)
    c.line(box_margin, center_y - box_h / 2, ctx.page_width - box_margin, center_y - box_h / 2)

    center_x = ctx.page_width / 2
    cursor = center_y + content_h / 2
    cursor = _draw_cover_title(ctx, c, title_lines, title_size, (center_x, cursor), cover_accent=cover_accent)
    cursor = _draw_cover_subtitle(ctx, c, subtitle, center_x, cursor)
    _draw_cover_info(ctx, c, info_lines, center_x, cursor)



def _draw_cover_title(ctx: RenderContext,
    c: canvas.Canvas,
    title_lines: list[str],
    title_size: int,
    pos: tuple[float, float],
    *,
    cover_accent: tuple[float, float, float],
) -> float:
    """Рисует строки заголовка с тенью. Возвращает позицию курсора."""
    center_x, cursor_top = pos
    c.setFont(ctx.font_bold, title_size)
    for line in title_lines:
        baseline_y = cursor_top - title_size
        if not ctx.print_friendly:
            c.saveState()
            c.setFillColorRGB(0, 0, 0)
            c.setFillAlpha(0.5)
            c.drawCentredString(center_x + 1.2, baseline_y - 1.2, line)
            c.restoreState()
        c.setFillColorRGB(*cover_accent)
        c.drawCentredString(center_x, baseline_y, line)
        cursor_top -= title_size * 1.2
    return cursor_top



def _draw_cover_subtitle(ctx: RenderContext,
    c: canvas.Canvas,
    subtitle: str,
    center_x: float,
    cursor: float,
) -> float:
    """Рисует подзаголовок обложки. Возвращает позицию курсора."""
    baseline_y = cursor - 5 * mm - 16
    c.setFont(ctx.font, 16)
    if ctx.print_friendly:
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(center_x, baseline_y, subtitle)
    else:
        c.saveState()
        c.setFillColorRGB(1, 1, 1)
        c.setFillAlpha(0.80)
        c.drawCentredString(center_x, baseline_y, subtitle)
        c.restoreState()
    return baseline_y



def _draw_cover_info(ctx: RenderContext,
    c: canvas.Canvas,
    info_lines: list[str],
    center_x: float,
    cursor: float,
) -> None:
    """Рисует информационные строки обложки под подзаголовком."""
    if not info_lines:
        return
    if ctx.print_friendly:
        c.setFillColorRGB(0, 0, 0)
    else:
        c.setFillColorRGB(1, 1, 1)
    c.setFont(ctx.font, 12)
    gap = 3.8 * mm
    baseline_y = cursor - gap - 12
    for line in info_lines:
        c.drawCentredString(center_x, baseline_y, line)
        baseline_y -= 5.2 * mm
