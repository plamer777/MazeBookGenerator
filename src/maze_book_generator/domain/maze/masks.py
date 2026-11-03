"""Фабрики масок форм лабиринтов и утилиты работы с ними."""

import math
import random
from collections import deque

from maze_book_generator.domain.maze.difficulty import effective_level, lerp
from maze_book_generator.domain.maze.types import Mask, Point
from maze_book_generator.domain.models import Difficulty

# Шаги к 4-соседям: вверх, вправо, вниз, влево
_neighbor_steps: list[Point] = [(0, -1), (1, 0), (0, 1), (-1, 0)]


def diamond_mask(width: int, height: int) -> Mask:
    """Создаёт маску ромба."""
    mask: Mask = [[False for _ in range(width)] for _ in range(height)]

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


def heart_mask(width: int, height: int) -> Mask:
    """Создаёт маску сердца."""
    mask: Mask = [[False for _ in range(width)] for _ in range(height)]

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
        return diamond_mask(width, height)

    return mask


def triangular_mask(width: int, height: int) -> Mask:
    """Создаёт треугольную маску."""
    mask: Mask = [[False for _ in range(width)] for _ in range(height)]

    for y in range(height):
        # Ширина треугольника на данной высоте:
        # вершины (width//2, 0), (0, height-1), (width-1, height-1)
        triangle_width = (height - y) * width // height
        center_x = width // 2
        left_x = center_x - triangle_width // 2
        right_x = center_x + triangle_width // 2

        for x in range(width):
            if left_x <= x <= right_x:
                mask[y][x] = True

    return mask


def random_mask(rng: random.Random, width: int, height: int) -> Mask:
    """Создаёт случайную маску из круга со случайным шумом на краях."""
    mask: Mask = [[False for _ in range(width)] for _ in range(height)]

    center_x = width // 2
    center_y = height // 2

    for y in range(height):
        for x in range(width):
            dx = x - center_x
            dy = y - center_y
            distance = math.sqrt(dx * dx + dy * dy)

            max_distance = min(width, height) // 2
            if distance < max_distance:
                noise = rng.random() * 0.3
                if distance / max_distance + noise < 0.8:
                    mask[y][x] = True

    return mask


def chaotic_connected_mask(
    rng: random.Random,
    width: int,
    height: int,
    difficulty: Difficulty,
) -> Mask:
    """Создаёт связную хаотичную маску без изолированных островков."""
    mask: Mask = [[False for _ in range(width)] for _ in range(height)]

    total_cells = width * height
    fill_ratio = lerp(effective_level(difficulty), 0.82, 0.92)
    target_cells = max(min(total_cells, int(total_cells * fill_ratio)), max(width, height) * 2)

    cx = width // 2
    cy = height // 2
    mask[cy][cx] = True

    frontier: list[Point] = [(cx, cy)]
    carved = 1

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
            frontier.append(rng.choice(connected_cells))

        point = rng.choice(frontier)
        grown = _grow_cell(rng, mask, point, center=(cx, cy), size=(width, height))
        if grown is not None:
            frontier.append(grown)
            carved += 1
        elif point in frontier:
            frontier.remove(point)

    return mask


def _grow_cell(
    rng: random.Random,
    mask: Mask,
    point: Point,
    *,
    center: Point,
    size: tuple[int, int],
) -> Point | None:
    """
    Пытается вырасти из point в случайном направлении.

    Вероятность роста падает с удалением от центра — маска получается
    компактной, но с хаотичными краями. Возвращает новую ячейку или None.
    """
    width, height = size
    x, y = point
    directions = list(_neighbor_steps)
    rng.shuffle(directions)

    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < width and 0 <= ny < height):
            continue
        if mask[ny][nx]:
            continue

        dist = abs(nx - center[0]) + abs(ny - center[1])
        max_dist = max(1, center[0] + center[1])
        distance_penalty = dist / max_dist
        growth_chance = 0.92 - 0.30 * distance_penalty
        if rng.random() > growth_chance:
            continue

        mask[ny][nx] = True
        return (nx, ny)
    return None


def _flood_component(
    mask: Mask,
    start: Point,
    visited: set[Point],
    width: int,
    height: int,
) -> set[Point]:
    """Собирает 4-связную компоненту от start, пополняя visited (BFS)."""
    component: set[Point] = set()
    queue = deque([start])
    visited.add(start)

    while queue:
        cx, cy = queue.popleft()
        component.add((cx, cy))

        for dx, dy in _neighbor_steps:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if not mask[ny][nx] or (nx, ny) in visited:
                continue
            visited.add((nx, ny))
            queue.append((nx, ny))

    return component


def extract_largest_component(mask: Mask, width: int, height: int) -> Mask:
    """Оставляет только крупнейшую 4-связную компоненту маски."""
    visited: set[Point] = set()
    largest_component: set[Point] = set()

    for y in range(height):
        for x in range(width):
            if not mask[y][x] or (x, y) in visited:
                continue

            component = _flood_component(mask, (x, y), visited, width, height)
            if len(component) > len(largest_component):
                largest_component = component

    normalized_mask: Mask = [[False for _ in range(width)] for _ in range(height)]
    for x, y in largest_component:
        normalized_mask[y][x] = True
    return normalized_mask


def is_boundary_cell(mask: Mask, x: int, y: int, width: int, height: int) -> bool:
    """Проверяет, что ячейка находится на внешней границе маски."""
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        nx, ny = x + dx, y + dy
        if not (0 <= nx < width and 0 <= ny < height):
            return True
        if not mask[ny][nx]:
            return True
    return False


def pick_boundary_cell(mask: Mask, width: int, height: int) -> Point | None:
    """Выбирает верхнюю левую ячейку на границе формы для старта лабиринта."""
    boundary_cells = [
        (x, y)
        for y in range(height)
        for x in range(width)
        if mask[y][x] and is_boundary_cell(mask, x, y, width, height)
    ]
    if not boundary_cells:
        return None
    return min(boundary_cells, key=lambda cell: (cell[1], cell[0]))


def first_cell(mask: Mask) -> Point | None:
    """Находит первую ячейку внутри маски (сканирование слева направо сверху вниз)."""
    for y in range(len(mask)):
        for x in range(len(mask[0])):
            if mask[y][x]:
                return (x, y)
    return None


def last_cell(mask: Mask) -> Point | None:
    """Находит последнюю ячейку внутри маски (сканирование справа налево снизу вверх)."""
    for y in range(len(mask) - 1, -1, -1):
        for x in range(len(mask[0]) - 1, -1, -1):
            if mask[y][x]:
                return (x, y)
    return None
