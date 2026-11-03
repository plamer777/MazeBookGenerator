"""Поиск пути и проверки достижимости в grid-лабиринте со стенами."""

from collections import deque

from maze_book_generator.domain.maze.masks import is_boundary_cell
from maze_book_generator.domain.maze.types import Grid, Mask, Point, Walls


def iter_wall_neighbors(walls: Walls, x: int, y: int, width: int, height: int) -> list[Point]:
    """Возвращает соседей ячейки, до которых можно дойти без пересечения стен."""
    directions = [
        (0, -1, 0, 2),  # вверх
        (1, 0, 1, 3),   # вправо
        (0, 1, 2, 0),   # вниз
        (-1, 0, 3, 1),  # влево
    ]

    neighbors: list[Point] = []
    for dx, dy, wall_idx, neighbor_wall_idx in directions:
        nx, ny = x + dx, y + dy
        if (
            0 <= nx < width
            and 0 <= ny < height
            and not walls[y][x][wall_idx]
            and not walls[ny][nx][neighbor_wall_idx]
        ):
            neighbors.append((nx, ny))
    return neighbors


def solve_with_walls(
    walls: Walls,
    start: Point,
    end: Point,
    width: int,
    height: int,
) -> list[Point]:
    """Ищет кратчайший путь в сетке с учётом стен (BFS)."""
    queue = deque([start])
    parents: dict[Point, Point | None] = {start: None}

    while queue:
        x, y = queue.popleft()
        if (x, y) == end:
            break

        for nx, ny in iter_wall_neighbors(walls, x, y, width, height):
            if (nx, ny) not in parents:
                parents[nx, ny] = (x, y)
                queue.append((nx, ny))

    if end not in parents:
        return []

    path: list[Point] = []
    node: Point | None = end
    while node is not None:
        path.append(node)
        node = parents[node]
    return path[::-1]


def find_farthest_boundary_cell(
    walls: Walls,
    mask: Mask,
    start: Point,
    width: int,
    height: int,
) -> Point | None:
    """Находит самую дальнюю от старта достижимую граничную ячейку (BFS)."""
    queue = deque([start])
    distances: dict[Point, int] = {start: 0}

    farthest = start
    farthest_distance = 0

    while queue:
        x, y = queue.popleft()
        current_distance = distances[x, y]

        if is_boundary_cell(mask, x, y, width, height) and current_distance > farthest_distance:
            farthest = (x, y)
            farthest_distance = current_distance

        for nx, ny in iter_wall_neighbors(walls, x, y, width, height):
            if not mask[ny][nx]:
                continue
            if (nx, ny) in distances:
                continue
            distances[nx, ny] = current_distance + 1
            queue.append((nx, ny))

    if farthest == start:
        return None
    return farthest


def count_reachable_mask_cells(
    walls: Walls,
    mask: Mask,
    start: Point,
    width: int,
    height: int,
) -> int:
    """Считает число достижимых ячеек маски из заданного старта (BFS)."""
    if not mask[start[1]][start[0]]:
        return 0

    queue = deque([start])
    visited: set[Point] = {start}

    while queue:
        x, y = queue.popleft()
        for nx, ny in iter_wall_neighbors(walls, x, y, width, height):
            if not mask[ny][nx] or (nx, ny) in visited:
                continue
            visited.add((nx, ny))
            queue.append((nx, ny))

    return len(visited)


def is_valid_maze(grid: Grid) -> bool:
    """Проверяет, что лабиринт валидный (есть хотя бы один проход)."""
    return any(1 in row for row in grid)
