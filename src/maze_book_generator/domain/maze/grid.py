"""Построение grid-лабиринтов по формам: маска → прорезание → проверка → Maze.

Все grid-формы (прямоугольник, квадрат, треугольник, ромб, сердце, случайная,
хаотичная) используют один конвейер: фабрика маски определяет форму,
остальные шаги общие.
"""

import random

from maze_book_generator.domain.maze import carving, masks, solver
from maze_book_generator.domain.maze.difficulty import effective_level, lerp
from maze_book_generator.domain.maze.types import Mask, Walls
from maze_book_generator.domain.models import Difficulty, Maze, MazeShape
from maze_book_generator.settings import MAZE_CHAOTIC_MAX_ATTEMPTS, MAZE_MASKED_MAX_ATTEMPTS


def build_rectangular(
    rng: random.Random,
    width: int,
    height: int,
    difficulty: Difficulty,
) -> Maze:
    """
    Генерирует прямоугольный лабиринт со стенами между ячейками.

    Args:
        rng: Генератор случайных чисел
        width: Ширина лабиринта
        height: Высота лабиринта
        difficulty: Уровень сложности

    Returns:
        Объект Maze
    """
    grid_width = width
    grid_height = height

    # Стены между ячейками: walls[y][x] = [верх, право, низ, лево]
    walls = _new_walls(grid_width, grid_height)

    # Маска прямоугольной формы (все ячейки внутри)
    mask = [[True for _ in range(grid_width)] for _ in range(grid_height)]

    carving.carve_passages(rng, walls, mask, 0, 0, difficulty)

    start = (0, 0)
    end = (grid_width - 1, grid_height - 1)

    # Grid для обратной совместимости
    grid = [[1 for _ in range(grid_width)] for _ in range(grid_height)]

    if not solver.is_valid_maze(grid):
        return build_rectangular(rng, width, height, difficulty)

    solution = solver.solve_with_walls(walls, start, end, width, height)

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


def build_square(
    rng: random.Random,
    width: int,
    height: int,
    difficulty: Difficulty,
) -> Maze:
    """Генерирует квадратный лабиринт (сторона = min(width, height))."""
    size = min(width, height)

    walls = _new_walls(size, size)
    mask = [[True for _ in range(size)] for _ in range(size)]

    carving.carve_passages(rng, walls, mask, 0, 0, difficulty)

    start = (0, 0)
    end = (size - 1, size - 1)

    grid = [[1 for _ in range(size)] for _ in range(size)]
    solution = solver.solve_with_walls(walls, start, end, size, size)

    return Maze(
        grid=grid,
        width=size,
        height=size,
        start=start,
        end=end,
        difficulty=difficulty,
        shape=MazeShape.SQUARE,
        solution_path=solution,
        walls=walls,
    )


def build_masked(
    rng: random.Random,
    width: int,
    height: int,
    difficulty: Difficulty,
    shape: MazeShape,
    raw_mask: Mask,
) -> Maze:
    """Генерирует лабиринт по маске с гарантией связности и проходимости."""
    mask = masks.extract_largest_component(raw_mask, width, height)

    for _ in range(MAZE_MASKED_MAX_ATTEMPTS):
        maze = _try_carved_maze(rng, mask, difficulty, shape)
        if maze is not None:
            return maze

    return build_rectangular(rng, width, height, difficulty)


def build_diamond(
    rng: random.Random,
    width: int,
    height: int,
    difficulty: Difficulty,
) -> Maze:
    """Генерирует лабиринт в форме ромба."""
    return build_masked(rng, width, height, difficulty, MazeShape.DIAMOND, masks.diamond_mask(width, height))


def build_heart(
    rng: random.Random,
    width: int,
    height: int,
    difficulty: Difficulty,
) -> Maze:
    """Генерирует лабиринт в форме сердца."""
    return build_masked(rng, width, height, difficulty, MazeShape.HEART, masks.heart_mask(width, height))


def build_triangular(
    rng: random.Random,
    width: int,
    height: int,
    difficulty: Difficulty,
) -> Maze:
    """Генерирует треугольный лабиринт."""
    mask = masks.triangular_mask(width, height)

    start = masks.first_cell(mask)
    if not start:
        return build_rectangular(rng, width, height, difficulty)

    walls = _new_walls(width, height)
    carving.carve_passages(rng, walls, mask, start[0], start[1], difficulty)

    end = masks.last_cell(mask) or (width - 1, height - 1)

    grid = [[1 if mask[y][x] else 0 for x in range(width)] for y in range(height)]
    solution = solver.solve_with_walls(walls, start, end, width, height)

    return Maze(
        grid=grid,
        width=width,
        height=height,
        start=start,
        end=end,
        difficulty=difficulty,
        shape=MazeShape.TRIANGULAR,
        solution_path=solution,
        walls=walls,
    )


def build_random(
    rng: random.Random,
    width: int,
    height: int,
    difficulty: Difficulty,
) -> Maze:
    """Генерирует лабиринт случайной формы."""
    for _ in range(MAZE_MASKED_MAX_ATTEMPTS):
        raw_mask = masks.random_mask(rng, width, height)
        mask = masks.extract_largest_component(raw_mask, width, height)

        maze = _try_carved_maze(rng, mask, difficulty, MazeShape.RANDOM)
        if maze is not None:
            return maze

    return build_rectangular(rng, width, height, difficulty)


def build_chaotic(
    rng: random.Random,
    width: int,
    height: int,
    difficulty: Difficulty,
) -> Maze:
    """
    Генерирует хаотичный лабиринт с нерегулярной, но связной формой.

    Сетка слегка увеличивается, чтобы итоговая фигура занимала примерно
    ту же площадь, что и другие типы лабиринтов.
    """
    shape_scale = lerp(effective_level(difficulty), 1.22, 1.08)
    grid_width = max(8, round(width * shape_scale))
    grid_height = max(7, round(height * shape_scale))

    for _ in range(MAZE_CHAOTIC_MAX_ATTEMPTS):
        mask = masks.chaotic_connected_mask(rng, grid_width, grid_height, difficulty)

        maze = _try_carved_maze(
            rng, mask, difficulty, MazeShape.CHAOTIC,
            chaotic=True,
        )
        if maze is not None:
            return maze

    return build_rectangular(rng, width, height, difficulty)


def _new_walls(width: int, height: int) -> Walls:
    """Создаёт сетку со всеми поднятыми стенами: [верх, право, низ, лево]."""
    return [[[True, True, True, True] for _ in range(width)] for _ in range(height)]


def _try_carved_maze(
    rng: random.Random,
    mask: Mask,
    difficulty: Difficulty,
    shape: MazeShape,
    *,
    chaotic: bool = False,
) -> Maze | None:
    """
    Одна попытка построить проходимый лабиринт внутри маски.

    Размеры сетки выводятся из маски. Возвращает None, если попытка не удалась
    (нет граничной ячейки для старта, финиш совпал со стартом, нет решения
    или не все ячейки маски достижимы).
    """
    width = len(mask[0])
    height = len(mask)

    walls = _new_walls(width, height)

    start = masks.pick_boundary_cell(mask, width, height)
    if start is None:
        return None

    carving.carve_passages(rng, walls, mask, start[0], start[1], difficulty)
    if chaotic:
        carving.add_chaotic_shortcuts(rng, walls, mask, width, height, difficulty)

    end = solver.find_farthest_boundary_cell(walls, mask, start, width, height)
    if end is None or end == start:
        return None

    grid = [[1 if mask[y][x] else 0 for x in range(width)] for y in range(height)]
    solution = solver.solve_with_walls(walls, start, end, width, height)
    if not solution:
        return None

    total_cells = sum(1 for y in range(height) for x in range(width) if mask[y][x])
    reachable_cells = solver.count_reachable_mask_cells(walls, mask, start, width, height)
    if reachable_cells != total_cells:
        return None

    return Maze(
        grid=grid,
        width=width,
        height=height,
        start=start,
        end=end,
        difficulty=difficulty,
        shape=shape,
        solution_path=solution,
        walls=walls,
    )
