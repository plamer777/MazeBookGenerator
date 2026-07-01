"""Генератор лабиринтов с различными уровнями сложности."""

import math
import random
from collections import deque
from typing import Dict, Set

from src.domain.models import Difficulty, Maze, MazeShape
from src.domain.polar_topology_service import PolarTopologyService, Cell, Connections


class MazeGenerator:
    """Генератор лабиринтов на основе DFS с настройкой сложности."""

    def __init__(self, seed: int | None = None) -> None:
        """Инициализация генератора с опциональным seed для воспроизводимости."""
        if seed is not None:
            random.seed(seed)
        else:
            # Разный seed для каждого экземпляра для вариативности
            random.seed()

    @staticmethod
    def _lerp(level: float, lo: float, hi: float) -> float:
        """
        Линейная интерполяция параметра по уровню сложности 1-7.

        Args:
            level: Уровень 1..7 (допускается float)
            lo: Значение для уровня 1
            hi: Значение для уровня 7
        """
        return lo + (hi - lo) * (level - 1) / 6.0

    @staticmethod
    def _effective_level(difficulty: Difficulty) -> float:
        """
        Перекалиброванный уровень сложности для более плавной градации.

        Цели:
        - поднять минимальный порог (L1 ≈ прежний L3–L4),
        - сохранить верхнюю границу L7 = 7.0 без изменений,
        - сделать шаги между уровнями плавными через степенную кривую
          (power < 1 даёт concave-профиль: нижние уровни поднимаются сильно,
          верхние почти не затрагиваются).

        Таблица значений (lo=3.5, hi=7.0, power=0.55):
            L1 → 3.50  |  L2 → 4.27  |  L3 → 4.90
            L4 → 5.44  |  L5 → 5.93  |  L6 → 6.47  |  L7 → 7.00

        Returns:
            Эффективный уровень в диапазоне [3.5 .. 7.0]
        """
        lvl = difficulty.level
        lo, hi, power = 3.5, 7.0, 0.55
        t = (lvl - 1) / 6.0  # нормированное значение 0..1
        return lo + (hi - lo) * (t ** power)

    def generate(
        self,
        width: int,
        height: int,
        difficulty: Difficulty,
        shape: MazeShape = MazeShape.RECTANGULAR,
    ) -> Maze:
        """
        Генерирует лабиринт заданных размеров и сложности.

        Для grid-лабиринтов (не CIRCULAR) размер сетки масштабируется
        по сложности: EASY — реже сетка (просторнее), HARD — плотнее.
        Для CIRCULAR плотность задаётся через num_rings.

        Args:
            width: Базовая ширина лабиринта (количество ячеек)
            height: Базовая высота лабиринта (количество ячеек)
            difficulty: Уровень сложности
            shape: Форма лабиринта

        Returns:
            Объект Maze с сгенерированным лабиринтом
        """
        if shape == MazeShape.CIRCULAR:
            return self._generate_circular_maze(width, height, difficulty)

        # Используем перекалиброванный уровень: минимум сложнее, рост плавный.
        scale = self._lerp(self._effective_level(difficulty), 0.45, 2.0)
        scaled_w = max(6, round(width * scale))
        scaled_h = max(5, round(height * scale))

        if shape == MazeShape.SQUARE:
            return self._generate_square_maze(scaled_w, scaled_h, difficulty)
        elif shape == MazeShape.TRIANGULAR:
            return self._generate_triangular_maze(scaled_w, scaled_h, difficulty)
        elif shape == MazeShape.DIAMOND:
            return self._generate_diamond_maze(scaled_w, scaled_h, difficulty)
        elif shape == MazeShape.HEART:
            return self._generate_heart_maze(scaled_w, scaled_h, difficulty)
        elif shape == MazeShape.RANDOM:
            return self._generate_random_maze(scaled_w, scaled_h, difficulty)
        elif shape == MazeShape.CHAOTIC:
            return self._generate_chaotic_maze(scaled_w, scaled_h, difficulty)
        else:
            return self._generate_rectangular_maze(scaled_w, scaled_h, difficulty)

    def _generate_rectangular_maze(
        self,
        width: int,
        height: int,
        difficulty: Difficulty,
    ) -> Maze:
        """
        Генерирует прямоугольный лабиринт со стенами между ячейками.

        Args:
            width: Ширина лабиринта
            height: Высота лабиринта
            difficulty: Уровень сложности

        Returns:
            Объект Maze
        """
        # Используем размеры напрямую без коррекции на нечётность
        grid_width = width
        grid_height = height

        # Инициализируем стены между ячейками
        # walls[y][x] = [верх, право, низ, лево]
        walls = [[[True, True, True, True] for _ in range(grid_width)] for _ in range(grid_height)]

        # Создаём маску для прямоугольной формы (все ячейки внутри)
        mask = [[True for _ in range(grid_width)] for _ in range(grid_height)]

        # Генерируем лабиринт с использованием стен
        self._carve_passages_with_walls_and_mask(walls, mask, 0, 0, grid_width, grid_height, difficulty)

        # Устанавливаем старт и конец
        start = (0, 0)
        end = (grid_width - 1, grid_height - 1)

        # Создаём grid для обратной совместимости
        grid = [[1 for _ in range(grid_width)] for _ in range(grid_height)]

        # Проверяем валидность
        if not self._is_valid_maze(grid):
            return self._generate_rectangular_maze(width, height, difficulty)

        # Находим решение с учетом стен
        solution = self._solve_maze_with_walls(walls, start, end, width, height)

        return Maze(
            grid=grid,
            width=grid_width,
            height=grid_height,
            start=start,
            end=end,
            difficulty=difficulty,
            shape=MazeShape.RECTANGULAR,
            solution_path=solution,
            walls=walls,
        )

    def _generate_diamond_maze(
        self,
        width: int,
        height: int,
        difficulty: Difficulty,
    ) -> Maze:
        """Генерирует лабиринт в форме ромба."""
        mask = self._create_diamond_mask(width, height)
        return self._generate_masked_maze(width, height, difficulty, MazeShape.DIAMOND, mask)

    def _generate_heart_maze(
        self,
        width: int,
        height: int,
        difficulty: Difficulty,
    ) -> Maze:
        """Генерирует лабиринт в форме сердца."""
        mask = self._create_heart_mask(width, height)
        return self._generate_masked_maze(width, height, difficulty, MazeShape.HEART, mask)

    def _generate_masked_maze(
        self,
        width: int,
        height: int,
        difficulty: Difficulty,
        shape: MazeShape,
        raw_mask: list[list[bool]],
    ) -> Maze:
        """Генерирует лабиринт по маске с гарантией связности и проходимости."""
        grid_width = width
        grid_height = height
        mask = self._extract_largest_mask_component(raw_mask, grid_width, grid_height)

        max_attempts = 10
        for _ in range(max_attempts):
            walls = [[[True, True, True, True] for _ in range(grid_width)] for _ in range(grid_height)]

            start = self._pick_boundary_cell(mask, grid_width, grid_height)
            if start is None:
                continue

            self._carve_passages_with_walls_and_mask(
                walls,
                mask,
                start[0],
                start[1],
                grid_width,
                grid_height,
                difficulty,
            )

            end = self._find_farthest_boundary_reachable_cell(
                walls,
                mask,
                start,
                grid_width,
                grid_height,
            )
            if end is None or end == start:
                continue

            grid = [[1 if mask[y][x] else 0 for x in range(grid_width)] for y in range(grid_height)]
            solution = self._solve_maze_with_walls(walls, start, end, grid_width, grid_height)
            if not solution:
                continue

            total_cells = sum(1 for y in range(grid_height) for x in range(grid_width) if mask[y][x])
            reachable_cells = self._count_reachable_mask_cells(walls, mask, start, grid_width, grid_height)
            if reachable_cells != total_cells:
                continue

            return Maze(
                grid=grid,
                width=grid_width,
                height=grid_height,
                start=start,
                end=end,
                difficulty=difficulty,
                shape=shape,
                solution_path=solution,
                walls=walls,
            )

        return self._generate_rectangular_maze(width, height, difficulty)

    def _generate_square_maze(
        self,
        width: int,
        height: int,
        difficulty: Difficulty,
    ) -> Maze:
        """
        Генерирует квадратный лабиринт.

        Args:
            width: Ширина лабиринта
            height: Высота лабиринта
            difficulty: Уровень сложности

        Returns:
            Объект Maze
        """
        # Используем минимальный размер для квадрата
        size = min(width, height)
        grid_size = size

        # Инициализируем стены
        walls = [[[True, True, True, True] for _ in range(grid_size)] for _ in range(grid_size)]

        # Маска для квадрата (все ячейки внутри)
        mask = [[True for _ in range(grid_size)] for _ in range(grid_size)]

        # Генерируем лабиринт
        self._carve_passages_with_walls_and_mask(walls, mask, 0, 0, grid_size, grid_size, difficulty)

        # Старт и конец
        start = (0, 0)
        end = (grid_size - 1, grid_size - 1)

        # Grid для обратной совместимости
        grid = [[1 for _ in range(grid_size)] for _ in range(grid_size)]

        solution = self._solve_maze_with_walls(walls, start, end, grid_size, grid_size)

        return Maze(
            grid=grid,
            width=grid_size,
            height=grid_size,
            start=start,
            end=end,
            difficulty=difficulty,
            shape=MazeShape.SQUARE,
            solution_path=solution,
            walls=walls,
        )

    def _generate_triangular_maze(
        self,
        width: int,
        height: int,
        difficulty: Difficulty,
    ) -> Maze:
        """
        Генерирует треугольный лабиринт.

        Args:
            width: Ширина лабиринта
            height: Высота лабиринта
            difficulty: Уровень сложности

        Returns:
            Объект Maze
        """
        grid_width = width
        grid_height = height

        # Инициализируем стены
        walls = [[[True, True, True, True] for _ in range(grid_width)] for _ in range(grid_height)]

        # Создаём треугольную маску
        mask = self._create_triangular_mask(grid_width, grid_height)

        # Находим первую ячейку внутри маски для старта
        start = self._find_first_cell_in_mask(mask)
        if not start:
            return self._generate_rectangular_maze(width, height, difficulty)

        # Генерируем лабиринт внутри маски
        self._carve_passages_with_walls_and_mask(walls, mask, start[0], start[1], grid_width, grid_height, difficulty)

        # Находим последнюю ячейку внутри маски для конца
        end = self._find_last_cell_in_mask(mask)
        if not end:
            end = (grid_width - 1, grid_height - 1)

        # Grid для обратной совместимости
        grid = [[1 if mask[y][x] else 0 for x in range(grid_width)] for y in range(grid_height)]

        solution = self._solve_maze_with_walls(walls, start, end, grid_width, grid_height)

        return Maze(
            grid=grid,
            width=grid_width,
            height=grid_height,
            start=start,
            end=end,
            difficulty=difficulty,
            shape=MazeShape.TRIANGULAR,
            solution_path=solution,
            walls=walls,
        )

    def _generate_random_maze(
        self,
        width: int,
        height: int,
        difficulty: Difficulty,
    ) -> Maze:
        """
        Генерирует лабиринт случайной формы.

        Args:
            width: Ширина лабиринта
            height: Высота лабиринта
            difficulty: Уровень сложности

        Returns:
            Объект Maze
        """
        grid_width = width
        grid_height = height

        max_attempts = 10
        for _ in range(max_attempts):
            walls = [[[True, True, True, True] for _ in range(grid_width)] for _ in range(grid_height)]
            raw_mask = self._create_random_mask(grid_width, grid_height)
            mask = self._extract_largest_mask_component(raw_mask, grid_width, grid_height)

            start = self._pick_boundary_cell(mask, grid_width, grid_height)
            if start is None:
                continue

            self._carve_passages_with_walls_and_mask(walls, mask, start[0], start[1], grid_width, grid_height, difficulty)

            end = self._find_farthest_boundary_reachable_cell(
                walls,
                mask,
                start,
                grid_width,
                grid_height,
            )
            if end is None or end == start:
                continue

            grid = [[1 if mask[y][x] else 0 for x in range(grid_width)] for y in range(grid_height)]
            solution = self._solve_maze_with_walls(walls, start, end, grid_width, grid_height)
            if not solution:
                continue

            total_cells = sum(1 for y in range(grid_height) for x in range(grid_width) if mask[y][x])
            reachable_cells = self._count_reachable_mask_cells(walls, mask, start, grid_width, grid_height)
            if reachable_cells != total_cells:
                continue

            return Maze(
                grid=grid,
                width=grid_width,
                height=grid_height,
                start=start,
                end=end,
                difficulty=difficulty,
                shape=MazeShape.RANDOM,
                solution_path=solution,
                walls=walls,
            )

        return self._generate_rectangular_maze(width, height, difficulty)

    def _generate_circular_maze(
        self,
        width: int,
        height: int,
        difficulty: Difficulty,
    ) -> Maze:
        """
        Генерирует настоящий круглый лабиринт с использованием полярных координат (чисто графовый подход).

        Args:
            width: Ширина лабиринта
            height: Высота лабиринта
            difficulty: Уровень сложности

        Returns:
            Объект Maze
        """
        grid_size = min(width, height)

        topology = self._build_polar_topology(difficulty)
        connections = self._build_polar_connections(topology, difficulty)
        topology.validate_connections(connections)

        start = (0, 0)
        outer_cells = topology.cells_per_ring[-1]
        end = (topology.num_rings - 1, outer_cells // 2)

        solution = self._solve_polar_maze(connections, start, end, topology)

        # Создаём минимальный grid ТОЛЬКО для обратной совместимости и визуализации
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

        # Конвертируем полярные координаты старта и конца в декартовы для совместимости
        start_cartesian = (center, center)
        end_radius = max_radius
        end_angle = end[1] * 2 * math.pi / outer_cells
        end_cartesian = (int(center + end_radius * math.cos(end_angle)), int(center + end_radius * math.sin(end_angle)))

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

    def _build_polar_topology(self, difficulty: Difficulty) -> PolarTopologyService:
        """
        Создаёт топологию полярного лабиринта с динамическим разбиением (subdivision).
        """
        lvl = self._effective_level(difficulty)
        num_rings = max(4, round(self._lerp(lvl, 5, 15)))

        base_sectors = max(6, round(self._lerp(lvl, 6, 12)))
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

    def _build_polar_connections(
        self,
        topology: PolarTopologyService,
        difficulty: Difficulty,
    ) -> Connections:
        """Строит граф соединений с помощью рекурсивного бэктрекера."""

        connections: Connections = {cell: set() for cell in topology.iter_cells()}
        self._carve_polar_maze(topology, connections, difficulty)
        self._add_extra_polar_passages(topology, connections, difficulty)
        return connections

    def _carve_polar_maze(
        self,
        topology: PolarTopologyService,
        connections: Connections,
        difficulty: Difficulty,
    ) -> None:
        """Строит каркас лабиринта рекурсивным бэктрекером."""

        start = (0, 0)
        stack = [start]
        visited: Set[Cell] = {start}

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

            biased_neighbors = self._apply_difficulty_bias(current, neighbors, difficulty)
            chosen = random.choice(biased_neighbors)
            self._connect_cells(connections, current, chosen)
            visited.add(chosen)
            stack.append(chosen)

    def _add_extra_polar_passages(
        self,
        topology: PolarTopologyService,
        connections: Connections,
        difficulty: Difficulty,
    ) -> None:
        """Добавляет дополнительные проходы в зависимости от сложности."""

        # L1=7% петель (меньше тупиков) … L7=0% (чистое дерево)
        passage_rate = max(0.0, self._lerp(self._effective_level(difficulty), 0.07, 0.0))

        extra_edges = int(topology.total_cells() * passage_rate)
        if extra_edges == 0:
            return

        cells = list(topology.iter_cells())
        for _ in range(extra_edges):
            cell = random.choice(cells)
            candidates = topology.iter_neighbor_candidates(*cell)
            if not candidates:
                continue
            neighbor = random.choice(candidates)
            if neighbor in connections[cell]:
                continue
            self._connect_cells(connections, cell, neighbor)

    def _connect_cells(
        self,
        connections: Connections,
        cell_a: Cell,
        cell_b: Cell,
    ) -> None:
        """Создаёт двустороннюю связь между ячейками."""

        connections[cell_a].add(cell_b)
        connections[cell_b].add(cell_a)
        assert cell_a in connections[cell_b], "Нарушена симметрия графа"

    def _apply_difficulty_bias(
        self,
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
            current: Текущая ячейка
            neighbors: Список непосещённых соседей
            difficulty: Уровень сложности

        Returns:
            Отфильтрованный список соседей (с учётом весов)
        """
        ring, _ = current
        radial = [n for n in neighbors if n[0] != ring]
        angular = [n for n in neighbors if n[0] == ring]

        lvl = self._effective_level(difficulty)
        # L1=80% bias к радиальным (прямые пути к центру)
        # L7=80% bias к угловым (спирали, больше тупиков)
        radial_bias  = self._lerp(lvl, 0.80, 0.0)
        angular_bias = self._lerp(lvl, 0.0, 0.80)

        if radial and random.random() < radial_bias:
            return radial
        if angular and random.random() < angular_bias:
            return angular
        return neighbors

    def _generate_chaotic_maze(
        self,
        width: int,
        height: int,
        difficulty: Difficulty,
    ) -> Maze:
        """
        Генерирует хаотичный лабиринт с нерегулярной формой, но связный, со стенами.

        Args:
            width: Ширина лабиринта
            height: Высота лабиринта
            difficulty: Уровень сложности

        Returns:
            Объект Maze
        """
        # Для хаотичной формы слегка увеличиваем сетку, чтобы итоговая фигура
        # занимала примерно ту же площадь, что и другие типы лабиринтов.
        shape_scale = self._lerp(self._effective_level(difficulty), 1.22, 1.08)
        grid_width = max(8, round(width * shape_scale))
        grid_height = max(7, round(height * shape_scale))

        max_attempts = 8
        for _ in range(max_attempts):
            walls = [[[True, True, True, True] for _ in range(grid_width)] for _ in range(grid_height)]
            mask = self._create_chaotic_connected_mask(grid_width, grid_height, difficulty)

            start = self._pick_boundary_cell(mask, grid_width, grid_height)
            if start is None:
                continue

            self._carve_passages_with_walls_and_mask(
                walls,
                mask,
                start[0],
                start[1],
                grid_width,
                grid_height,
                difficulty,
            )
            self._add_chaotic_shortcuts(walls, mask, grid_width, grid_height, difficulty)

            end = self._find_farthest_boundary_reachable_cell(
                walls,
                mask,
                start,
                grid_width,
                grid_height,
            )
            if end is None or end == start:
                continue

            grid = [[1 if mask[y][x] else 0 for x in range(grid_width)] for y in range(grid_height)]
            solution = self._solve_maze_with_walls(walls, start, end, grid_width, grid_height)
            if not solution:
                continue

            total_cells = sum(1 for y in range(grid_height) for x in range(grid_width) if mask[y][x])
            reachable_cells = self._count_reachable_mask_cells(walls, mask, start, grid_width, grid_height)
            if reachable_cells != total_cells:
                continue

            return Maze(
                grid=grid,
                width=grid_width,
                height=grid_height,
                start=start,
                end=end,
                difficulty=difficulty,
                shape=MazeShape.CHAOTIC,
                solution_path=solution,
                walls=walls,
            )

        return self._generate_rectangular_maze(width, height, difficulty)

    def _create_chaotic_connected_mask(
        self,
        width: int,
        height: int,
        difficulty: Difficulty,
    ) -> list[list[bool]]:
        """Создаёт связную хаотичную маску без изолированных островков."""
        mask = [[False for _ in range(width)] for _ in range(height)]

        total_cells = width * height
        fill_ratio = self._lerp(self._effective_level(difficulty), 0.82, 0.92)
        target_cells = max(min(total_cells, int(total_cells * fill_ratio)), max(width, height) * 2)

        cx = width // 2
        cy = height // 2
        mask[cy][cx] = True

        frontier: list[tuple[int, int]] = [(cx, cy)]
        carved = 1
        directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]

        while carved < target_cells:
            if not frontier:
                connected_cells = [
                    (x, y)
                    for y in range(height)
                    for x in range(width)
                    if mask[y][x]
                ]
                if not connected_cells:
                    break
                frontier.append(random.choice(connected_cells))

            x, y = random.choice(frontier)
            random.shuffle(directions)
            expanded = False

            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    continue
                if mask[ny][nx]:
                    continue

                dist = abs(nx - cx) + abs(ny - cy)
                max_dist = max(1, cx + cy)
                distance_penalty = dist / max_dist
                growth_chance = 0.92 - 0.30 * distance_penalty
                if random.random() > growth_chance:
                    continue

                mask[ny][nx] = True
                frontier.append((nx, ny))
                carved += 1
                expanded = True
                break

            if not expanded and (x, y) in frontier:
                frontier.remove((x, y))

        return mask

    def _create_diamond_mask(self, width: int, height: int) -> list[list[bool]]:
        """Создаёт маску ромба."""
        mask = [[False for _ in range(width)] for _ in range(height)]

        cx = (width - 1) / 2.0
        cy = (height - 1) / 2.0
        rx = max(1.0, width / 2.2)
        ry = max(1.0, height / 2.2)

        for y in range(height):
            for x in range(width):
                norm_x = abs((x - cx) / rx)
                norm_y = abs((y - cy) / ry)
                if norm_x + norm_y <= 1.0:
                    mask[y][x] = True

        return mask

    def _create_heart_mask(self, width: int, height: int) -> list[list[bool]]:
        """Создаёт маску сердца."""
        mask = [[False for _ in range(width)] for _ in range(height)]

        cx = (width - 1) / 2.0
        cy = (height - 1) / 2.0
        sx = max(1.0, width / 2.3)
        sy = max(1.0, height / 2.3)

        for y in range(height):
            for x in range(width):
                nx = (x - cx) / sx
                ny = (cy - y) / sy
                value = (nx * nx + ny * ny - 1) ** 3 - nx * nx * (ny ** 3)
                if value <= 0:
                    mask[y][x] = True

        filled_cells = sum(1 for row in mask for cell in row if cell)
        minimum_cells = max(6, min(width, height))
        if filled_cells < minimum_cells:
            return self._create_diamond_mask(width, height)

        return mask

    def _pick_boundary_cell(
        self,
        mask: list[list[bool]],
        width: int,
        height: int,
    ) -> tuple[int, int] | None:
        """Выбирает ячейку на границе формы для старта лабиринта."""
        boundary_cells = [
            (x, y)
            for y in range(height)
            for x in range(width)
            if mask[y][x] and self._is_mask_boundary_cell(mask, x, y, width, height)
        ]
        if not boundary_cells:
            return None
        return min(boundary_cells, key=lambda cell: (cell[1], cell[0]))

    def _is_mask_boundary_cell(
        self,
        mask: list[list[bool]],
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> bool:
        """Проверяет, что ячейка находится на внешней границе маски."""
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                return True
            if not mask[ny][nx]:
                return True
        return False

    def _add_chaotic_shortcuts(
        self,
        walls: list[list[list[bool]]],
        mask: list[list[bool]],
        width: int,
        height: int,
        difficulty: Difficulty,
    ) -> None:
        """Добавляет дополнительные локальные проходы для более хаотичного рисунка."""
        directions = [(0, -1, 0, 2), (1, 0, 1, 3), (0, 1, 2, 0), (-1, 0, 3, 1)]
        inside_cells = [(x, y) for y in range(height) for x in range(width) if mask[y][x]]
        if not inside_cells:
            return

        num_walks = max(2, round(self._lerp(self._effective_level(difficulty), 6, 18)))
        walk_len_min = 4
        walk_len_max = max(walk_len_min + 1, round(self._lerp(self._effective_level(difficulty), 10, 20)))

        for _ in range(num_walks):
            x, y = random.choice(inside_cells)
            walk_length = random.randint(walk_len_min, walk_len_max)

            for _ in range(walk_length):
                candidates = []
                for dx, dy, wall_current, wall_neighbor in directions:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and mask[ny][nx]:
                        candidates.append((nx, ny, wall_current, wall_neighbor))

                if not candidates:
                    break

                nx, ny, wall_current, wall_neighbor = random.choice(candidates)
                walls[y][x][wall_current] = False
                walls[ny][nx][wall_neighbor] = False
                x, y = nx, ny

    def _find_farthest_boundary_reachable_cell(
        self,
        walls: list[list[list[bool]]],
        mask: list[list[bool]],
        start: tuple[int, int],
        width: int,
        height: int,
    ) -> tuple[int, int] | None:
        """Находит самую дальнюю от старта достижимую граничную ячейку."""
        queue = deque([start])
        distances: dict[tuple[int, int], int] = {start: 0}

        farthest = start
        farthest_distance = 0

        while queue:
            x, y = queue.popleft()
            current_distance = distances[(x, y)]

            if self._is_mask_boundary_cell(mask, x, y, width, height) and current_distance > farthest_distance:
                farthest = (x, y)
                farthest_distance = current_distance

            for nx, ny in self._iter_wall_neighbors(walls, x, y, width, height):
                if not mask[ny][nx]:
                    continue
                if (nx, ny) in distances:
                    continue
                distances[(nx, ny)] = current_distance + 1
                queue.append((nx, ny))

        if farthest == start:
            return None
        return farthest

    def _extract_largest_mask_component(
        self,
        mask: list[list[bool]],
        width: int,
        height: int,
    ) -> list[list[bool]]:
        """Оставляет только крупнейшую 4-связную компоненту маски."""
        visited: set[tuple[int, int]] = set()
        largest_component: set[tuple[int, int]] = set()

        for y in range(height):
            for x in range(width):
                if not mask[y][x] or (x, y) in visited:
                    continue

                component: set[tuple[int, int]] = set()
                queue = deque([(x, y)])
                visited.add((x, y))

                while queue:
                    cx, cy = queue.popleft()
                    component.add((cx, cy))

                    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                        nx, ny = cx + dx, cy + dy
                        if not (0 <= nx < width and 0 <= ny < height):
                            continue
                        if not mask[ny][nx] or (nx, ny) in visited:
                            continue
                        visited.add((nx, ny))
                        queue.append((nx, ny))

                if len(component) > len(largest_component):
                    largest_component = component

        normalized_mask = [[False for _ in range(width)] for _ in range(height)]
        for x, y in largest_component:
            normalized_mask[y][x] = True
        return normalized_mask

    def _count_reachable_mask_cells(
        self,
        walls: list[list[list[bool]]],
        mask: list[list[bool]],
        start: tuple[int, int],
        width: int,
        height: int,
    ) -> int:
        """Считает число достижимых ячеек маски из заданного старта."""
        if not mask[start[1]][start[0]]:
            return 0

        queue = deque([start])
        visited: set[tuple[int, int]] = {start}

        while queue:
            x, y = queue.popleft()
            for nx, ny in self._iter_wall_neighbors(walls, x, y, width, height):
                if not mask[ny][nx] or (nx, ny) in visited:
                    continue
                visited.add((nx, ny))
                queue.append((nx, ny))

        return len(visited)

    def _is_valid_maze(self, grid: list[list[int]]) -> bool:
        """
        Проверяет, что лабиринт валидный (есть проходы).

        Args:
            grid: Сетка лабиринта

        Returns:
            True если лабиринт валидный
        """
        # Проверяем, что есть хотя бы один проход
        for row in grid:
            if 1 in row:
                return True
        return False

    def _carve_passages_with_walls_and_mask(
        self,
        walls: list[list[list[bool]]],
        mask: list[list[bool]],
        x: int,
        y: int,
        width: int,
        height: int,
        difficulty: Difficulty,
    ) -> None:
        """
        Итеративно прокладывает проходы (DFS) внутри маски с difficulty bias.

        Args:
            walls: Стены между ячейками
            mask: Маска формы (True=внутри формы, False=снаружи)
            x: Начальная координата X
            y: Начальная координата Y
            width: Ширина сетки
            height: Высота сетки
            difficulty: Уровень сложности
        """
        directions = [
            (0, -1, 0, 2),  # вверх
            (1, 0, 1, 3),   # вправо
            (0, 1, 2, 0),   # вниз
            (-1, 0, 3, 1),  # влево
        ]

        stack: list[tuple[int, int, int | None]] = [(x, y, None)]
        visited: set[tuple[int, int]] = {(x, y)}

        while stack:
            cx, cy, prev_dir = stack[-1]

            unvisited = [
                (dx, dy, wc, wn)
                for dx, dy, wc, wn in directions
                if 0 <= cx + dx < width
                and 0 <= cy + dy < height
                and mask[cy + dy][cx + dx]
                and (cx + dx, cy + dy) not in visited
            ]

            if not unvisited:
                stack.pop()
                continue

            chosen = self._pick_direction(unvisited, prev_dir, difficulty)
            dx, dy, wall_current, wall_neighbor = chosen
            nx, ny = cx + dx, cy + dy

            walls[cy][cx][wall_current] = False
            walls[ny][nx][wall_neighbor] = False
            visited.add((nx, ny))
            stack.append((nx, ny, wall_current))

        self._add_loops_by_difficulty(walls, width, height, difficulty, mask=mask)

    def _pick_direction(
        self,
        candidates: list[tuple[int, int, int, int]],
        prev_wall: int | None,
        difficulty: Difficulty,
    ) -> tuple[int, int, int, int]:
        """
        Выбирает следующее направление с учётом сложности.

        EASY: 65% вероятность продолжить в том же направлении (длинные прямые коридоры).
        MEDIUM: равномерный случайный выбор (стандартный DFS).
        HARD: 65% вероятность сменить направление (больше развилок и тупиков).

        Args:
            candidates: Список доступных направлений (dx, dy, wall_current, wall_neighbor)
            prev_wall: Индекс стены последнего хода (None в начале)
            difficulty: Уровень сложности

        Returns:
            Выбранное направление
        """
        if prev_wall is None or len(candidates) == 1:
            return random.choice(candidates)

        same = [d for d in candidates if d[2] == prev_wall]
        other = [d for d in candidates if d[2] != prev_wall]

        lvl = self._effective_level(difficulty)
        # L1=80% продолжить прямо (длинные коридоры)
        # L7=80% сменить направление (больше развилок и тупиков)
        straight_bias = self._lerp(lvl, 0.80, 0.0)
        turn_bias     = self._lerp(lvl, 0.0, 0.80)

        if same and random.random() < straight_bias:
            return same[0]
        if other and random.random() < turn_bias:
            return random.choice(other)
        return random.choice(candidates)

    def _add_loops_by_difficulty(
        self,
        walls: list[list[list[bool]]],
        width: int,
        height: int,
        difficulty: Difficulty,
        mask: list[list[bool]] | None,
    ) -> None:
        """
        Добавляет петли (дополнительные проходы) после DFS для контроля сложности.

        EASY: ~4% ячеек получают лишние проходы (меньше тупиков, легче ориентироваться).
        MEDIUM: ~1.5% ячеек.
        HARD: петли не добавляются (чистое дерево, максимум тупиков).

        Args:
            walls: Стены лабиринта
            width: Ширина сетки
            height: Высота сетки
            difficulty: Уровень сложности
            mask: Маска формы или None для прямоугольника
        """
        # L1=6% петель, L7=0% (чистое дерево без доп. проходов)
        loop_rate = max(0.0, self._lerp(self._effective_level(difficulty), 0.06, 0.0))

        if loop_rate == 0.0:
            return

        directions = [(0, -1, 0, 2), (1, 0, 1, 3), (0, 1, 2, 0), (-1, 0, 3, 1)]
        total_cells = sum(
            1
            for y in range(height)
            for x in range(width)
            if mask is None or mask[y][x]
        )
        num_loops = int(total_cells * loop_rate)

        candidates = [
            (x, y)
            for y in range(height)
            for x in range(width)
            if mask is None or mask[y][x]
        ]

        added = 0
        attempts = 0
        while added < num_loops and attempts < num_loops * 10:
            attempts += 1
            x, y = random.choice(candidates)
            dx, dy, wc, wn = random.choice(directions)
            nx, ny = x + dx, y + dy
            in_bounds = 0 <= nx < width and 0 <= ny < height
            in_mask = mask is None or (in_bounds and mask[ny][nx])
            if in_bounds and in_mask and walls[y][x][wc]:
                walls[y][x][wc] = False
                walls[ny][nx][wn] = False
                added += 1

    def _solve_maze_with_walls(
        self,
        walls: list[list[list[bool]]],
        start: tuple[int, int],
        end: tuple[int, int],
        width: int,
        height: int,
    ) -> list[tuple[int, int]]:
        """Ищет кратчайший путь в сетке с учётом стен (BFS)."""

        from collections import deque

        queue = deque([start])
        parents: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

        while queue:
            x, y = queue.popleft()
            if (x, y) == end:
                break

            neighbors = self._iter_wall_neighbors(walls, x, y, width, height)
            for nx, ny in neighbors:
                if (nx, ny) not in parents:
                    parents[(nx, ny)] = (x, y)
                    queue.append((nx, ny))

        if end not in parents:
            return []

        path: list[tuple[int, int]] = []
        node: tuple[int, int] | None = end
        while node is not None:
            path.append(node)
            node = parents[node]
        return path[::-1]

    def _iter_wall_neighbors(
        self,
        walls: list[list[list[bool]]],
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> list[tuple[int, int]]:
        """Возвращает соседей ячейки, учитывая отсутствующие стены."""

        directions = [
            (0, -1, 0, 2),  # вверх
            (1, 0, 1, 3),   # вправо
            (0, 1, 2, 0),   # вниз
            (-1, 0, 3, 1),  # влево
        ]

        neighbors: list[tuple[int, int]] = []
        for dx, dy, wall_idx, neighbor_wall_idx in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                if not walls[y][x][wall_idx] and not walls[ny][nx][neighbor_wall_idx]:
                    neighbors.append((nx, ny))
        return neighbors

    def _create_triangular_mask(self, width: int, height: int) -> list[list[bool]]:
        """Создаёт треугольную маску."""
        mask = [[False for _ in range(width)] for _ in range(height)]

        for y in range(height):
            for x in range(width):
                # Треугольник: верхняя часть равнобедренного треугольника
                # Проверяем, находится ли точка внутри треугольника
                # Вершины: (width//2, 0), (0, height-1), (width-1, height-1)
                if y >= 0 and y < height:
                    # Ширина треугольника на данной высоте
                    triangle_width = (height - y) * width // height
                    center_x = width // 2
                    left_x = center_x - triangle_width // 2
                    right_x = center_x + triangle_width // 2

                    if left_x <= x <= right_x:
                        mask[y][x] = True

        return mask

    def _create_random_mask(self, width: int, height: int) -> list[list[bool]]:
        """Создаёт случайную маску."""
        mask = [[False for _ in range(width)] for _ in range(height)]

        # Создаём случайную форму с помощью простых фигур
        # Центр
        center_x = width // 2
        center_y = height // 2

        for y in range(height):
            for x in range(width):
                # Расстояние от центра
                dx = x - center_x
                dy = y - center_y
                distance = math.sqrt(dx * dx + dy * dy)

                # Случайная форма на основе расстояния и случайного шума
                max_distance = min(width, height) // 2
                if distance < max_distance:
                    # Добавляем случайность
                    noise = random.random() * 0.3
                    if distance / max_distance + noise < 0.8:
                        mask[y][x] = True

        return mask

    def _find_first_cell_in_mask(self, mask: list[list[bool]]) -> tuple[int, int] | None:
        """Находит первую ячейку внутри маски."""
        for y in range(len(mask)):
            for x in range(len(mask[0])):
                if mask[y][x]:
                    return (x, y)
        return None

    def _find_last_cell_in_mask(self, mask: list[list[bool]]) -> tuple[int, int] | None:
        """Находит последнюю ячейку внутри маски."""
        for y in range(len(mask) - 1, -1, -1):
            for x in range(len(mask[0]) - 1, -1, -1):
                if mask[y][x]:
                    return (x, y)
        return None

    def _solve_polar_maze(
        self,
        connections: Connections,
        start: Cell,
        end: Cell,
        topology: PolarTopologyService,
    ) -> list[Cell]:
        """Находит кратчайший путь в полярном лабиринте с помощью BFS."""

        queue = deque([start])
        parents: Dict[Cell, Cell | None] = {start: None}

        while queue:
            current = queue.popleft()
            if current == end:
                break

            for neighbor in connections[current]:
                assert current in connections[neighbor], "Нарушена симметрия графа"
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
