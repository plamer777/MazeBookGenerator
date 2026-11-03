"""Отрисовка полярного лабиринта: дуги, радиальные сегменты, путь решения."""

import math
from itertools import pairwise

from reportlab.pdfgen import canvas

from maze_book_generator.domain.maze.polar import PolarTopologyService
from maze_book_generator.domain.models import Maze
from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.drawing import markers
from maze_book_generator.infrastructure.pdf.params import MarkerLabelSpec, MazeDrawParams, PolarView


def draw_polar_geometry(ctx: RenderContext,
    c: canvas.Canvas,
    maze: Maze,
    view: PolarView,
    params: MazeDrawParams,
) -> None:
    """Рисует тело полярного лабиринта: стены, маркеры, подписи, путь решения."""
    topology = PolarTopologyService(maze.cells_per_ring)
    end_cell = maze.solution_path[-1] if maze.solution_path else (topology.num_rings - 1, 0)

    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.0)
    _draw_polar_walls(c, topology, _collect_connections(maze, topology), view, end_cell)
    _draw_polar_markers(ctx, c, topology, view, end_cell, show_labels=params.show_labels)

    if params.show_solution and maze.solution_path:
        render_polar_solution_path(c, maze.solution_path, view, topology)


def _collect_connections(maze: Maze, topology: PolarTopologyService) -> dict[tuple[int, int], set[tuple[int, int]]]:
    """Возвращает граф соединений лабиринта, дополненный пустыми ячейками."""
    connections = {cell: set(neighbors) for cell, neighbors in (maze.polar_connections or {}).items()}
    for cell in topology.iter_cells():
        connections.setdefault(cell, set())
    return connections


def _draw_polar_walls(c: canvas.Canvas,
    topology: PolarTopologyService,
    connections: dict[tuple[int, int], set[tuple[int, int]]],
    view: PolarView,
    end_cell: tuple[int, int],
) -> None:
    """Рисует дуговые и радиальные стены всех ячеек полярного лабиринта."""
    for ring in range(topology.num_rings):
        count = topology.cells_per_ring[ring]
        for sector in range(count):
            cell = (ring, sector)
            linked = connections[cell]
            _draw_cell_arcs(c, topology, view, cell, linked, end_cell=end_cell)
            _draw_radial_wall(c, topology, view, cell, linked)


def _draw_cell_arcs(c: canvas.Canvas,
    topology: PolarTopologyService,
    view: PolarView,
    cell: tuple[int, int],
    linked: set[tuple[int, int]],
    *,
    end_cell: tuple[int, int],
) -> None:
    """Рисует внутренние и наружные дуговые стены одной ячейки."""
    ring, sector = cell
    inner_info = topology.inner_neighbor_interval(ring, sector)
    if inner_info:
        neighbor, angle_start, angle_end = inner_info
        if neighbor not in linked and angle_end > angle_start:
            radius = view.max_radius * ring / topology.num_rings
            draw_arc(c, (view.center_x, view.center_y), radius, angle_start, angle_end)

    if ring < topology.num_rings - 1:
        for neighbor, angle_start, angle_end in topology.outer_neighbor_intervals(ring, sector):
            if neighbor not in linked and angle_end > angle_start:
                radius = view.max_radius * (ring + 1) / topology.num_rings
                draw_arc(c, (view.center_x, view.center_y), radius, angle_start, angle_end)
        return

    sector_start, sector_end = topology.get_sector_bounds(ring, sector)
    if cell == end_cell:
        # Выход из лабиринта — разрыв во внешней дуге
        gap = min((sector_end - sector_start) * 0.3, sector_end - sector_start)
        left_end = sector_start + (sector_end - sector_start - gap) / 2
        right_start = left_end + gap
        draw_arc(c, (view.center_x, view.center_y), view.max_radius, sector_start, left_end)
        draw_arc(c, (view.center_x, view.center_y), view.max_radius, right_start, sector_end)
    else:
        draw_arc(c, (view.center_x, view.center_y), view.max_radius, sector_start, sector_end)


def _draw_radial_wall(c: canvas.Canvas,
    topology: PolarTopologyService,
    view: PolarView,
    cell: tuple[int, int],
    linked: set[tuple[int, int]],
) -> None:
    """Рисует радиальную стену ячейки по часовой стрелке."""
    ring, sector = cell
    if ring == 0:
        return
    cw_neighbor = topology.get_clockwise_neighbor(ring, sector)
    if cw_neighbor in linked:
        return
    _, sector_end = topology.get_sector_bounds(ring, sector)
    inner_radius = view.max_radius * ring / topology.num_rings
    outer_radius = view.max_radius * (ring + 1) / topology.num_rings
    draw_radial_segment(c, (view.center_x, view.center_y), sector_end, inner_radius, outer_radius)


def _draw_polar_markers(ctx: RenderContext,
    c: canvas.Canvas,
    topology: PolarTopologyService,
    view: PolarView,
    end_cell: tuple[int, int],
    *,
    show_labels: bool,
) -> None:
    """Рисует маркеры старта и финиша полярного лабиринта."""
    marker_r = view.max_radius / topology.num_rings * 0.45
    markers.draw_triangle_marker(c, view.center_x, view.center_y, marker_r, angle=math.pi / 2, color=(0, 0.75, 0))

    end_angle = topology.get_sector_center_angle(*end_cell)
    arrow_tip_x = view.center_x + (view.max_radius + marker_r * 0.3) * math.cos(end_angle)
    arrow_tip_y = view.center_y + (view.max_radius + marker_r * 0.3) * math.sin(end_angle)
    markers.draw_triangle_marker(c, arrow_tip_x, arrow_tip_y, marker_r, angle=end_angle + math.pi, color=(0.9, 0, 0))

    if show_labels:
        start_text = ctx.texts.get("start_label")
        finish_text = ctx.texts.get("finish_label")
        start_pos, finish_pos = markers.compute_marker_label_positions(ctx, c,
            spec=MarkerLabelSpec(
                start_marker=(view.center_x, view.center_y),
                finish_marker=(arrow_tip_x, arrow_tip_y),
                start_text=start_text,
                finish_text=finish_text,
                marker_radius=marker_r,
            ),
        )
        markers.draw_marker_label(ctx, c, start_pos[0], start_pos[1], start_text)
        markers.draw_marker_label(ctx, c, finish_pos[0], finish_pos[1], finish_text)


def render_polar_solution_path(c: canvas.Canvas,
    solution_path: list[tuple[int, int]],
    view: PolarView,
    topology: PolarTopologyService,
) -> None:
    """Рисует непрерывный путь решения полярного лабиринта по коридорам."""
    if not solution_path or len(solution_path) < 2:
        return

    c.setStrokeColorRGB(1, 0, 0)
    c.setLineWidth(2.5)

    cursor = _SolutionCursor(view, topology, solution_path[0])
    for current, nxt in pairwise(solution_path):
        if current[0] == nxt[0]:
            _step_along_ring(c, cursor, nxt)
        else:
            _step_across_rings(c, cursor, current, nxt)

    # Финальный отрезок к внешней границе
    end_x, end_y = cursor.to_xy(view.max_radius, cursor.angle)
    c.line(cursor.x, cursor.y, end_x, end_y)


class _SolutionCursor:
    """Курсор отрисовки пути решения: текущая точка, радиус и угол."""

    def __init__(self, view: PolarView, topology: PolarTopologyService,
                 first_cell: tuple[int, int]) -> None:
        self._view = view
        self._topology = topology
        ring0, sec0 = first_cell
        self.angle = topology.get_sector_center_angle(ring0, sec0)
        self.radius = self.ring_radius(ring0) if ring0 > 0 else 0.0
        self.x, self.y = self.to_xy(self.radius, self.angle)

    def ring_radius(self, ring: int) -> float:
        """Радиус середины кольца."""
        return self._view.max_radius * (ring + 0.5) / self._topology.num_rings

    def to_xy(self, radius: float, angle: float) -> tuple[float, float]:
        """Полярные координаты в экранные."""
        return (self._view.center_x + radius * math.cos(angle),
                self._view.center_y + radius * math.sin(angle))

    def sector_angle(self, cell: tuple[int, int]) -> float:
        """Центральный угол сектора ячейки."""
        return self._topology.get_sector_center_angle(*cell)

    def overlap_angle(self, inner: tuple[int, int], outer: tuple[int, int]) -> float:
        """Центральный угол перекрытия двух секторов на разных кольцах."""
        i_start, i_end = self._topology.get_sector_bounds(*inner)
        o_start, o_end = self._topology.get_sector_bounds(*outer)
        if min(i_end, o_end) > max(i_start, o_start):
            return (max(i_start, o_start) + min(i_end, o_end)) / 2
        return (i_start + i_end) / 2

    def shortest_arc_end(self, target_raw: float) -> float:
        """Угол target с поправкой на кратчайшую дугу от текущего угла."""
        diff = (target_raw - self.angle) % (2 * math.pi)
        if diff > math.pi:
            return self.angle - (2 * math.pi - diff)
        return self.angle + diff

    def line_to(self, c: canvas.Canvas, radius: float, angle: float) -> None:
        """Отрезок от текущей точки к (radius, angle) с переносом курсора."""
        x, y = self.to_xy(radius, angle)
        c.line(self.x, self.y, x, y)
        self.x, self.y = x, y

    def arc_to(self, c: canvas.Canvas, radius: float, arc_end: float, segments: int) -> None:
        """Дуга от текущего угла до arc_end на заданном радиусе."""
        draw_arc_from(c, (self._view.center_x, self._view.center_y),
                      radius, self.angle, arc_end, segments=segments)
        self.angle = arc_end
        self.radius = radius
        self.x, self.y = self.to_xy(radius, arc_end)


def _step_along_ring(c: canvas.Canvas, cursor: _SolutionCursor, nxt: tuple[int, int]) -> None:
    """Угловой переход пути внутри одного кольца — дуга по середине кольца."""
    ring, _sector = nxt
    radius = cursor.ring_radius(ring)

    # Если текущая точка на другом радиусе — сначала радиальный отрезок до дуги
    if abs(cursor.radius - radius) > 0.5:
        cursor.line_to(c, radius, cursor.angle)

    arc_end = cursor.shortest_arc_end(cursor.sector_angle(nxt))
    cursor.arc_to(c, radius, arc_end, segments=24)


def _step_across_rings(c: canvas.Canvas,
    cursor: _SolutionCursor,
    current: tuple[int, int],
    nxt: tuple[int, int],
) -> None:
    """Радиальный переход пути между кольцами через угол перекрытия секторов."""
    inner, outer = (current, nxt) if current[0] < nxt[0] else (nxt, current)
    trans_angle = cursor.overlap_angle(inner, outer)
    inner_radius = cursor.ring_radius(inner[0])
    outer_radius = cursor.ring_radius(outer[0])

    # Выровнять радиус до inner, затем довести дугой до угла перехода
    if abs(cursor.radius - inner_radius) > 0.5:
        cursor.line_to(c, inner_radius, cursor.angle)
    if abs(cursor.angle % (2 * math.pi) - trans_angle) > 1e-6:
        cursor.arc_to(c, inner_radius, cursor.shortest_arc_end(trans_angle), segments=12)

    # Радиальный отрезок до середины следующего кольца
    cursor.line_to(c, outer_radius, trans_angle)
    cursor.angle = trans_angle


def angle_in_range(angle: float, start: float, end: float) -> bool:
    """Проверяет, лежит ли угол строго внутри диапазона [start, end].

    Учитывает wrap-around через 2π.

    Args:
        angle: Проверяемый угол (радианы)
        start: Начало диапазона
        end: Конец диапазона

    Returns:
        True если angle ∈ (start, end)
    """
    two_pi = 2 * math.pi
    a = angle % two_pi
    s = start % two_pi
    e = end % two_pi
    if s < e:
        return s < a < e
    return a > s or a < e


def draw_arc(c: canvas.Canvas,
    center: tuple[float, float],
    radius: float,
    angle_start: float,
    angle_end: float,
    *,
    segments: int = 16,
) -> None:
    """Рисует дугу от angle_start до angle_end (направление задаётся знаком разности)."""
    if radius <= 0:
        return
    center_x, center_y = center
    step = (angle_end - angle_start) / max(segments, 1)
    prev_x = center_x + radius * math.cos(angle_start)
    prev_y = center_y + radius * math.sin(angle_start)
    for i in range(1, segments + 1):
        angle = angle_start + step * i
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        c.line(prev_x, prev_y, x, y)
        prev_x, prev_y = x, y


def draw_arc_from(c: canvas.Canvas,
    center: tuple[float, float],
    radius: float,
    angle_start: float,
    angle_end: float,
    *,
    segments: int = 16,
) -> None:
    """Рисует дугу от angle_start до angle_end без автоисправления направления."""
    if radius <= 0 or abs(angle_end - angle_start) < 1e-9:
        return
    center_x, center_y = center
    step = (angle_end - angle_start) / max(segments, 1)
    prev_x = center_x + radius * math.cos(angle_start)
    prev_y = center_y + radius * math.sin(angle_start)
    for i in range(1, segments + 1):
        angle = angle_start + step * i
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        c.line(prev_x, prev_y, x, y)
        prev_x, prev_y = x, y


def draw_radial_segment(c: canvas.Canvas,
    center: tuple[float, float],
    angle: float,
    inner_radius: float,
    outer_radius: float,
) -> None:
    """Рисует радиальный отрезок стены от inner до outer радиуса."""
    center_x, center_y = center
    start_x = center_x + inner_radius * math.cos(angle)
    start_y = center_y + inner_radius * math.sin(angle)
    end_x = center_x + outer_radius * math.cos(angle)
    end_y = center_y + outer_radius * math.sin(angle)
    c.line(start_x, start_y, end_x, end_y)

