"""Прорезание проходов, петель и хаотичных шорткатов в grid-лабиринте."""

import random

from maze_book_generator.domain.maze.difficulty import effective_level, lerp
from maze_book_generator.domain.maze.types import Mask, Walls
from maze_book_generator.domain.models import Difficulty

# Шаг прорезания: (dx, dy, стена текущей ячейки, стена соседа)
Step = tuple[int, int, int, int]

# Направления: вверх, вправо, вниз, влево (приватная таблица стен)
_directions: list[Step] = [
    (0, -1, 0, 2),
    (1, 0, 1, 3),
    (0, 1, 2, 0),
    (-1, 0, 3, 1),
]


def carve_passages(
    rng: random.Random,
    walls: Walls,
    mask: Mask,
    x: int,
    y: int,
    difficulty: Difficulty,
) -> None:
    """
    Итеративно прокладывает проходы (DFS) внутри маски с difficulty bias.

    Размеры сетки выводятся из маски (height × width ячеек).

    Args:
        rng: Генератор случайных чисел (сеединый)
        walls: Стены между ячейками (модифицируются на месте)
        mask: Маска формы (True=внутри формы, False=снаружи)
        x: Начальная координата X
        y: Начальная координата Y
        difficulty: Уровень сложности
    """
    width = len(mask[0])
    height = len(mask)

    stack: list[tuple[int, int, int | None]] = [(x, y, None)]
    visited: set[tuple[int, int]] = {(x, y)}

    while stack:
        cx, cy, prev_dir = stack[-1]

        unvisited = [
            (dx, dy, wc, wn)
            for dx, dy, wc, wn in _directions
            if 0 <= cx + dx < width
            and 0 <= cy + dy < height
            and mask[cy + dy][cx + dx]
            and (cx + dx, cy + dy) not in visited
        ]

        if not unvisited:
            stack.pop()
            continue

        chosen = _pick_direction(rng, unvisited, prev_dir, difficulty)
        dx, dy, wall_current, wall_neighbor = chosen
        nx, ny = cx + dx, cy + dy

        walls[cy][cx][wall_current] = False
        walls[ny][nx][wall_neighbor] = False
        visited.add((nx, ny))
        stack.append((nx, ny, wall_current))

    add_loops_by_difficulty(rng, walls, width, height, difficulty, mask=mask)


def _pick_direction(
    rng: random.Random,
    candidates: list[Step],
    prev_wall: int | None,
    difficulty: Difficulty,
) -> Step:
    """
    Выбирает следующее направление с учётом сложности.

    EASY: высокая вероятность продолжить в том же направлении (длинные прямые коридоры).
    MEDIUM: равномерный случайный выбор (стандартный DFS).
    HARD: высокая вероятность сменить направление (больше развилок и тупиков).

    Args:
        rng: Генератор случайных чисел
        candidates: Список доступных направлений (dx, dy, wall_current, wall_neighbor)
        prev_wall: Индекс стены последнего хода (None в начале)
        difficulty: Уровень сложности

    Returns:
        Выбранное направление
    """
    if prev_wall is None or len(candidates) == 1:
        return rng.choice(candidates)

    same = [d for d in candidates if d[2] == prev_wall]
    other = [d for d in candidates if d[2] != prev_wall]

    lvl = effective_level(difficulty)
    # L1=80% продолжить прямо (длинные коридоры)
    # L7=80% сменить направление (больше развилок и тупиков)
    straight_bias = lerp(lvl, 0.80, 0.0)
    turn_bias = lerp(lvl, 0.0, 0.80)

    if same and rng.random() < straight_bias:
        return same[0]
    if other and rng.random() < turn_bias:
        return rng.choice(other)
    return rng.choice(candidates)


def add_loops_by_difficulty(
    rng: random.Random,
    walls: Walls,
    width: int,
    height: int,
    difficulty: Difficulty,
    mask: Mask | None,
) -> None:
    """
    Добавляет петли (дополнительные проходы) после DFS для контроля сложности.

    EASY: ~6% ячеек получают лишние проходы (меньше тупиков, легче ориентироваться).
    HARD: петли не добавляются (чистое дерево, максимум тупиков).

    Args:
        rng: Генератор случайных чисел
        walls: Стены лабиринта (модифицируются на месте)
        width: Ширина сетки
        height: Высота сетки
        difficulty: Уровень сложности
        mask: Маска формы или None для прямоугольника
    """
    # L1=6% петель, L7=0% (чистое дерево без доп. проходов)
    loop_rate = max(0.0, lerp(effective_level(difficulty), 0.06, 0.0))

    if loop_rate <= 0.0:
        return

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
        x, y = rng.choice(candidates)
        dx, dy, wc, wn = rng.choice(_directions)
        nx, ny = x + dx, y + dy
        in_bounds = 0 <= nx < width and 0 <= ny < height
        in_mask = mask is None or (in_bounds and mask[ny][nx])
        if in_bounds and in_mask and walls[y][x][wc]:
            walls[y][x][wc] = False
            walls[ny][nx][wn] = False
            added += 1


def add_chaotic_shortcuts(
    rng: random.Random,
    walls: Walls,
    mask: Mask,
    width: int,
    height: int,
    difficulty: Difficulty,
) -> None:
    """
    Добавляет дополнительные локальные проходы случайными блужданиями.

    Чем выше сложность, тем больше блужданий и длиннее каждое —
    рисунок лабиринта становится более хаотичным.

    Args:
        rng: Генератор случайных чисел
        walls: Стены лабиринта (модифицируются на месте)
        mask: Маска формы
        width: Ширина сетки
        height: Высота сетки
        difficulty: Уровень сложности
    """
    inside_cells = [(x, y) for y in range(height) for x in range(width) if mask[y][x]]
    if not inside_cells:
        return

    num_walks = max(2, round(lerp(effective_level(difficulty), 6, 18)))
    walk_len_min = 4
    walk_len_max = max(walk_len_min + 1, round(lerp(effective_level(difficulty), 10, 20)))

    for _ in range(num_walks):
        x, y = rng.choice(inside_cells)
        walk_length = rng.randint(walk_len_min, walk_len_max)

        for _ in range(walk_length):
            candidates = []
            for dx, dy, wall_current, wall_neighbor in _directions:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and mask[ny][nx]:
                    candidates.append((nx, ny, wall_current, wall_neighbor))

            if not candidates:
                break

            nx, ny, wall_current, wall_neighbor = rng.choice(candidates)
            walls[y][x][wall_current] = False
            walls[ny][nx][wall_neighbor] = False
            x, y = nx, ny
