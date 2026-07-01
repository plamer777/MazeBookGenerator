"""Модели данных для MazeBookGenerator."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Set, Tuple


class Difficulty(str, Enum):
    """Уровень сложности лабиринта (7 градаций)."""
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"
    L7 = "L7"

    # Алиасы для обратной совместимости
    EASY   = "L2"
    MEDIUM = "L4"
    HARD   = "L6"

    @property
    def level(self) -> int:
        """Числовой уровень сложности 1-7."""
        return int(self.value[1])


class DifficultyMode(str, Enum):
    """Режим распределения сложности по страницам."""
    FIXED = "FIXED"
    INCREMENTAL = "INCREMENTAL"
    RANDOM_RANGE = "RANDOM_RANGE"
    KIDS_EASY = "KIDS_EASY"
    CHALLENGE_HARD = "CHALLENGE_HARD"
    STORY_WAVE = "STORY_WAVE"


class MazeShape(str, Enum):
    """Формы лабиринтов."""
    RECTANGULAR = "RECTANGULAR"
    SQUARE = "SQUARE"
    TRIANGULAR = "TRIANGULAR"
    CIRCULAR = "CIRCULAR"
    RANDOM = "RANDOM"
    CHAOTIC = "CHAOTIC"
    DIAMOND = "DIAMOND"
    HEART = "HEART"


@dataclass
class Maze:
    """Модель лабиринта."""
    grid: list[list[int]]  # 0 - стена, 1 - проход (для обратной совместимости)
    width: int
    height: int
    start: Tuple[int, int]
    end: Tuple[int, int]
    difficulty: Difficulty
    shape: MazeShape = MazeShape.RECTANGULAR
    solution_path: list[Tuple[int, int]] | None = None
    # Стены между ячейками: walls[y][x] = [верх, право, низ, лево] (True=есть стена)
    walls: list[list[list[bool]]] | None = None
    # Полярный граф соединений: connections[(ring, sector)] = set[(ring, sector)]
    polar_connections: Dict[tuple[int, int], Set[tuple[int, int]]] | None = None
    # Количество колец в полярном лабиринте
    num_rings: int | None = None
    # Количество ячеек в каждом кольце (переменное)
    cells_per_ring: list[int] | None = None


@dataclass
class PagePrompt:
    """Задание для одной страницы книги."""
    task: str
    heroes: list[str]


@dataclass
class Theme:
    """Тема книги от AI."""
    book_title: str
    book_description: str
    page_prompts: list[PagePrompt]
    image_notes: str | None = None
    image_keywords: list[list[str]] = None  # type: ignore[assignment]


@dataclass
class BookPage:
    """Страница книги с лабиринтом."""
    maze: Maze
    title: str
    prompt: str
    page_number: int
    image_path: str | None = None
    is_solution: bool = False


@dataclass
class Book:
    """Модель книги."""
    id: int
    theme: Theme
    pages: list[BookPage]
    output_dir: str
