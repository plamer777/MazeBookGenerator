"""Полярная топология лабиринта и конвейер генерации круглых лабиринтов.

В отличие от grid-форм, полярный лабиринт — это граф ячеек (кольцо, сектор)
с динамическим разбиением колец 1:1 или 1:2, поэтому весь его конвейер
живёт отдельно от прямоугольной сетки стен.
"""

from __future__ import annotations

import math
import random
from collections import deque
from collections.abc import Iterator, Sequence

from maze_book_generator.domain.maze.difficulty import effective_level, lerp
from maze_book_generator.domain.maze.types import Cell, Connections
from maze_book_generator.domain.models import Difficulty, Maze, MazeShape


class PolarTopologyService:
    """Отвечает за топологию полярного лабиринта с динамическим разбиением (subdivision)."""

    def __init__(self, cells_per_ring: Sequence[int]) -> None:
        """Инициализация сервиса топологии по количеству ячеек в каждом кольце."""
        if not cells_per_ring:
            msg = "Список колец не может быть пустым"
            raise ValueError(msg)
        if cells_per_ring[0] != 1:
            msg = "Центральное кольцо должно содержать одну ячейку"
            raise ValueError(msg)

        # Строгая валидация симметрии: следующее кольцо равно предыдущему или ровно в 2 раза больше
        for i in range(2, len(cells_per_ring)):
            prev = cells_per_ring[i-1]
            curr = cells_per_ring[i]
            if curr != prev and curr != prev * 2:
                msg = f"Ошибка разбиения сетки: {prev} -> {curr}. Разрешено только 1:1 или 1:2."
                raise ValueError(msg)

        self.cells_per_ring: list[int] = list(cells_per_ring)
        self.num_rings: int = len(self.cells_per_ring)
        self._sector_bounds: list[list[tuple[float, float]]] = [
            [self._compute_bounds(ring, sector) for sector in range(count)]
            for ring, count in enumerate(self.cells_per_ring)
        ]

    def iter_cells(self) -> Iterator[Cell]:
        """Итерирует все ячейки топологии как (кольцо, сектор)."""
        for ring, count in enumerate(self.cells_per_ring):
            for sector in range(count):
                yield (ring, sector)

    def total_cells(self) -> int:
        """Возвращает общее число ячеек во всех кольцах."""
        return sum(self.cells_per_ring)

    def get_sector_bounds(self, ring: int, sector: int) -> tuple[float, float]:
        """Возвращает угловые границы сектора (start, end) в радианах."""
        self._validate_cell(ring, sector)
        return self._sector_bounds[ring][sector]

    def get_sector_center_angle(self, ring: int, sector: int) -> float:
        """Возвращает центральный угол сектора в радианах."""
        start, end = self.get_sector_bounds(ring, sector)
        return (start + end) / 2

    def get_inner_neighbor(self, ring: int, sector: int) -> Cell | None:
        """Возвращает внутреннего соседа ячейки или None для центра."""
        if ring == 0:
            return None
        if ring == 1:
            return (0, 0)

        inner_count = self.cells_per_ring[ring - 1]
        current_count = self.cells_per_ring[ring]

        if current_count == inner_count:
            return (ring - 1, sector)
        return (ring - 1, sector // 2)

    def get_outer_neighbors(self, ring: int, sector: int) -> list[Cell]:
        """Возвращает внешних соседей ячейки (1 или 2 при разбиении кольца)."""
        if ring == self.num_rings - 1:
            return []
        if ring == 0:
            return [(1, i) for i in range(self.cells_per_ring[1])]

        outer_count = self.cells_per_ring[ring + 1]
        current_count = self.cells_per_ring[ring]

        if outer_count == current_count:
            return [(ring + 1, sector)]
        return [(ring + 1, sector * 2), (ring + 1, sector * 2 + 1)]

    def get_clockwise_neighbor(self, ring: int, sector: int) -> Cell:
        """Возвращает соседа по часовой стрелке в том же кольце."""
        if ring == 0:
            return (0, 0)
        count = self.cells_per_ring[ring]
        return (ring, (sector + 1) % count)

    def get_counter_clockwise_neighbor(self, ring: int, sector: int) -> Cell:
        """Возвращает соседа против часовой стрелки в том же кольце."""
        if ring == 0:
            return (0, 0)
        count = self.cells_per_ring[ring]
        return (ring, (sector - 1) % count)

    def iter_neighbor_candidates(self, ring: int, sector: int) -> list[Cell]:
        """Возвращает всех потенциальных соседей ячейки: внутренний, внешние, по кольцу."""
        neighbors: list[Cell] = []
        inner = self.get_inner_neighbor(ring, sector)
        if inner is not None:
            neighbors.append(inner)
        neighbors.extend(self.get_outer_neighbors(ring, sector))

        if ring > 0:
            neighbors.append(self.get_clockwise_neighbor(ring, sector))
            neighbors.append(self.get_counter_clockwise_neighbor(ring, sector))
        return neighbors

    def inner_neighbor_interval(self, ring: int, sector: int) -> tuple[Cell, float, float] | None:
        """Возвращает внутреннего соседа с угловым интервалом текущей ячейки."""
        inner = self.get_inner_neighbor(ring, sector)
        if inner is None:
            return None
        start, end = self.get_sector_bounds(ring, sector)
        return inner, start, end

    def outer_neighbor_intervals(self, ring: int, sector: int) -> list[tuple[Cell, float, float]]:
        """Возвращает внешних соседей с их угловыми интервалами."""
        intervals = []
        for neighbor in self.get_outer_neighbors(ring, sector):
            n_start, n_end = self.get_sector_bounds(*neighbor)
            intervals.append((neighbor, n_start, n_end))
        return intervals

    def _compute_bounds(self, ring: int, sector: int) -> tuple[float, float]:
        if ring == 0:
            return 0.0, 2 * math.pi
        count = self.cells_per_ring[ring]
        start = (sector / count) * 2 * math.pi
        end = ((sector + 1) / count) * 2 * math.pi
        return start, end

    def _validate_cell(self, ring: int, sector: int) -> None:
        if not (0 <= ring < self.num_rings):
            msg = f"Некорректное кольцо: {ring}"
            raise ValueError(msg)
        if ring > 0 and not (0 <= sector < self.cells_per_ring[ring]):
            msg = f"Некорректный сектор {sector} для кольца {ring}"
            raise ValueError(msg)


def build_topology(difficulty: Difficulty) -> PolarTopologyService:
    """
    Создаёт топологию полярного лабиринта с динамическим разбиением (subdivision).

    Число колец и базовое число секторов зависят от сложности;
    кольцо делится надвое, когда дуга ячейки становится слишком широкой.
    """
    lvl = effective_level(difficulty)
    num_rings = max(4, round(lerp(lvl, 5, 15)))

    base_sectors = max(6, round(lerp(lvl, 6, 12)))
    # Базовое количество должно быть чётным
    if base_sectors % 2 != 0:
        base_sectors += 1

    cells_per_ring: list[int] = [1]

    if num_rings > 1:
        current_sectors = base_sectors
        cells_per_ring.append(current_sectors)

        for ring in range(2, num_rings):
            # Вычисляем пропорцию ячейки (ширина дуги по отношению к радиусу)
            cell_width = (2 * math.pi * ring) / current_sectors

            # Если ячейка стала шире порога (обычно 1.8 - 2.0), делим её надвое
            if cell_width > 1.8:
                current_sectors *= 2

            cells_per_ring.append(current_sectors)

    return PolarTopologyService(cells_per_ring)


def build_connections(
    rng: random.Random,
    topology: PolarTopologyService,
    difficulty: Difficulty,
) -> Connections:
    """Строит граф соединений рекурсивным бэктрекером и добавляет проходы."""
    connections: Connections = {cell: set() for cell in topology.iter_cells()}
    _carve_maze(rng, topology, connections, difficulty)
    _add_extra_passages(rng, topology, connections, difficulty)
    return connections


def _carve_maze(
    rng: random.Random,
    topology: PolarTopologyService,
    connections: Connections,
    difficulty: Difficulty,
) -> None:
    """Строит каркас лабиринта рекурсивным бэктрекером."""
    start = (0, 0)
    stack = [start]
    visited: set[Cell] = {start}

    while stack:
        current = stack[-1]
        neighbors = [
            neighbor
            for neighbor in topology.iter_neighbor_candidates(*current)
            if neighbor not in visited
        ]

        if not neighbors:
            stack.pop()
            continue

        biased_neighbors = _apply_difficulty_bias(rng, current, neighbors, difficulty)
        chosen = rng.choice(biased_neighbors)
        connect_cells(connections, current, chosen)
        visited.add(chosen)
        stack.append(chosen)


def _add_extra_passages(
    rng: random.Random,
    topology: PolarTopologyService,
    connections: Connections,
    difficulty: Difficulty,
) -> None:
    """Добавляет дополнительные проходы в зависимости от сложности."""
    # L1=7% петель (меньше тупиков) … L7=0% (чистое дерево)
    passage_rate = max(0.0, lerp(effective_level(difficulty), 0.07, 0.0))

    extra_edges = int(topology.total_cells() * passage_rate)
    if extra_edges == 0:
        return

    cells = list(topology.iter_cells())
    for _ in range(extra_edges):
        cell = rng.choice(cells)
        candidates = topology.iter_neighbor_candidates(*cell)
        if not candidates:
            continue
        neighbor = rng.choice(candidates)
        if neighbor in connections[cell]:
            continue
        connect_cells(connections, cell, neighbor)


def connect_cells(connections: Connections, cell_a: Cell, cell_b: Cell) -> None:
    """Создаёт двустороннюю связь между ячейками."""
    connections[cell_a].add(cell_b)
    connections[cell_b].add(cell_a)


def radial_angle(
    topology: PolarTopologyService,
    inner_cell: Cell,
    outer_cell: Cell,
) -> float:
    """Возвращает угол радиальной границы между двумя смежными ячейками."""
    inner_start, inner_end = topology.get_sector_bounds(*inner_cell)
    outer_start, outer_end = topology.get_sector_bounds(*outer_cell)
    overlap_start = max(inner_start, outer_start)
    overlap_end = min(inner_end, outer_end)
    if overlap_start >= overlap_end:
        return (inner_start + inner_end) / 2
    return (overlap_start + overlap_end) / 2


def validate_connections(
    topology: PolarTopologyService,
    connections: Connections,
) -> None:
    """Проверяет симметрию и связность графа соединений."""
    all_cells = list(topology.iter_cells())
    for cell in all_cells:
        connections.setdefault(cell, set())

    for cell, neighbors in connections.items():
        for neighbor in neighbors:
            if cell not in connections.get(neighbor, set()):
                msg = f"Нарушена симметрия между {cell} и {neighbor}"
                raise ValueError(msg)

    start = (0, 0)
    visited = {start}
    queue = deque([start])

    while queue:
        current = queue.popleft()
        for neighbor in connections[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    if len(visited) != len(all_cells):
        msg = "Граф содержит изолированные области"
        raise ValueError(msg)


def _apply_difficulty_bias(
    rng: random.Random,
    current: Cell,
    neighbors: list[Cell],
    difficulty: Difficulty,
) -> list[Cell]:
    """
    Возвращает список соседей с учётом bias по сложности.

    EASY: идём радиально (bias к центру/от центра) — короткие пути.
    MEDIUM: равномерный выбор соседа.
    HARD: bias к angular-соседям (spiral bias) — длинные дуги, больше тупиков.

    Args:
        rng: Генератор случайных чисел
        current: Текущая ячейка
        neighbors: Список непосещённых соседей
        difficulty: Уровень сложности

    Returns:
        Отфильтрованный список соседей (с учётом весов)
    """
    ring, _ = current
    radial = [n for n in neighbors if n[0] != ring]
    angular = [n for n in neighbors if n[0] == ring]

    lvl = effective_level(difficulty)
    # L1=80% bias к радиальным (прямые пути к центру)
    # L7=80% bias к угловым (спирали, больше тупиков)
    radial_bias = lerp(lvl, 0.80, 0.0)
    angular_bias = lerp(lvl, 0.0, 0.80)

    if radial and rng.random() < radial_bias:
        return radial
    if angular and rng.random() < angular_bias:
        return angular
    return neighbors


def solve(connections: Connections, start: Cell, end: Cell) -> list[Cell]:
    """Находит кратчайший путь в полярном лабиринте с помощью BFS."""
    queue = deque([start])
    parents: dict[Cell, Cell | None] = {start: None}

    while queue:
        current = queue.popleft()
        if current == end:
            break

        for neighbor in connections[current]:
            if neighbor not in parents:
                parents[neighbor] = current
                queue.append(neighbor)

    if end not in parents:
        return []

    path: list[Cell] = []
    node: Cell | None = end
    while node is not None:
        path.append(node)
        node = parents[node]
    return path[::-1]


def generate_maze(
    rng: random.Random,
    width: int,
    height: int,
    difficulty: Difficulty,
) -> Maze:
    """
    Генерирует настоящий круглый лабиринт в полярных координатах (чисто графовый подход).

    Возвращает Maze с заполненными polar-полями (polar_connections, num_rings,
    cells_per_ring); декартовы grid/walls/start/end — только для совместимости.
    """
    grid_size = min(width, height)

    topology = build_topology(difficulty)
    connections = build_connections(rng, topology, difficulty)
    validate_connections(topology, connections)

    start = (0, 0)
    outer_cells = topology.cells_per_ring[-1]
    end = (topology.num_rings - 1, outer_cells // 2)

    solution = solve(connections, start, end)

    grid, center, max_radius = _compatibility_grid(grid_size)

    # Конвертируем полярные координаты старта и конца в декартовы для совместимости
    start_cartesian = (center, center)
    end_angle = end[1] * 2 * math.pi / outer_cells
    end_cartesian = (int(center + max_radius * math.cos(end_angle)), int(center + max_radius * math.sin(end_angle)))

    # Создаём декартовы стены для совместимости
    walls = [[[True, True, True, True] for _ in range(grid_size)] for _ in range(grid_size)]

    return Maze(
        grid=grid,
        width=grid_size,
        height=grid_size,
        start=start_cartesian,
        end=end_cartesian,
        difficulty=difficulty,
        shape=MazeShape.CIRCULAR,
        solution_path=solution,
        walls=walls,
        polar_connections={cell: set(neighbors) for cell, neighbors in connections.items()},
        num_rings=topology.num_rings,
        cells_per_ring=list(topology.cells_per_ring),
    )


def _compatibility_grid(grid_size: int) -> tuple[list[list[int]], int, int]:
    """
    Строит минимальный декартов grid для обратной совместимости и визуализации.

    Возвращает (grid, center, max_radius): круг единиц внутри радиуса,
    центр сетки и внутренний радиус в ячейках.
    """
    grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
    center = grid_size // 2
    max_radius = grid_size // 2 - 1

    for y in range(grid_size):
        for x in range(grid_size):
            dx = x - center
            dy = y - center
            distance = math.sqrt(dx * dx + dy * dy)
            if distance <= max_radius:
                grid[y][x] = 1

    return grid, center, max_radius
