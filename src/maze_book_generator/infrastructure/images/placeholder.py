"""Генератор изображений для обложек и иллюстраций."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from maze_book_generator.infrastructure.fonts import (
    find_dejavu_bold,
    find_dejavu_regular,
)
from maze_book_generator.utils import create_rng


class ImageGenerator:
    """Генератор изображений для обложек и иллюстраций книг."""

    def __init__(self) -> None:
        """Инициализация генератора."""
        self.cover_width = 1200
        self.cover_height = 800
        self.illustration_width = 300
        self.illustration_height = 300
        # Собственный RNG для декоративных элементов — не трогаем глобальный random
        self._rng = create_rng()

    def generate_cover(self, title: str, output_path: Path) -> Path:
        """
        Генерирует изображение обложки.

        Args:
            title: Заголовок книги
            output_path: Путь для сохранения изображения

        Returns:
            Путь к сохранённому изображению
        """
        # Создаём изображение с градиентным фоном
        img = Image.new("RGB", (self.cover_width, self.cover_height), color="#4A90E2")
        draw = ImageDraw.Draw(img)

        # Рисуем градиент
        for y in range(self.cover_height):
            color = self._get_gradient_color(y, self.cover_height)
            draw.line([(0, y), (self.cover_width, y)], fill=color)

        # Добавляем декоративные элементы
        self._draw_decorations(draw, self.cover_width, self.cover_height)

        # Добавляем текст
        # DejaVu по кандидатным путям; иначе — стандартный шрифт PIL
        bold_path = find_dejavu_bold()
        regular_path = find_dejavu_regular()
        font_large = (
            ImageFont.truetype(bold_path, 60)
            if bold_path
            else ImageFont.load_default()
        )
        font_small = (
            ImageFont.truetype(regular_path, 30)
            if regular_path
            else ImageFont.load_default()
        )

        # Центрируем текст
        text_bbox = draw.textbbox((0, 0), title, font=font_large)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (self.cover_width - text_width) // 2
        text_y = self.cover_height // 2 - 50

        draw.text((text_x, text_y), title, fill="white", font=font_large)

        # Подзаголовок
        subtitle = "Maze Book"
        text_bbox = draw.textbbox((0, 0), subtitle, font=font_small)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (self.cover_width - text_width) // 2
        text_y = self.cover_height // 2 + 30

        draw.text((text_x, text_y), subtitle, fill="white", font=font_small)

        # Сохраняем
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "PNG")
        return output_path

    def generate_illustration(self, _prompt: str, output_path: Path) -> Path:
        """
        Генерирует иллюстрацию для страницы (заглушка с мини-лабиринтом).

        Args:
            _prompt: Промпт для генерации — заглушке не нужен, параметр сохранён
                для совместимости интерфейса с провайдерами иллюстраций
            output_path: Путь для сохранения изображения

        Returns:
            Путь к сохранённому изображению
        """
        # Создаём более интересную иллюстрацию с мини-лабиринтом
        img = Image.new("RGB", (self.illustration_width, self.illustration_height), color="#FFF8DC")
        draw = ImageDraw.Draw(img)

        # Рисуем рамку
        draw.rectangle(
            [(10, 10), (self.illustration_width - 10, self.illustration_height - 10)],
            outline="#8B4513",
            width=3,
        )

        # Рисуем мини-лабиринт как иллюстрацию
        self._draw_mini_maze(draw, self.illustration_width, self.illustration_height)

        # Сохраняем
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "PNG")
        return output_path

    def _get_gradient_color(self, y: int, height: int) -> str:
        """Возвращает цвет градиента для заданной позиции Y."""
        # Градиент от синего к фиолетовому
        ratio = y / height
        r = int(74 + ratio * 50)
        g = int(144 - ratio * 50)
        b = int(226 - ratio * 30)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw_decorations(self, draw: ImageDraw.Draw, width: int, height: int) -> None:
        """Рисует декоративные элементы на обложке."""
        # Рисуем несколько кругов
        for _ in range(5):
            x = int(width * 0.1 + (width * 0.8) * (_ / 4))
            y = int(height * 0.1 + (height * 0.8) * (_ / 4))
            radius = 20 + _ * 10
            draw.ellipse(
                [(x - radius, y - radius), (x + radius, y + radius)],
                outline="white",
                width=2,
            )

    def _draw_mini_maze(self, draw: ImageDraw.Draw, width: int, height: int) -> None:
        """Рисует мини-лабиринт как иллюстрацию с более реалистичной структурой."""
        maze_size = 7
        cell_size = 35
        start_x = (width - maze_size * cell_size) // 2
        start_y = (height - maze_size * cell_size) // 2 + 10

        grid = self._mini_maze_grid(maze_size)
        self._paint_mini_cells(draw, grid, start_x, start_y, cell_size)
        self._paint_mini_endpoints(draw, start_x, start_y, cell_size, maze_size)

    def _mini_maze_grid(self, maze_size: int) -> list[list[int]]:
        """Генерирует сетку мини-лабиринта с путём, достижимым концом и лишними проходами."""
        grid = [[0 for _ in range(maze_size)] for _ in range(maze_size)]
        grid[0][0] = 1
        self._carve_mini_path(grid, maze_size)
        grid[maze_size - 1][maze_size - 1] = 1
        for _ in range(5):
            grid[self._rng.randint(0, maze_size - 1)][self._rng.randint(0, maze_size - 1)] = 1
        return grid

    def _carve_mini_path(self, grid: list[list[int]], maze_size: int) -> None:
        """Прокладывает случайный путь по сетке, отмечая проходы единицами."""
        x, y = 0, 0
        directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        for _ in range(maze_size * 2):
            self._rng.shuffle(directions)
            step = self._first_open_step(grid, x, y, directions, maze_size)
            if step is None:
                break
            x, y = x + step[0], y + step[1]
            grid[y][x] = 1

    @staticmethod
    def _first_open_step(
        grid: list[list[int]],
        x: int,
        y: int,
        directions: list[tuple[int, int]],
        maze_size: int,
    ) -> tuple[int, int] | None:
        """Возвращает первое направление в свободную ячейку или None."""
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < maze_size and 0 <= ny < maze_size and grid[ny][nx] == 0:
                return dx, dy
        return None

    @staticmethod
    def _paint_mini_cells(
        draw: ImageDraw.Draw,
        grid: list[list[int]],
        start_x: int,
        start_y: int,
        cell_size: int,
    ) -> None:
        """Закрашивает ячейки сетки: проходы светлыми, стены тёмными."""
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                cell_x = start_x + x * cell_size
                cell_y = start_y + y * cell_size
                fill, outline = ("#FFF8DC", "#DEB887") if cell == 1 else ("#8B4513", "#654321")
                draw.rectangle(
                    [(cell_x + 2, cell_y + 2), (cell_x + cell_size - 2, cell_y + cell_size - 2)],
                    fill=fill,
                    outline=outline,
                )

    @staticmethod
    def _paint_mini_endpoints(
        draw: ImageDraw.Draw,
        start_x: int,
        start_y: int,
        cell_size: int,
        maze_size: int,
    ) -> None:
        """Помечает старт зелёным и финиш красным квадратом."""
        draw.rectangle(
            [(start_x + 4, start_y + 4), (start_x + cell_size - 4, start_y + cell_size - 4)],
            fill="#32CD32",
        )
        end_x = start_x + (maze_size - 1) * cell_size
        end_y = start_y + (maze_size - 1) * cell_size
        draw.rectangle(
            [(end_x + 4, end_y + 4), (end_x + cell_size - 4, end_y + cell_size - 4)],
            fill="#DC143C",
        )
