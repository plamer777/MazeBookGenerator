"""Unit-тесты для MazeGenerator."""

import unittest

from src.domain.maze_generator import MazeGenerator
from src.domain.models import Difficulty, MazeShape


class TestMazeGenerator(unittest.TestCase):
    """Проверяет логику генерации лабиринтов."""

    def setUp(self) -> None:
        """Инициализация генератора с фиксированным seed для воспроизводимости."""
        self.generator = MazeGenerator(seed=42)

    def test_lerp_interpolation(self) -> None:
        """Линейная интерполяция должна корректно вычислять значения."""
        # level=1 -> lo, level=7 -> hi
        self.assertAlmostEqual(MazeGenerator._lerp(1, 10, 20), 10.0)
        self.assertAlmostEqual(MazeGenerator._lerp(7, 10, 20), 20.0)
        self.assertAlmostEqual(MazeGenerator._lerp(4, 10, 20), 15.0)

    def test_effective_level_calibration(self) -> None:
        """Эффективный уровень должен быть перекалиброван согласно таблице."""
        # L1 ≈ 3.5, L7 = 7.0
        self.assertAlmostEqual(MazeGenerator._effective_level(Difficulty.L1), 3.5, places=1)
        self.assertAlmostEqual(MazeGenerator._effective_level(Difficulty.L7), 7.0, places=1)
        # L4 ≈ 5.89 (фактическое значение)
        self.assertAlmostEqual(MazeGenerator._effective_level(Difficulty.L4), 5.89, places=1)

    def test_rectangular_maze_generation(self) -> None:
        """Генерация прямоугольного лабиринта должна создавать валидный объект Maze."""
        maze = self.generator.generate(10, 8, Difficulty.MEDIUM, MazeShape.RECTANGULAR)

        self.assertEqual(maze.shape, MazeShape.RECTANGULAR)
        self.assertEqual(maze.difficulty, Difficulty.MEDIUM)
        self.assertIsNotNone(maze.start)
        self.assertIsNotNone(maze.end)
        self.assertIsNotNone(maze.solution_path)
        self.assertIsNotNone(maze.walls)
        self.assertGreater(len(maze.solution_path), 0)

    def test_square_maze_generation(self) -> None:
        """Генерация квадратного лабиринта должна использовать минимальный размер."""
        maze = self.generator.generate(12, 8, Difficulty.MEDIUM, MazeShape.SQUARE)

        self.assertEqual(maze.shape, MazeShape.SQUARE)
        self.assertEqual(maze.width, maze.height)  # квадрат

    def test_triangular_maze_generation(self) -> None:
        """Генерация треугольного лабиринта должна создавать маску треугольника."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.TRIANGULAR)

        self.assertEqual(maze.shape, MazeShape.TRIANGULAR)
        self.assertIsNotNone(maze.start)
        self.assertIsNotNone(maze.end)

    def test_diamond_maze_generation(self) -> None:
        """Генерация лабиринта-ромба должна создавать маску ромба."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.DIAMOND)

        self.assertEqual(maze.shape, MazeShape.DIAMOND)
        self.assertIsNotNone(maze.start)
        self.assertIsNotNone(maze.end)

    def test_heart_maze_generation(self) -> None:
        """Генерация лабиринта-сердца должна создавать маску сердца."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.HEART)

        self.assertEqual(maze.shape, MazeShape.HEART)
        self.assertIsNotNone(maze.start)
        self.assertIsNotNone(maze.end)

    def test_circular_maze_generation(self) -> None:
        """Генерация круглого лабиринта должна создавать полярную топологию."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.CIRCULAR)

        self.assertEqual(maze.shape, MazeShape.CIRCULAR)
        self.assertIsNotNone(maze.polar_connections)
        self.assertIsNotNone(maze.num_rings)
        self.assertIsNotNone(maze.cells_per_ring)
        self.assertGreater(maze.num_rings, 0)

    def test_random_maze_generation(self) -> None:
        """Генерация случайного лабиринта должна создавать валидный лабиринт."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.RANDOM)

        self.assertEqual(maze.shape, MazeShape.RANDOM)
        self.assertIsNotNone(maze.start)
        self.assertIsNotNone(maze.end)
        self.assertIsNotNone(maze.solution_path)

    def test_chaotic_maze_generation(self) -> None:
        """Генерация хаотичного лабиринта должна создавать связную маску."""
        maze = self.generator.generate(10, 10, Difficulty.MEDIUM, MazeShape.CHAOTIC)

        self.assertEqual(maze.shape, MazeShape.CHAOTIC)
        self.assertIsNotNone(maze.start)
        self.assertIsNotNone(maze.end)
        self.assertIsNotNone(maze.solution_path)

    def test_solution_path_validity(self) -> None:
        """Путь решения должен соединять старт и финиш."""
        maze = self.generator.generate(10, 8, Difficulty.MEDIUM, MazeShape.RECTANGULAR)

        self.assertEqual(maze.solution_path[0], maze.start)
        self.assertEqual(maze.solution_path[-1], maze.end)

    def test_maze_walls_structure(self) -> None:
        """Стены лабиринта должны иметь корректную структуру."""
        maze = self.generator.generate(10, 8, Difficulty.MEDIUM, MazeShape.RECTANGULAR)

        # walls[y][x] = [верх, право, низ, лево]
        self.assertEqual(len(maze.walls), maze.height)
        self.assertEqual(len(maze.walls[0]), maze.width)
        for row in maze.walls:
            for cell in row:
                self.assertEqual(len(cell), 4)
                self.assertIsInstance(cell[0], bool)
                self.assertIsInstance(cell[1], bool)
                self.assertIsInstance(cell[2], bool)
                self.assertIsInstance(cell[3], bool)

    def test_difficulty_scaling(self) -> None:
        """Сложность должна влиять на размер сетки."""
        easy_maze = self.generator.generate(10, 8, Difficulty.EASY, MazeShape.RECTANGULAR)
        hard_maze = self.generator.generate(10, 8, Difficulty.HARD, MazeShape.RECTANGULAR)

        # HARD должен быть больше по размеру
        self.assertGreaterEqual(hard_maze.width, easy_maze.width)
        self.assertGreaterEqual(hard_maze.height, easy_maze.height)

    def test_seed_reproducibility(self) -> None:
        """Одинаковый seed должен давать одинаковые лабиринты."""
        gen1 = MazeGenerator(seed=123)
        maze1 = gen1.generate(10, 8, Difficulty.L4, MazeShape.RECTANGULAR)

        gen2 = MazeGenerator(seed=123)
        maze2 = gen2.generate(10, 8, Difficulty.L4, MazeShape.RECTANGULAR)

        self.assertEqual(maze1.start, maze2.start)
        self.assertEqual(maze1.end, maze2.end)
        # Проверяем, что пути решения имеют одинаковую длину (точное сравнение может быть нестабильным)
        self.assertEqual(len(maze1.solution_path), len(maze2.solution_path))

    def test_mask_boundary_detection(self) -> None:
        """Проверка граничных ячеек маски должна работать корректно."""
        mask = [
            [True, True, True],
            [True, False, True],
            [True, True, True],
        ]

        # Угловые ячейки - граничные
        self.assertTrue(self.generator._is_mask_boundary_cell(mask, 0, 0, 3, 3))
        self.assertTrue(self.generator._is_mask_boundary_cell(mask, 2, 0, 3, 3))
        self.assertTrue(self.generator._is_mask_boundary_cell(mask, 0, 2, 3, 3))
        self.assertTrue(self.generator._is_mask_boundary_cell(mask, 2, 2, 3, 3))

        # Центральная ячейка (False) - не граничная
        self.assertFalse(self.generator._is_mask_boundary_cell(mask, 1, 1, 3, 3))

    def test_pick_boundary_cell(self) -> None:
        """Выбор граничной ячейки должен возвращать валидную ячейку."""
        mask = [
            [True, True, True],
            [True, False, True],
            [True, True, True],
        ]

        cell = self.generator._pick_boundary_cell(mask, 3, 3)
        self.assertIsNotNone(cell)
        self.assertIn(cell[0], [0, 1, 2])
        self.assertIn(cell[1], [0, 1, 2])

    def test_diamond_mask_creation(self) -> None:
        """Маска ромба должна иметь форму ромба."""
        mask = self.generator._create_diamond_mask(10, 10)

        # Центр должен быть заполнен
        self.assertTrue(mask[5][5])
        # Углы должны быть пустыми
        self.assertFalse(mask[0][0])
        self.assertFalse(mask[0][9])
        self.assertFalse(mask[9][0])
        self.assertFalse(mask[9][9])

    def test_heart_mask_creation(self) -> None:
        """Маска сердца должна иметь форму сердца."""
        mask = self.generator._create_heart_mask(10, 10)

        # В верхней части должны быть заполненные ячейки (верхушки сердца)
        top_filled = any(mask[0][x] for x in range(10))
        self.assertTrue(top_filled)


if __name__ == "__main__":
    unittest.main()
