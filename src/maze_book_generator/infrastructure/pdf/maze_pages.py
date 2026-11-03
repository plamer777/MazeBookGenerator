"""Страницы лабиринтов и ответов: заголовки, рамки, размещение лабиринта."""

import dataclasses

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from maze_book_generator.domain.models import BookPage, Maze, MazeShape
from maze_book_generator.infrastructure.pdf import cover, decorations, images
from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.drawing import grid, polar
from maze_book_generator.infrastructure.pdf.params import MazeDrawParams, PolarView, Rect
from maze_book_generator.settings import (
    MAZE_PAGE_DECO_MARGIN,
    MAZE_PAGE_DIFFICULTY_FONT,
    MAZE_PAGE_FRAME_M,
    MAZE_PAGE_HEADER_FONT,
    MAZE_PAGE_HEADER_H,
    MAZE_PAGE_MAZE_TOP_GAP,
    MAZE_PAGE_NUM_FONT,
    MAZE_PAGE_PROMPT_FONT,
    MAZE_PAGE_PROMPT_GAP,
)


def render_maze_page(ctx: RenderContext, c: canvas.Canvas, page: BookPage, book_title: str = "") -> None:
    """
    Рендерит страницу с лабиринтом в детском стиле.

    Структура: цветной фон, заокруглённая рамка, декор углов,
    плашка-заголовок, подсказка и лабиринт максимального размера.
    """
    accent = cover.cover_palette(book_title or page.title)[2]
    header_y = _draw_page_scaffold(ctx, c, accent, page.page_number)

    maze_title = ctx.texts.get("maze_title").replace("{n}", str(page.page_number))
    _draw_header_title(ctx, c, maze_title, header_y)

    prompt_y = _draw_prompt_hint(ctx, c, accent, page, header_y)
    maze_area = _maze_area(ctx, prompt_y - MAZE_PAGE_MAZE_TOP_GAP * mm)
    _render_page_maze(ctx, c, page, accent, maze_area, show_solution=False)


def render_solution_page(ctx: RenderContext, c: canvas.Canvas, page: BookPage, book_title: str = "") -> None:
    """Рендерит страницу с ответом в том же детском стиле."""
    accent = cover.cover_palette(book_title or page.title)[2]
    header_y = _draw_page_scaffold(ctx, c, accent, page.page_number)

    maze_title = ctx.texts.get("maze_title").replace("{n}", str(page.page_number))
    sol_title = f"{maze_title} — {ctx.texts.get('answer_page_suffix')}"
    _draw_header_title(ctx, c, sol_title, header_y)

    maze_area = _maze_area(ctx, header_y - 5 * mm)
    _render_page_maze(ctx, c, page, accent, maze_area, show_solution=True)


def _draw_page_scaffold(
    ctx: RenderContext,
    c: canvas.Canvas,
    accent: tuple[float, float, float],
    page_number: int,
) -> float:
    """Фон + рамка + уголки + плашка заголовка; возвращает header_y."""
    bg = (1.0, 1.0, 1.0) if ctx.print_friendly else (0.97, 0.97, 1.0)
    c.setFillColorRGB(*bg)
    c.rect(0, 0, ctx.page_width, ctx.page_height, fill=1, stroke=0)

    c.setStrokeColorRGB(*accent)
    c.setLineWidth(2.5)
    c.roundRect(MAZE_PAGE_FRAME_M * mm, MAZE_PAGE_FRAME_M * mm,
                ctx.page_width - 2 * MAZE_PAGE_FRAME_M * mm,
                ctx.page_height - 2 * MAZE_PAGE_FRAME_M * mm,
                radius=6 * mm, fill=0, stroke=1)

    if not ctx.print_friendly:
        decorations.render_page_corner_deco(ctx, c, accent, page_number)

    header_y = ctx.page_height - MAZE_PAGE_FRAME_M * mm - MAZE_PAGE_HEADER_H * mm
    c.setFillColorRGB(*accent)
    c.roundRect(MAZE_PAGE_FRAME_M * mm, header_y,
                ctx.page_width - 2 * MAZE_PAGE_FRAME_M * mm, MAZE_PAGE_HEADER_H * mm,
                radius=4 * mm, fill=1, stroke=0)
    return header_y


def _draw_header_title(
    ctx: RenderContext, c: canvas.Canvas, title: str, header_y: float
) -> None:
    """Белый заголовок по центру цветной плашки."""
    c.setFillColorRGB(1, 1, 1)
    c.setFont(ctx.font_bold, MAZE_PAGE_HEADER_FONT)
    tw = c.stringWidth(title, ctx.font_bold, MAZE_PAGE_HEADER_FONT)
    c.drawString((ctx.page_width - tw) / 2, header_y + 7 * mm, title)


def _draw_prompt_hint(
    ctx: RenderContext,
    c: canvas.Canvas,
    accent: tuple[float, float, float],
    page: BookPage,
    header_y: float,
) -> float:
    """Подсказка задания и подпись сложности под плашкой; возвращает prompt_y."""
    prompt_y = header_y - MAZE_PAGE_PROMPT_GAP * mm
    if ctx.print_friendly:
        c.setFillColorRGB(0.12, 0.12, 0.12)
    else:
        c.setFillColorRGB(*accent)
    c.setFont(ctx.font, MAZE_PAGE_PROMPT_FONT)
    pw = c.stringWidth(page.prompt, ctx.font, MAZE_PAGE_PROMPT_FONT)
    c.drawString((ctx.page_width - pw) / 2, prompt_y, page.prompt)

    if page.difficulty_label:
        difficulty_caption = ctx.texts.format("difficulty_caption", value=page.difficulty_label)
        c.setFont(ctx.font_bold, MAZE_PAGE_DIFFICULTY_FONT)
        dw = c.stringWidth(difficulty_caption, ctx.font_bold, MAZE_PAGE_DIFFICULTY_FONT)
        c.drawString((ctx.page_width - dw) / 2, prompt_y - 5 * mm, difficulty_caption)
    return prompt_y


def _maze_area(ctx: RenderContext, maze_top: float) -> Rect:
    """Прямоугольник области лабиринта внутри декоративного поля."""
    return Rect(
        MAZE_PAGE_FRAME_M * mm + MAZE_PAGE_DECO_MARGIN * mm,
        MAZE_PAGE_FRAME_M * mm + MAZE_PAGE_DECO_MARGIN * mm,
        ctx.page_width - 2 * (MAZE_PAGE_FRAME_M * mm + MAZE_PAGE_DECO_MARGIN * mm),
        maze_top - MAZE_PAGE_FRAME_M * mm - MAZE_PAGE_DECO_MARGIN * mm,
    )


def _render_page_maze(
    ctx: RenderContext,
    c: canvas.Canvas,
    page: BookPage,
    accent: tuple[float, float, float],
    maze_area: Rect,
    *,
    show_solution: bool,
) -> None:
    """Водяной знак + лабиринт по области + номер страницы."""
    if page.image_path and not ctx.print_friendly:
        images.render_watermark_image(c, page.image_path, maze_area)

    render_maze_fitted(
        ctx, c, page.maze, maze_area,
        MazeDrawParams(
            show_solution=show_solution,
            show_labels=ctx.config.show_start_finish_labels,
        ),
    )

    c.setFillColorRGB(*accent)
    c.setFont(ctx.font, MAZE_PAGE_NUM_FONT)
    c.drawRightString(
        ctx.page_width - MAZE_PAGE_FRAME_M * mm - 4 * mm,
        MAZE_PAGE_FRAME_M * mm + 3 * mm,
        f"#{page.page_number}",
    )



def render_maze_fitted(
    ctx: RenderContext,
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



def _render_polar_fitted(
    ctx: RenderContext,
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



def _render_grid_fitted(
    ctx: RenderContext,
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

