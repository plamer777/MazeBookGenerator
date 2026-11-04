"""Отрисовка grid-лабиринтов: прямоугольные и фигурные формы, путь решения."""

import math

from reportlab.pdfgen import canvas

from maze_book_generator.domain.models import Maze
from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.drawing import markers
from maze_book_generator.infrastructure.pdf.params import MarkerLabelSpec


def draw_grid_body(c: canvas.Canvas,
    maze: Maze,
    cell_size: float,
    start_x: float,
    start_y: float,
    *,
    mask: list[list[bool]] | None = None,
) -> None:
    """Рисует тело сеточного лабиринта: стены или контуры ячеек по маске."""
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.0)

    if maze.walls:
        _draw_wall_segments(c, maze, cell_size, start_x, start_y, mask=mask)
    else:
        _draw_cell_outlines(c, maze, cell_size, start_x, start_y, mask=mask)


def _draw_wall_segments(c: canvas.Canvas,
    maze: Maze,
    cell_size: float,
    start_x: float,
    start_y: float,
    *,
    mask: list[list[bool]] | None,
) -> None:
    """Рисует стены ячеек линиями по данным maze.walls [верх, право, низ, лево]."""
    for y in range(maze.height):
        for x in range(maze.width):
            if mask and not mask[y][x]:
                continue
            cell_x = start_x + x * cell_size
            cell_y = start_y + (maze.height - 1 - y) * cell_size
            walls = maze.walls[y][x]
            if walls[0]:
                c.line(cell_x, cell_y + cell_size, cell_x + cell_size, cell_y + cell_size)
            if walls[1]:
                c.line(cell_x + cell_size, cell_y, cell_x + cell_size, cell_y + cell_size)
            if walls[2]:
                c.line(cell_x, cell_y, cell_x + cell_size, cell_y)
            if walls[3]:
                c.line(cell_x, cell_y, cell_x, cell_y + cell_size)


def _draw_cell_outlines(c: canvas.Canvas,
    maze: Maze,
    cell_size: float,
    start_x: float,
    start_y: float,
    *,
    mask: list[list[bool]] | None,
) -> None:
    """Fallback-отрисовка: контуры ячеек по значению grid, если walls не заданы."""
    for y in range(maze.height):
        for x in range(maze.width):
            if mask and not mask[y][x]:
                continue
            if maze.grid[y][x] == 0:
                c.rect(
                    start_x + x * cell_size,
                    start_y + (maze.height - 1 - y) * cell_size,
                    cell_size,
                    cell_size,
                    fill=0,
                    stroke=1,
                )


def render_solution_path(ctx: RenderContext, c: canvas.Canvas, maze: Maze,
                         solution_path: list[tuple[int, int]], start: tuple[float, float]) -> None:
    """Рисует путь решения лабиринта красной линией."""
    if not solution_path or len(solution_path) < 2:
        return
    start_x, start_y = start

    c.setStrokeColorRGB(1, 0, 0)  # Красный цвет для пути
    c.setLineWidth(2.0)

    for i in range(len(solution_path) - 1):
        x1, y1 = solution_path[i]
        x2, y2 = solution_path[i + 1]

        # Конвертируем координаты ячеек в координаты на странице
        screen_x1 = start_x + x1 * ctx.cell_size + ctx.cell_size / 2
        screen_y1 = start_y + (maze.height - 1 - y1) * ctx.cell_size + ctx.cell_size / 2
        screen_x2 = start_x + x2 * ctx.cell_size + ctx.cell_size / 2
        screen_y2 = start_y + (maze.height - 1 - y2) * ctx.cell_size + ctx.cell_size / 2

        c.line(screen_x1, screen_y1, screen_x2, screen_y2)


def render_start_end(ctx: RenderContext,
    c: canvas.Canvas,
    maze: Maze,
    start_x: float,
    start_y: float,
    *,
    show_labels: bool = False,
) -> None:
    """
    Рисует маркеры старта и конца лабиринта в виде треугольников.

    Треугольник указывает в направлении входа/выхода из лабиринта.
    Направление определяется по положению ячейки на границе сетки.

    Args:
        c: Canvas для рисования
        ctx: Контекст рендеринга (палитра, размеры страницы, print_friendly)
        maze: Объект лабиринта
        start_x: Начальная координата X лабиринта на странице
        start_y: Начальная координата Y лабиринта на странице
        show_labels: Показывать ли текстовые подписи СТАРТ/ФИНИШ
    """
    marker_r = ctx.cell_size * 0.45

    def cell_center(gx: int, gy: int) -> tuple[float, float]:
        cx = start_x + gx * ctx.cell_size + ctx.cell_size / 2
        cy = start_y + (maze.height - 1 - gy) * ctx.cell_size + ctx.cell_size / 2
        return cx, cy

    def border_angle(gx: int, gy: int) -> float:
        """Угол, указывающий внутрь лабиринта из граничной ячейки."""
        if gy == 0:
            return math.pi / 2        # снизу → вверх
        if gy == maze.height - 1:
            return -math.pi / 2       # сверху → вниз
        if gx == 0:
            return 0.0                # слева → вправо
        return math.pi                # справа → влево

    sx, sy = maze.start
    ex, ey = maze.end

    scx, scy = cell_center(sx, sy)
    angle_s = border_angle(sx, sy)
    markers.draw_triangle_marker(c, scx, scy, marker_r, angle=angle_s, color=(0, 0.75, 0))

    ecx, ecy = cell_center(ex, ey)
    angle_e = border_angle(ex, ey)
    markers.draw_triangle_marker(c, ecx, ecy, marker_r, angle=angle_e + math.pi, color=(0.9, 0, 0))

    if show_labels:
        start_text = ctx.texts.get("start_label")
        finish_text = ctx.texts.get("finish_label")
        start_pos, finish_pos = markers.compute_marker_label_positions(ctx, c,
            spec=MarkerLabelSpec(
                start_marker=(scx, scy),
                finish_marker=(ecx, ecy),
                start_text=start_text,
                finish_text=finish_text,
                marker_radius=marker_r,
            ),
        )
        markers.draw_marker_label(ctx, c, start_pos[0], start_pos[1], start_text)
        markers.draw_marker_label(ctx, c, finish_pos[0], finish_pos[1], finish_text)

