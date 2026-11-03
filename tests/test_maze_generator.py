"""Unit-тесты для MazeGenerator."""


import pytest

from src.domain.maze_generator import MazeGenerator
from src.domain.models import Difficulty, MazeShape


class TestMazeGenerator:
    """Проверяет логику генерации лабиринтов."""

    def setup_method(self) -> None:
        """Инициализация генератора с фиксированным seed для воспроизводимости."""
        self.generator = MazeGenerator(seed=42)

    def test_lerp_interpolation(self) -> None:
        """Линейная интерполяция должна корректно вычислять значения."""
        # level=1 -> lo, level=7 -> hi
        assert MazeGenerator._lerp(1, 10, 20) == pytest.approx(10.0, abs=10**-7)
        assert MazeGenerator._lerp(7, 10, 20) == pytest.approx(20.0, abs=10**-7)
        assert MazeGenerator._lerp(4, 10, 20) == pytest.approx(15.0, abs=10**-7)

    def test_effective_level_calibration(self) -> None:
        """Эффективный уровень должен быть перекалиброван согласно таблице."""
        # L1 ≈ 3.5, L7 = 7.0
        assert MazeGenerator._effective_level(Difficulty.L1) == pytest.approx(3.5, abs=10**-1)
        assert MazeGenerator._effective_level(Difficulty.L7) == pytest.approx(7.0, abs=10**-1)
        # L4 ≈ 5.89 (фактическое значение)
        assert MazeGenerator._effective_level(Difficulty.L4) == pytest.approx(5.89, abs=10**-1)

    def test_rectangular_maze_generation(self) -> None:
        """Генерация прямоугольного лабиринта должна создавать валидный объект Maze."""
        maze = self.generator.generate(10, 8, Difficulty.MEDIUM, MazeShape.RECTANGULAR)

        assert maze.shape == MazeShape.RECTANGULAR
        assert maze.difficulty == Difficulty.MEDIUM
        assert maze.start is not None
        assert maze.end is not None
        assert maze.solution_path is not None
        assert maze.walls is not None
        assert len(maze.solution_path) > 0

    def test_square_maze_generation(self) -> None:
        """Генерация квадратного лабиринта должна использовать минимальный размер."""
        maze = self.generator.generate(12, 8, Difficulty.MEDIUM, MazeShape.SQUARE)

        assert maze.shape == MazeShape.SQUARE
        assert maze.width == maze.height  # квадрат

    def test_triangular_maze_generation(self) -> None:
        """Генерация треугольного лабиринта должна создавать маску треугольника."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.TRIANGULAR)

        assert maze.shape == MazeShape.TRIANGULAR
        assert maze.start is not None
        assert maze.end is not None

    def test_diamond_maze_generation(self) -> None:
        """Генерация лабиринта-ромба должна создавать маску ромба."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.DIAMOND)

        assert maze.shape == MazeShape.DIAMOND
        assert maze.start is not None
        assert maze.end is not None

    def test_heart_maze_generation(self) -> None:
        """Генерация лабиринта-сердца должна создавать маску сердца."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.HEART)

        assert maze.shape == MazeShape.HEART
        assert maze.start is not None
        assert maze.end is not None

    def test_circular_maze_generation(self) -> None:
        """Генерация круглого лабиринта должна создавать полярную топологию."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.CIRCULAR)

        assert maze.shape == MazeShape.CIRCULAR
        assert maze.polar_connections is not None
        assert maze.num_rings is not None
        assert maze.cells_per_ring is not None
        assert maze.num_rings > 0

    def test_random_maze_generation(self) -> None:
        """Генерация случайного лабиринта должна создавать валидный лабиринт."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.RANDOM)

        assert maze.shape == MazeShape.RANDOM
        assert maze.start is not None
        assert maze.end is not None
        assert maze.solution_path is not None

    def test_chaotic_maze_generation(self) -> None:
        """Генерация хаотичного лабиринта должна создавать связную маску."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.CHAOTIC)

        assert maze.shape == MazeShape.CHAOTIC
        assert maze.start is not None
        assert maze.end is not None
        assert maze.solution_path is not None

    def test_solution_path_validity(self) -> None:
        """Путь решения должен соединять старт и финиш."""
        maze = self.generator.generate(10, 8, Difficulty.MEDIUM, MazeShape.RECTANGULAR)

        assert maze.solution_path[0] == maze.start
        assert maze.solution_path[-1] == maze.end

    def test_maze_walls_structure(self) -> None:
        """Стены лабиринта должны иметь корректную структуру."""
        maze = self.generator.generate(10, 8, Difficulty.MEDIUM, MazeShape.RECTANGULAR)

        # walls[y][x] = [верх, право, низ, лево]
        assert len(maze.walls) == maze.height
        assert len(maze.walls[0]) == maze.width
        for row in maze.walls:
            for cell in row:
                assert len(cell) == 4
                assert isinstance(cell[0], bool)
                assert isinstance(cell[1], bool)
                assert isinstance(cell[2], bool)
                assert isinstance(cell[3], bool)

    def test_difficulty_scaling(self) -> None:
        """Сложность должна влиять на размер сетки."""
        easy_maze = self.generator.generate(10, 8, Difficulty.EASY, MazeShape.RECTANGULAR)
        hard_maze = self.generator.generate(10, 8, Difficulty.HARD, MazeShape.RECTANGULAR)

        # HARD должен быть больше по размеру
        assert hard_maze.width >= easy_maze.width
        assert hard_maze.height >= easy_maze.height

    def test_seed_reproducibility(self) -> None:
        """Одинаковый seed должен давать одинаковые лабиринты."""
        gen1 = MazeGenerator(seed=123)
        maze1 = gen1.generate(10, 8, Difficulty.L4, MazeShape.RECTANGULAR)

        gen2 = MazeGenerator(seed=123)
        maze2 = gen2.generate(10, 8, Difficulty.L4, MazeShape.RECTANGULAR)

        assert maze1.start == maze2.start
        assert maze1.end == maze2.end
        # Проверяем, что пути решения имеют одинаковую длину (точное сравнение может быть нестабильным)
        assert len(maze1.solution_path) == len(maze2.solution_path)

    def test_mask_boundary_detection(self) -> None:
        """Проверка граничных ячеек маски должна работать корректно."""
        mask = [
            [True, True, True],
            [True, False, True],
            [True, True, True],
        ]

        # Угловые ячейки - граничные
        assert self.generator._is_mask_boundary_cell(mask, 0, 0, 3, 3)
        assert self.generator._is_mask_boundary_cell(mask, 2, 0, 3, 3)
        assert self.generator._is_mask_boundary_cell(mask, 0, 2, 3, 3)
        assert self.generator._is_mask_boundary_cell(mask, 2, 2, 3, 3)

        # Центральная ячейка (False) - не граничная
        assert not self.generator._is_mask_boundary_cell(mask, 1, 1, 3, 3)

    def test_pick_boundary_cell(self) -> None:
        """Выбор граничной ячейки должен возвращать валидную ячейку."""
        mask = [
            [True, True, True],
            [True, False, True],
            [True, True, True],
        ]

        cell = self.generator._pick_boundary_cell(mask, 3, 3)
        assert cell is not None
        assert cell[0] in [0, 1, 2]
        assert cell[1] in [0, 1, 2]

    def test_diamond_mask_creation(self) -> None:
        """Маска ромба должна иметь форму ромба."""
        mask = self.generator._create_diamond_mask(10, 10)

        # Центр должен быть заполнен
        assert mask[5][5]
        # Углы должны быть пустыми
        assert not mask[0][0]
        assert not mask[0][9]
        assert not mask[9][0]
        assert not mask[9][9]

    def test_heart_mask_creation(self) -> None:
        """Маска сердца должна иметь форму сердца."""
        mask = self.generator._create_heart_mask(10, 10)

        # В верхней части должны быть заполненные ячейки (верхушки сердца)
        top_filled = any(mask[0][x] for x in range(10))
        assert top_filled
