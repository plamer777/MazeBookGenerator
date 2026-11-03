"""Фасад генератора лабиринтов: масштабирование сетки и диспетчеризация по формам."""

from maze_book_generator.domain.maze import grid, polar
from maze_book_generator.domain.maze.difficulty import effective_level, lerp
from maze_book_generator.domain.models import Difficulty, Maze, MazeShape
from maze_book_generator.settings import MAZE_GRID_SCALE_MAX, MAZE_GRID_SCALE_MIN
from maze_book_generator.utils import create_rng


class MazeGenerator:
    """Генератор лабиринтов на основе DFS с настройкой сложности."""

    def __init__(self, seed: int | None = None) -> None:
        """Инициализация генератора с опциональным seed для воспроизводимости."""
        # Собственный RNG: seed делает генерацию воспроизводимой,
        # при этом не затрагивается глобальное состояние random.
        self._rng = create_rng(seed)

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
            return polar.generate_maze(self._rng, width, height, difficulty)

        # Используем перекалиброванный уровень: минимум сложнее, рост плавный.
        scale = lerp(effective_level(difficulty), MAZE_GRID_SCALE_MIN, MAZE_GRID_SCALE_MAX)
        scaled_w = max(6, round(width * scale))
        scaled_h = max(5, round(height * scale))

        builders = {
            MazeShape.SQUARE: grid.build_square,
            MazeShape.TRIANGULAR: grid.build_triangular,
            MazeShape.DIAMOND: grid.build_diamond,
            MazeShape.HEART: grid.build_heart,
            MazeShape.RANDOM: grid.build_random,
            MazeShape.CHAOTIC: grid.build_chaotic,
        }
        builder = builders.get(shape, grid.build_rectangular)
        return builder(self._rng, scaled_w, scaled_h, difficulty)
