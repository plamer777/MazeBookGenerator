"""Генератор изображений для обложек и иллюстраций."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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
        try:
            # Пытаемся использовать системный шрифт
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except OSError:
            # Fallback на стандартный шрифт
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

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

    def _draw_pattern(self, draw: ImageDraw.Draw, width: int, height: int) -> None:
        """Рисует простой узор для иллюстрации."""
        # Рисуем сетку
        step = 30
        for x in range(20, width - 20, step):
            draw.line([(x, 20), (x, height - 20)], fill="#DEB887", width=1)
        for y in range(20, height - 20, step):
            draw.line([(20, y), (width - 20, y)], fill="#DEB887", width=1)

    def _draw_mini_maze(self, draw: ImageDraw.Draw, width: int, height: int) -> None:
        """Рисует мини-лабиринт как иллюстрацию с более реалистичной структурой."""

        # Размер мини-лабиринта
        maze_size = 7
        cell_size = 35
        start_x = (width - maze_size * cell_size) // 2
        start_y = (height - maze_size * cell_size) // 2 + 10

        # Создаём сетку с более структурированным подходом
        grid = [[0 for _ in range(maze_size)] for _ in range(maze_size)]

        # Генерируем простой путь от старта к концу
        x, y = 0, 0
        grid[y][x] = 1

        # Простой путь
        directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        for _ in range(maze_size * 2):
            self._rng.shuffle(directions)
            moved = False
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if 0 <= nx < maze_size and 0 <= ny < maze_size and grid[ny][nx] == 0:
                    x, y = nx, ny
                    grid[y][x] = 1
                    moved = True
                    break
            if not moved:
                break

        # Убеждаемся что конец достижим
        grid[maze_size - 1][maze_size - 1] = 1

        # Добавляем несколько случайных проходов
        for _ in range(5):
            rx = self._rng.randint(0, maze_size - 1)
            ry = self._rng.randint(0, maze_size - 1)
            grid[ry][rx] = 1

        # Рисуем сетку
        for y in range(maze_size):
            for x in range(maze_size):
                cell_x = start_x + x * cell_size
                cell_y = start_y + y * cell_size

                if grid[y][x] == 1:
                    # Проход
                    draw.rectangle(
                        [(cell_x + 2, cell_y + 2), (cell_x + cell_size - 2, cell_y + cell_size - 2)],
                        fill="#FFF8DC",
                        outline="#DEB887",
                    )
                else:
                    # Стена
                    draw.rectangle(
                        [(cell_x + 2, cell_y + 2), (cell_x + cell_size - 2, cell_y + cell_size - 2)],
                        fill="#8B4513",
                        outline="#654321",
                    )

        # Рисуем старт (зелёный)
        draw.rectangle(
            [(start_x + 4, start_y + 4), (start_x + cell_size - 4, start_y + cell_size - 4)],
            fill="#32CD32",
        )

        # Рисуем конец (красный)
        end_x = start_x + (maze_size - 1) * cell_size
        end_y = start_y + (maze_size - 1) * cell_size
        draw.rectangle(
            [(end_x + 4, end_y + 4), (end_x + cell_size - 4, end_y + cell_size - 4)],
            fill="#DC143C",
        )
