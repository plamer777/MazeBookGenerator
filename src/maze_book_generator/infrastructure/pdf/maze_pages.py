"""Страницы лабиринтов и ответов: заголовки, рамки, размещение лабиринта."""

import dataclasses

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from maze_book_generator.domain.models import BookPage, Maze, MazeShape
from maze_book_generator.infrastructure.pdf import cover, decorations, images
from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.drawing import grid, polar
from maze_book_generator.infrastructure.pdf.params import MazeDrawParams, PolarView, Rect


def render_maze_page(ctx: RenderContext, c: canvas.Canvas, page: BookPage, book_title: str = "") -> None:
    """
    Рендерит страницу с лабиринтом в детском стиле.

    Структура:
    - Светлый цветной фон
    - Заокруглённая рамка в цвете палитры
    - Декоративные символы в углах
    - Цветная плашка-заголовок сверху
    - Лабиринт максимального размера с динамическим cell_size

    Args:
        c: Canvas для рисования
        page: Объект страницы
    """
    _, _, accent = cover.cover_palette(book_title or page.title)

    # --- Фон ---
    bg = (1.0, 1.0, 1.0) if ctx.print_friendly else (0.97, 0.97, 1.0)
    c.setFillColorRGB(*bg)
    c.rect(0, 0, ctx.page_width, ctx.page_height, fill=1, stroke=0)

    # --- Заокруглённая рамка ---
    frame_m = 8 * mm
    c.setStrokeColorRGB(*accent)
    c.setLineWidth(2.5)
    c.roundRect(frame_m, frame_m,
                ctx.page_width - 2 * frame_m,
                ctx.page_height - 2 * frame_m,
                radius=6 * mm, fill=0, stroke=1)

    # --- Декоративные символы в углах ---
    if not ctx.print_friendly:
        decorations.render_page_corner_deco(ctx, c, accent, page.page_number)

    # --- Плашка заголовка ---
    header_h = 22 * mm
    header_y = ctx.page_height - frame_m - header_h
    c.setFillColorRGB(*accent)
    c.roundRect(frame_m, header_y,
                ctx.page_width - 2 * frame_m, header_h,
                radius=4 * mm, fill=1, stroke=0)

    c.setFillColorRGB(1, 1, 1)
    c.setFont(ctx.font_bold, 18)
    maze_title = ctx.texts.get("maze_title").replace("{n}", str(page.page_number))
    tw = c.stringWidth(maze_title, ctx.font_bold, 18)
    c.drawString((ctx.page_width - tw) / 2, header_y + 7 * mm, maze_title)

    # Подсказка под плашкой
    prompt_y = header_y - 8 * mm
    if ctx.print_friendly:
        c.setFillColorRGB(0.12, 0.12, 0.12)
    else:
        c.setFillColorRGB(*accent)
    c.setFont(ctx.font, 11)
    pw = c.stringWidth(page.prompt, ctx.font, 11)
    c.drawString((ctx.page_width - pw) / 2, prompt_y, page.prompt)

    if page.difficulty_label:
        difficulty_caption = ctx.texts.format("difficulty_caption", value=page.difficulty_label)
        c.setFont(ctx.font_bold, 10)
        dw = c.stringWidth(difficulty_caption, ctx.font_bold, 10)
        c.drawString((ctx.page_width - dw) / 2, prompt_y - 5 * mm, difficulty_caption)

    # --- Лабиринт максимального размера ---
    # Верхняя граница строго под подсказкой (с зазором 5mm)
    deco_margin = 20 * mm
    maze_top = prompt_y - 11 * mm
    # --- Водяной знак-иллюстрация под лабиринтом ---
    maze_area = Rect(
        frame_m + deco_margin,
        frame_m + deco_margin,
        ctx.page_width - 2 * (frame_m + deco_margin),
        maze_top - frame_m - deco_margin,
    )
    if page.image_path and not ctx.print_friendly:
        images.render_watermark_image(c, page.image_path, maze_area)

    render_maze_fitted(ctx, c, page.maze, maze_area,
        MazeDrawParams(show_labels=ctx.config.show_start_finish_labels))

    # --- Номер страницы ---
    c.setFillColorRGB(*accent)
    c.setFont(ctx.font, 9)
    c.drawRightString(ctx.page_width - frame_m - 4 * mm, frame_m + 3 * mm, f"#{page.page_number}")



def render_solution_page(ctx: RenderContext, c: canvas.Canvas, page: BookPage, book_title: str = "") -> None:
    """
    Рендерит страницу с ответом в том же детском стиле.

    Args:
        c: Canvas для рисования
        page: Объект страницы
    """
    _, _, accent = cover.cover_palette(book_title or page.title)

    bg = (1.0, 1.0, 1.0) if ctx.print_friendly else (0.97, 0.97, 1.0)
    c.setFillColorRGB(*bg)
    c.rect(0, 0, ctx.page_width, ctx.page_height, fill=1, stroke=0)

    frame_m = 8 * mm
    c.setStrokeColorRGB(*accent)
    c.setLineWidth(2.5)
    c.roundRect(frame_m, frame_m,
                ctx.page_width - 2 * frame_m,
                ctx.page_height - 2 * frame_m,
                radius=6 * mm, fill=0, stroke=1)

    if not ctx.print_friendly:
        decorations.render_page_corner_deco(ctx, c, accent, page.page_number)

    header_h = 22 * mm
    header_y = ctx.page_height - frame_m - header_h
    c.setFillColorRGB(*accent)
    c.roundRect(frame_m, header_y,
                ctx.page_width - 2 * frame_m, header_h,
                radius=4 * mm, fill=1, stroke=0)

    sol_title = f"{ctx.texts.get('maze_title').replace('{n}', str(page.page_number))} — {ctx.texts.get('answer_page_suffix')}"
    c.setFillColorRGB(1, 1, 1)
    c.setFont(ctx.font_bold, 18)
    tw = c.stringWidth(sol_title, ctx.font_bold, 18)
    c.drawString((ctx.page_width - tw) / 2, header_y + 7 * mm, sol_title)

    deco_margin = 20 * mm
    maze_top = header_y - 5 * mm
    maze_area = Rect(
        frame_m + deco_margin,
        frame_m + deco_margin,
        ctx.page_width - 2 * (frame_m + deco_margin),
        maze_top - frame_m - deco_margin,
    )

    if page.image_path and not ctx.print_friendly:
        images.render_watermark_image(c, page.image_path, maze_area)

    render_maze_fitted(ctx, c, page.maze, maze_area,
        MazeDrawParams(show_solution=True, show_labels=ctx.config.show_start_finish_labels))

    c.setFillColorRGB(*accent)
    c.setFont(ctx.font, 9)
    c.drawRightString(ctx.page_width - frame_m - 4 * mm, frame_m + 3 * mm, f"#{page.page_number}")



def render_maze_fitted(ctx: RenderContext,
    c: canvas.Canvas,
    maze: Maze,
    area: Rect,
    params: MazeDrawParams,
) -> None:
    """
    Рендерит лабиринт, масштабируя cell_size так, чтобы он занял всю область.

    Вычисляет максимальный cell_size при котором лабиринт помещается в область,
    затем центрирует его внутри неё.

    Args:
        ctx: Контекст рендеринга
        c: Canvas для рисования
        maze: Объект лабиринта
        area: Доступная область страницы
        params: Флаги отрисовки (решение, подписи)
    """
    if maze.shape == MazeShape.CIRCULAR:
        _render_polar_fitted(ctx, c, maze, area, params)
    else:
        _render_grid_fitted(ctx, c, maze, area, params)



def _render_polar_fitted(ctx: RenderContext,
    c: canvas.Canvas,
    maze: Maze,
    area: Rect,
    params: MazeDrawParams,
) -> None:
    """Вписывает полярный лабиринт в область: диаметр = min(w, h)."""
    diameter = min(area.width, area.height)
    view = PolarView(
        center_x=area.x + area.width / 2,
        center_y=area.y + area.height / 2,
        max_radius=diameter / 2 - 2,
    )
    fitted_ctx = dataclasses.replace(ctx, cell_size=diameter / max(maze.width, maze.height))
    polar.draw_polar_geometry(fitted_ctx, c, maze, view, params)



def _render_grid_fitted(ctx: RenderContext,
    c: canvas.Canvas,
    maze: Maze,
    area: Rect,
    params: MazeDrawParams,
) -> None:
    """Вписывает сеточный лабиринт в область с сохранением пропорций."""
    fit_cell = min(area.width / maze.width, area.height / maze.height)
    maze_w_px = maze.width * fit_cell
    maze_h_px = maze.height * fit_cell
    start_x = area.x + (area.width - maze_w_px) / 2
    start_y = area.y + (area.height - maze_h_px) / 2
    fitted_ctx = dataclasses.replace(ctx, cell_size=fit_cell)
    render_maze_at(fitted_ctx, c, maze, start_x, start_y, params=params)



def render_maze_at(ctx: RenderContext,
    c: canvas.Canvas,
    maze: Maze,
    start_x: float,
    start_y: float,
    *,
    params: MazeDrawParams,
) -> None:
    """
    Рендерит сеточный лабиринт с явными координатами левого нижнего угла.

    Использует ctx.cell_size (должен быть установлен перед вызовом).

    Args:
        ctx: Контекст рендеринга
        c: Canvas
        maze: Объект лабиринта
        start_x: X левого нижнего угла
        start_y: Y левого нижнего угла
        params: Флаги отрисовки (решение, подписи)
    """
    grid.draw_grid_body(c, maze, ctx.cell_size, start_x, start_y, mask=_shape_mask(maze))
    grid.render_start_end(ctx, c, maze, start_x, start_y, show_labels=params.show_labels)

    if params.show_solution and maze.solution_path:
        grid.render_solution_path(ctx, c, maze, maze.solution_path, (start_x, start_y))



def _shape_mask(maze: Maze) -> list[list[bool]] | None:
    """Возвращает маску формы для фигурных лабиринтов, иначе None."""
    if maze.shape not in (
        MazeShape.TRIANGULAR,
        MazeShape.RANDOM,
        MazeShape.CHAOTIC,
        MazeShape.DIAMOND,
        MazeShape.HEART,
    ):
        return None
    return [[bool(maze.grid[y][x]) for x in range(maze.width)] for y in range(maze.height)]

