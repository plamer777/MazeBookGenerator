"""PDF рендерер для генерации книг с лабиринтами."""

import io
import math
import random
from pathlib import Path

from PIL import Image
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from src.domain.models import Book, BookPage, Maze, MazeShape
from src.domain.polar_topology_service import PolarTopologyService
from src.settings import WATERMARK_ALPHA, settings


class PDFRenderer:
    """Рендерер PDF документов с лабиринтами."""

    def __init__(self) -> None:
        """Инициализация рендерера с настройками из settings."""
        self.page_width = settings.PDF_PAGE_WIDTH * mm
        self.page_height = settings.PDF_PAGE_HEIGHT * mm
        self.margin = settings.PDF_MARGIN * mm
        self.cell_size = settings.DEFAULT_CELL_SIZE * mm

    def render_book(self, book: Book, output_path: Path) -> None:
        """
        Рендерит полную книгу в PDF файл.

        Args:
            book: Объект книги с лабиринтами
            output_path: Путь для сохранения PDF
        """
        c = canvas.Canvas(str(output_path), pagesize=(self.page_width, self.page_height))

        # Обложка
        self._render_cover(c, book)
        c.showPage()

        # Страницы с лабиринтами
        for page in book.pages:
            if page.prompt == "Answer Key":
                self._render_solution_page(c, page, book.theme.book_title)
            else:
                self._render_maze_page(c, page, book.theme.book_title)
            c.showPage()

        c.save()

    def _cover_palette(self, seed: str) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
        """
        Генерирует детерминированную палитру из 3 цветов по строке-ключу.

        Возвращает (bg_top, bg_bottom, accent) — цвета фона и акцента.

        Args:
            seed: Строка-источник (например, название книги)

        Returns:
            Кортеж из трёх RGB-цветов (0..1)
        """
        palettes = [
            ((0.10, 0.15, 0.35), (0.20, 0.30, 0.55), (0.95, 0.80, 0.25)),  # синий + золото
            ((0.12, 0.30, 0.20), (0.22, 0.45, 0.32), (0.90, 0.75, 0.20)),  # зелёный + золото
            ((0.35, 0.10, 0.15), (0.55, 0.20, 0.25), (0.95, 0.90, 0.60)),  # бордо + кремовый
            ((0.15, 0.25, 0.40), (0.30, 0.45, 0.60), (1.00, 0.60, 0.20)),  # стальной + оранжевый
            ((0.25, 0.10, 0.40), (0.40, 0.20, 0.55), (0.85, 0.90, 0.95)),  # фиолетовый + серебро
        ]
        idx = sum(ord(ch) for ch in seed) % len(palettes)
        return palettes[idx]

    def _render_cover(self, c: canvas.Canvas, book: Book) -> None:
        """
        Рендерит обложку книги.

        Структура (сверху вниз):
        - Цветной фон (двухцветный вертикальный градиент через полосы)
        - Паттерн-полоса из лабиринтных ячеек вверху и внизу
        - Рамка-меандр по периметру
        - Название книги с тенью по центру
        - Подзаголовок «Maze Book»

        Args:
            c: Canvas для рисования
            book: Объект книги
        """
        title = book.theme.book_title
        bg_top, bg_bottom, accent = self._cover_palette(title)

        # --- Фон: вертикальный псевдо-градиент через горизонтальные полосы ---
        num_strips = 60
        strip_h = self.page_height / num_strips
        for i in range(num_strips):
            t = i / num_strips
            r = bg_top[0] + (bg_bottom[0] - bg_top[0]) * t
            g = bg_top[1] + (bg_bottom[1] - bg_top[1]) * t
            b = bg_top[2] + (bg_bottom[2] - bg_top[2]) * t
            c.setFillColorRGB(r, g, b)
            c.rect(0, self.page_height - (i + 1) * strip_h, self.page_width, strip_h + 0.5, fill=1, stroke=0)

        # --- Лабиринтный паттерн: полосы сверху и снизу ---
        band_h = 28 * mm
        cell = 7 * mm
        self._render_maze_band(c, y_bottom=self.page_height - band_h, band_h=band_h, cell=cell, accent=accent)
        self._render_maze_band(c, y_bottom=0, band_h=band_h, cell=cell, accent=accent)

        # --- Рамка-меандр ---
        self._render_meander_border(c, accent)

        # --- Блок названия по центру страницы ---
        center_y = self.page_height / 2
        box_h = 55 * mm
        box_margin = 22 * mm
        # Полупрозрачная плашка под текстом
        c.saveState()
        c.setFillColorRGB(0, 0, 0)
        c.setFillAlpha(0.45)
        c.rect(box_margin, center_y - box_h / 2, self.page_width - 2 * box_margin, box_h, fill=1, stroke=0)
        c.restoreState()

        # Тонкие линии-акценты над и под плашкой
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(1.5)
        c.line(box_margin, center_y + box_h / 2, self.page_width - box_margin, center_y + box_h / 2)
        c.line(box_margin, center_y - box_h / 2, self.page_width - box_margin, center_y - box_h / 2)

        # Название (тень + основной текст)
        font_size = 34
        c.setFont("Helvetica-Bold", font_size)
        tw = c.stringWidth(title, "Helvetica-Bold", font_size)
        tx = (self.page_width - tw) / 2
        ty = center_y + 6 * mm
        c.saveState()
        c.setFillColorRGB(0, 0, 0)
        c.setFillAlpha(0.5)
        c.drawString(tx + 1.2, ty - 1.2, title)
        c.restoreState()
        c.setFillColorRGB(*accent)
        c.drawString(tx, ty, title)

        # Подзаголовок
        subtitle = "Maze Book"
        c.setFont("Helvetica", 16)
        sw = c.stringWidth(subtitle, "Helvetica", 16)
        c.saveState()
        c.setFillColorRGB(1, 1, 1)
        c.setFillAlpha(0.80)
        c.drawString((self.page_width - sw) / 2, center_y - 10 * mm, subtitle)
        c.restoreState()

        # Декоративные уголки
        self._render_corner_ornaments(c, accent)

    def _render_maze_band(
        self,
        c: canvas.Canvas,
        y_bottom: float,
        band_h: float,
        cell: float,
        accent: tuple[float, float, float],
    ) -> None:
        """
        Рисует горизонтальную полосу с паттерном из лабиринтных ячеек.

        Каждая ячейка случайно имеет 0–3 стены — создаётся визуальный
        лабиринтный узор поверх фона.

        Args:
            c: Canvas
            y_bottom: Нижняя граница полосы
            band_h: Высота полосы
            cell: Размер ячейки
            accent: RGB-цвет линий
        """
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(1.0)
        cols = int(self.page_width / cell) + 1
        rows = int(band_h / cell) + 1
        rng = random.Random(int(y_bottom + band_h * 7))
        for row in range(rows):
            for col in range(cols):
                x0 = col * cell
                y0 = y_bottom + row * cell
                walls = [rng.random() < 0.55 for _ in range(4)]  # верх, право, низ, лево
                if walls[0]:
                    c.line(x0, y0 + cell, x0 + cell, y0 + cell)
                if walls[1]:
                    c.line(x0 + cell, y0, x0 + cell, y0 + cell)
                if walls[2]:
                    c.line(x0, y0, x0 + cell, y0)
                if walls[3]:
                    c.line(x0, y0, x0, y0 + cell)

    def _render_meander_border(
        self,
        c: canvas.Canvas,
        accent: tuple[float, float, float],
    ) -> None:
        """
        Рисует двойную рамку-меандр по периметру страницы.

        Внешняя рамка — сплошная толстая линия.
        Внутренняя — меандровый орнамент с прямоугольными зубцами.

        Args:
            c: Canvas
            accent: RGB-цвет рамки
        """
        margin = 12 * mm
        inner = 18 * mm
        step = 8 * mm

        # Внешняя рамка
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(2.5)
        c.rect(margin, margin, self.page_width - 2 * margin, self.page_height - 2 * margin, fill=0, stroke=1)

        # Внутренняя меандровая рамка
        c.setLineWidth(1.2)
        path = c.beginPath()
        w = self.page_width
        h = self.page_height
        tooth = step
        depth = 4 * mm

        def meander_side(
            pts: list[tuple[float, float]],
            x0: float, y0: float,
            x1: float, y1: float,
            nx: float, ny: float,
        ) -> None:
            """Добавляет точки меандровой стороны к pts."""
            length = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
            dx = (x1 - x0) / length
            dy = (y1 - y0) / length
            pos = 0.0
            state = False
            while pos < length:
                nxt = min(pos + tooth, length)
                cx_end = x0 + dx * nxt + (depth * nx if state else 0)
                cy_end = y0 + dy * nxt + (depth * ny if state else 0)
                pts.append((cx_end, cy_end))
                if nxt < length:
                    pts.append((x0 + dx * nxt + (depth * nx if not state else 0),
                                y0 + dy * nxt + (depth * ny if not state else 0)))
                state = not state
                pos = nxt

        pts: list[tuple[float, float]] = [(inner, inner)]
        meander_side(pts, inner, inner, w - inner, inner, 0, 1)
        meander_side(pts, w - inner, inner, w - inner, h - inner, -1, 0)
        meander_side(pts, w - inner, h - inner, inner, h - inner, 0, -1)
        meander_side(pts, inner, h - inner, inner, inner, 1, 0)

        path.moveTo(*pts[0])
        for px, py in pts[1:]:
            path.lineTo(px, py)
        path.close()
        c.drawPath(path, stroke=1, fill=0)

    def _render_corner_ornaments(
        self,
        c: canvas.Canvas,
        accent: tuple[float, float, float],
    ) -> None:
        """
        Рисует декоративные уголки — квадратные спирали в каждом углу.

        Args:
            c: Canvas
            accent: RGB-цвет орнамента
        """
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(1.0)
        size = 14 * mm
        margin = 14 * mm
        corners = [
            (margin, self.page_height - margin, 1, -1),
            (self.page_width - margin, self.page_height - margin, -1, -1),
            (margin, margin, 1, 1),
            (self.page_width - margin, margin, -1, 1),
        ]
        for cx0, cy0, sx, sy in corners:
            step_px = size / 5
            for i in range(4):
                r = size - i * step_px
                if r <= 0:
                    break
                c.rect(cx0 - r * sx / 2, cy0 - r * sy / 2, r * sx, r * sy, fill=0, stroke=1)

    def _render_maze_border(self, c: canvas.Canvas) -> None:
        """
        Рисует рамку с рандомными изломами в стиле лабиринта (для страниц с лабиринтами).

        Args:
            c: Canvas для рисования
        """
        border_margin = 20 * mm
        min_indent = 10 * mm
        max_indent = 20 * mm

        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(2.0)

        points = []
        points.extend(self._generate_border_side(
            start_x=border_margin,
            start_y=self.page_height - border_margin,
            end_x=self.page_width - border_margin,
            end_y=self.page_height - border_margin,
            is_horizontal=True, direction=1, indent_direction=-1,
            min_indent=min_indent, max_indent=max_indent,
        ))
        points.extend(self._generate_border_side(
            start_x=self.page_width - border_margin,
            start_y=self.page_height - border_margin,
            end_x=self.page_width - border_margin,
            end_y=border_margin,
            is_horizontal=False, direction=-1, indent_direction=-1,
            min_indent=min_indent, max_indent=max_indent,
        ))
        points.extend(self._generate_border_side(
            start_x=self.page_width - border_margin,
            start_y=border_margin,
            end_x=border_margin,
            end_y=border_margin,
            is_horizontal=True, direction=-1, indent_direction=1,
            min_indent=min_indent, max_indent=max_indent,
        ))
        points.extend(self._generate_border_side(
            start_x=border_margin,
            start_y=border_margin,
            end_x=border_margin,
            end_y=self.page_height - border_margin,
            is_horizontal=False, direction=1, indent_direction=1,
            min_indent=min_indent, max_indent=max_indent,
        ))
        points.append(points[0])

        path = c.beginPath()
        path.moveTo(points[0][0], points[0][1])
        for x, y in points[1:]:
            path.lineTo(x, y)
        c.drawPath(path, stroke=1, fill=0)

    def _generate_border_side(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        is_horizontal: bool,
        direction: int,
        indent_direction: int,
        min_indent: float,
        max_indent: float,
    ) -> list[tuple[float, float]]:
        """
        Генерирует точки для одной стороны рамки с изломами.

        Args:
            start_x: Начальная координата X
            start_y: Начальная координата Y
            end_x: Конечная координата X
            end_y: Конечная координата Y
            is_horizontal: True если сторона горизонтальная
            direction: Направление движения (1 или -1)
            indent_direction: Направление излома (1 или -1)
            min_indent: Минимальный излом
            max_indent: Максимальный излом

        Returns:
            Список точек (x, y)
        """
        points = [(start_x, start_y)]

        if is_horizontal:
            current = start_x
            limit = end_x
        else:
            current = start_y
            limit = end_y

        while (direction == 1 and current < limit) or (direction == -1 and current > limit):
            step = random.randint(10, 30) * mm
            current = min(current + step * direction, limit) if direction == 1 else max(current + step * direction, limit)

            indent = random.randint(0, 1) * random.randint(int(min_indent / mm), int(max_indent / mm)) * mm
            if is_horizontal:
                other = start_y + indent * indent_direction
                points.append((current, other))
            else:
                other = start_x + indent * indent_direction
                points.append((other, current))

        return points

    def _render_maze_page(self, c: canvas.Canvas, page: BookPage, book_title: str = "") -> None:
        """
        Рендерит страницу с лабиринтом в детском стиле.

        Структура:
        - Светлый цветной фон
        - Заокруглённая рамка в цвете палитры
        - Декоративные символы в углах
        - Цветная плашка-заголовок сверху
        - Лабиринт максимального размера с динамическим cell_size

        Args:
            c: Canvas для рисования
            page: Объект страницы
        """
        _, _, accent = self._cover_palette(book_title or page.title)

        # --- Фон ---
        bg = (0.97, 0.97, 1.0)
        c.setFillColorRGB(*bg)
        c.rect(0, 0, self.page_width, self.page_height, fill=1, stroke=0)

        # --- Заокруглённая рамка ---
        frame_m = 8 * mm
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(2.5)
        c.roundRect(frame_m, frame_m,
                    self.page_width - 2 * frame_m,
                    self.page_height - 2 * frame_m,
                    radius=6 * mm, fill=0, stroke=1)

        # --- Декоративные символы в углах ---
        self._render_page_corner_deco(c, accent, page.page_number)

        # --- Плашка заголовка ---
        header_h = 22 * mm
        header_y = self.page_height - frame_m - header_h
        c.setFillColorRGB(*accent)
        c.roundRect(frame_m, header_y,
                    self.page_width - 2 * frame_m, header_h,
                    radius=4 * mm, fill=1, stroke=0)

        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 18)
        tw = c.stringWidth(page.title, "Helvetica-Bold", 18)
        c.drawString((self.page_width - tw) / 2, header_y + 7 * mm, page.title)

        # Подсказка под плашкой
        prompt_y = header_y - 8 * mm
        c.setFillColorRGB(*accent)
        c.setFont("Helvetica", 11)
        pw = c.stringWidth(page.prompt, "Helvetica", 11)
        c.drawString((self.page_width - pw) / 2, prompt_y, page.prompt)

        # --- Лабиринт максимального размера ---
        # Верхняя граница строго под подсказкой (с зазором 5mm)
        deco_margin = 20 * mm
        maze_top = prompt_y - 5 * mm
        maze_area_x = frame_m + deco_margin
        maze_area_y = frame_m + deco_margin
        maze_area_w = self.page_width - 2 * (frame_m + deco_margin)
        maze_area_h = maze_top - maze_area_y

        # --- Водяной знак-иллюстрация под лабиринтом ---
        print(f'Image path before rendering watermark: {page.image_path}')
        if page.image_path:
            self._render_watermark_image(c, page.image_path, maze_area_x, maze_area_y, maze_area_w, maze_area_h)

        self._render_maze_fitted(c, page.maze, maze_area_x, maze_area_y, maze_area_w, maze_area_h)

        # --- Номер страницы ---
        c.setFillColorRGB(*accent)
        c.setFont("Helvetica", 9)
        c.drawRightString(self.page_width - frame_m - 4 * mm, frame_m + 3 * mm, f"#{page.page_number}")

    def _render_solution_page(self, c: canvas.Canvas, page: BookPage, book_title: str = "") -> None:
        """
        Рендерит страницу с ответом в том же детском стиле.

        Args:
            c: Canvas для рисования
            page: Объект страницы
        """
        _, _, accent = self._cover_palette(book_title or page.title)

        bg = (0.97, 0.97, 1.0)
        c.setFillColorRGB(*bg)
        c.rect(0, 0, self.page_width, self.page_height, fill=1, stroke=0)

        frame_m = 8 * mm
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(2.5)
        c.roundRect(frame_m, frame_m,
                    self.page_width - 2 * frame_m,
                    self.page_height - 2 * frame_m,
                    radius=6 * mm, fill=0, stroke=1)

        self._render_page_corner_deco(c, accent, page.page_number)

        header_h = 22 * mm
        header_y = self.page_height - frame_m - header_h
        c.setFillColorRGB(*accent)
        c.roundRect(frame_m, header_y,
                    self.page_width - 2 * frame_m, header_h,
                    radius=4 * mm, fill=1, stroke=0)

        sol_title = f"{page.title} — Answer"
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 18)
        tw = c.stringWidth(sol_title, "Helvetica-Bold", 18)
        c.drawString((self.page_width - tw) / 2, header_y + 7 * mm, sol_title)

        deco_margin = 20 * mm
        maze_top = header_y - 5 * mm
        maze_area_x = frame_m + deco_margin
        maze_area_y = frame_m + deco_margin
        maze_area_w = self.page_width - 2 * (frame_m + deco_margin)
        maze_area_h = maze_top - maze_area_y

        if page.image_path:
            self._render_watermark_image(c, page.image_path, maze_area_x, maze_area_y, maze_area_w, maze_area_h)

        self._render_maze_fitted(c, page.maze, maze_area_x, maze_area_y, maze_area_w, maze_area_h, show_solution=True)

        c.setFillColorRGB(*accent)
        c.setFont("Helvetica", 9)
        c.drawRightString(self.page_width - frame_m - 4 * mm, frame_m + 3 * mm, f"#{page.page_number}")

    def _render_watermark_image(
        self,
        c: canvas.Canvas,
        image_path: str,
        area_x: float,
        area_y: float,
        area_w: float,
        area_h: float,
        alpha: float = WATERMARK_ALPHA,
    ) -> None:
        """
        Накладывает иллюстрацию как полупрозрачный водяной знак в центр области лабиринта.

        Изображение масштабируется с сохранением пропорций и центрируется.
        Alpha-канал применяется через Pillow — не требует удаления фона.

        Args:
            c: Canvas для рисования
            image_path: Путь к исходному PNG-файлу
            area_x: Левая граница области X
            area_y: Нижняя граница области Y
            area_w: Ширина области
            area_h: Высота области
            alpha: Прозрачность (0.0 — невидимо, 1.0 — непрозрачно)
        """
        try:
            img = Image.open(image_path).convert("RGBA")

            r, g, b, a = img.split()
            a = a.point(lambda v: int(v * alpha))
            img = Image.merge("RGBA", (r, g, b, a))

            img_ratio = img.width / img.height
            area_ratio = area_w / area_h

            if img_ratio > area_ratio:
                draw_w = area_w
                draw_h = area_w / img_ratio
            else:
                draw_h = area_h
                draw_w = area_h * img_ratio

            draw_x = area_x + (area_w - draw_w) / 2
            draw_y = area_y + (area_h - draw_h) / 2

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            c.drawImage(
                ImageReader(buf),
                draw_x, draw_y,
                width=draw_w, height=draw_h,
                mask="auto",
                preserveAspectRatio=True,
            )
        except Exception as e:
            print(f'Failed to render watermark image: {e}'[:200])

    def _render_maze_fitted(
        self,
        c: canvas.Canvas,
        maze: Maze,
        area_x: float,
        area_y: float,
        area_w: float,
        area_h: float,
        show_solution: bool = False,
    ) -> None:
        """
        Рендерит лабиринт, масштабируя cell_size так, чтобы он занял всю доступную область.

        Вычисляет максимальный cell_size при котором лабиринт помещается в (area_w × area_h),
        затем центрирует его внутри области.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            area_x: Левая граница области X
            area_y: Нижняя граница области Y
            area_w: Ширина доступной области
            area_h: Высота доступной области
            show_solution: Показывать ли путь решения
        """
        orig_cell = self.cell_size

        if maze.shape == MazeShape.CIRCULAR:
            # Полярный лабиринт — круг, диаметр = min(area_w, area_h)
            diameter = min(area_w, area_h)
            offset_x = area_x + (area_w - diameter) / 2
            offset_y = area_y + (area_h - diameter) / 2
            self.cell_size = diameter / max(maze.width, maze.height)
            self._render_polar_maze_at(c, maze, offset_x, offset_y, diameter, show_solution)
        else:
            cell_w = area_w / maze.width
            cell_h = area_h / maze.height
            fit_cell = min(cell_w, cell_h)
            maze_w_px = maze.width * fit_cell
            maze_h_px = maze.height * fit_cell
            offset_x = area_x + (area_w - maze_w_px) / 2
            offset_y = area_y + (area_h - maze_h_px) / 2
            self.cell_size = fit_cell
            self._render_maze_at(c, maze, offset_x, offset_y, show_solution)

        self.cell_size = orig_cell

    def _render_maze_at(
        self,
        c: canvas.Canvas,
        maze: Maze,
        start_x: float,
        start_y: float,
        show_solution: bool = False,
    ) -> None:
        """
        Рендерит лабиринт с явными координатами левого нижнего угла.

        Использует self.cell_size (должен быть установлен перед вызовом).

        Args:
            c: Canvas
            maze: Объект лабиринта
            start_x: X левого нижнего угла
            start_y: Y левого нижнего угла
            show_solution: Показывать ли решение
        """
        if maze.shape in (
            MazeShape.TRIANGULAR,
            MazeShape.RANDOM,
            MazeShape.CHAOTIC,
            MazeShape.DIAMOND,
            MazeShape.HEART,
        ):
            mask = [[bool(maze.grid[y][x]) for x in range(maze.width)] for y in range(maze.height)]
        else:
            mask = None

        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1.2)

        if maze.walls:
            for y in range(maze.height):
                for x in range(maze.width):
                    if mask and not mask[y][x]:
                        continue
                    cell_x = start_x + x * self.cell_size
                    cell_y = start_y + (maze.height - 1 - y) * self.cell_size
                    walls = maze.walls[y][x]
                    if walls[0]:
                        c.line(cell_x, cell_y + self.cell_size, cell_x + self.cell_size, cell_y + self.cell_size)
                    if walls[1]:
                        c.line(cell_x + self.cell_size, cell_y, cell_x + self.cell_size, cell_y + self.cell_size)
                    if walls[2]:
                        c.line(cell_x, cell_y, cell_x + self.cell_size, cell_y)
                    if walls[3]:
                        c.line(cell_x, cell_y, cell_x, cell_y + self.cell_size)

        self._render_start_end(c, maze, start_x, start_y)

        if show_solution and maze.solution_path:
            c.setStrokeColorRGB(1, 0, 0)
            c.setLineWidth(2.0)
            for i in range(len(maze.solution_path) - 1):
                x1, y1 = maze.solution_path[i]
                x2, y2 = maze.solution_path[i + 1]
                sx1 = start_x + x1 * self.cell_size + self.cell_size / 2
                sy1 = start_y + (maze.height - 1 - y1) * self.cell_size + self.cell_size / 2
                sx2 = start_x + x2 * self.cell_size + self.cell_size / 2
                sy2 = start_y + (maze.height - 1 - y2) * self.cell_size + self.cell_size / 2
                c.line(sx1, sy1, sx2, sy2)

    def _render_polar_maze_at(
        self,
        c: canvas.Canvas,
        maze: Maze,
        offset_x: float,
        offset_y: float,
        maze_size_px: float,
        show_solution: bool = False,
    ) -> None:
        """
        Рендерит полярный лабиринт с явными координатами.

        Args:
            c: Canvas
            maze: Объект лабиринта
            offset_x: X левого нижнего угла области
            offset_y: Y нижней границы области
            maze_size_px: Размер квадратной области в pt
            show_solution: Показывать ли решение
        """
        center_x = offset_x + maze_size_px / 2
        center_y = offset_y + maze_size_px / 2
        max_radius = maze_size_px / 2 - 2

        topology = PolarTopologyService(maze.cells_per_ring)
        connections = {cell: set(neighbors) for cell, neighbors in (maze.polar_connections or {}).items()}
        for cell in topology.iter_cells():
            connections.setdefault(cell, set())

        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1.0)

        end_cell = maze.solution_path[-1] if maze.solution_path else (topology.num_rings - 1, 0)

        for ring in range(topology.num_rings):
            count = topology.cells_per_ring[ring]
            for sector in range(count):
                cell = (ring, sector)
                linked = connections[cell]

                inner_info = topology.inner_neighbor_interval(ring, sector)
                if inner_info:
                    neighbor, angle_start, angle_end = inner_info
                    if neighbor not in linked and angle_end > angle_start:
                        radius = max_radius * ring / topology.num_rings
                        self._draw_arc(c, center_x, center_y, radius, angle_start, angle_end)

                if ring < topology.num_rings - 1:
                    for neighbor, angle_start, angle_end in topology.outer_neighbor_intervals(ring, sector):
                        if neighbor not in linked and angle_end > angle_start:
                            radius = max_radius * (ring + 1) / topology.num_rings
                            self._draw_arc(c, center_x, center_y, radius, angle_start, angle_end)
                else:
                    sector_start, sector_end = topology.get_sector_bounds(ring, sector)
                    if cell == end_cell:
                        gap = (sector_end - sector_start) * 0.3
                        left_end = sector_start + (sector_end - sector_start - gap) / 2
                        right_start = left_end + gap
                        self._draw_arc(c, center_x, center_y, max_radius, sector_start, left_end)
                        self._draw_arc(c, center_x, center_y, max_radius, right_start, sector_end)
                    else:
                        self._draw_arc(c, center_x, center_y, max_radius, sector_start, sector_end)
                if ring > 0:
                    cw_neighbor = topology.get_clockwise_neighbor(ring, sector)
                    if cw_neighbor not in linked:
                        _, sector_end = topology.get_sector_bounds(ring, sector)
                        inner_radius = max_radius * ring / topology.num_rings if ring > 0 else 0
                        outer_radius = max_radius * (ring + 1) / topology.num_rings
                        self._draw_radial_segment(c, center_x, center_y, sector_end, inner_radius, outer_radius)

        marker_r = max_radius / topology.num_rings * 0.45
        self._draw_triangle_marker(c, center_x, center_y, marker_r, angle=math.pi / 2, color=(0, 0.75, 0))

        end_angle = topology.get_sector_center_angle(*end_cell)
        arrow_tip_x = center_x + (max_radius + marker_r * 0.3) * math.cos(end_angle)
        arrow_tip_y = center_y + (max_radius + marker_r * 0.3) * math.sin(end_angle)
        self._draw_triangle_marker(c, arrow_tip_x, arrow_tip_y, marker_r, angle=end_angle + math.pi, color=(0.9, 0, 0))

        if show_solution and maze.solution_path:
            self._render_polar_solution_path(c, maze.solution_path, center_x, center_y, max_radius, topology)

    def _render_page_corner_deco(
        self,
        c: canvas.Canvas,
        accent: tuple[float, float, float],
        page_seed: int = 0,
    ) -> None:
        """
        Рисует декоративные элементы по всему периметру страницы: 2 слоя.

        Слой 1 (внешний) — крупные символы у рамки, в углах и по бокам.
        Слой 2 (внутренний) — меньшие символы с отступом, не заезжают в зону лабиринта.
        Чередование символов и цветов рандомное по номеру страницы.

        Args:
            c: Canvas
            accent: Базовый акцентный цвет
            page_seed: Номер страницы для уникального seed
        """
        frame_m = 8 * mm
        rng = random.Random(page_seed * 997 + 13)

        colors = [
            accent,
            (0.95, 0.35, 0.35),
            (0.30, 0.75, 0.45),
            (0.35, 0.55, 0.95),
            (0.95, 0.70, 0.20),
            (0.80, 0.45, 0.90),
            (0.25, 0.80, 0.85),
            (0.95, 0.55, 0.25),
        ]
        symbols_big = ["★", "✿", "♥", "♦", "☀", "❤", "✦", "◆"]
        symbols_mid = ["•", "♥", "★", "▲", "✿", "●", "♦", "✶"]
        symbols_small = ["·", "◦", "․", "⋅", "•", "▪"]

        # Границы зоны лабиринта (декор не должен заезжать сюда)
        maze_x_min = frame_m + 20 * mm
        maze_x_max = self.page_width - frame_m - 20 * mm
        maze_y_min = frame_m + 20 * mm
        # Верхняя зона ограничена плашкой заголовка
        header_bottom = self.page_height - frame_m - 22 * mm - 10 * mm
        maze_y_max = header_bottom

        def draw_sym(
            sym: str,
            x: float,
            y: float,
            size: float,
            color: tuple[float, float, float],
        ) -> None:
            """Рисует символ если он не попадает в зону лабиринта."""
            if maze_x_min < x < maze_x_max and maze_y_min < y < maze_y_max:
                return
            c.setFillColorRGB(*color)
            c.setFont("Helvetica-Bold", size)
            c.drawCentredString(x, y - size * 0.3, sym)

        # ============================================================
        # СЛОЙ 1: крупные символы у рамки (по периметру)
        # ============================================================
        step1 = 18 * mm

        # Углы — самые крупные
        corners = [
            (frame_m + 9 * mm,  self.page_height - frame_m - 9 * mm),
            (self.page_width - frame_m - 9 * mm, self.page_height - frame_m - 9 * mm),
            (frame_m + 9 * mm,  frame_m + 9 * mm),
            (self.page_width - frame_m - 9 * mm, frame_m + 9 * mm),
        ]
        for i, (cx, cy) in enumerate(corners):
            sym = rng.choice(symbols_big)
            col = rng.choice(colors)
            draw_sym(sym, cx, cy, 22, col)

        # Верхняя сторона
        x = frame_m + 9 * mm + step1
        while x < self.page_width - frame_m - 9 * mm:
            draw_sym(rng.choice(symbols_mid), x, self.page_height - frame_m - 7 * mm, 16, rng.choice(colors))
            x += step1

        # Нижняя сторона
        x = frame_m + 9 * mm + step1
        while x < self.page_width - frame_m - 9 * mm:
            draw_sym(rng.choice(symbols_mid), x, frame_m + 7 * mm, 16, rng.choice(colors))
            x += step1

        # Левая сторона
        y = frame_m + 9 * mm + step1
        while y < header_bottom:
            draw_sym(rng.choice(symbols_mid), frame_m + 7 * mm, y, 16, rng.choice(colors))
            y += step1

        # Правая сторона
        y = frame_m + 9 * mm + step1
        while y < header_bottom:
            draw_sym(rng.choice(symbols_mid), self.page_width - frame_m - 7 * mm, y, 16, rng.choice(colors))
            y += step1

        # ============================================================
        # СЛОЙ 2: средние символы чуть дальше от рамки
        # ============================================================
        step2 = 22 * mm
        offset2 = 16 * mm

        # Верхняя полоса (2-й слой)
        x = frame_m + offset2 + step2
        while x < self.page_width - frame_m - offset2:
            draw_sym(rng.choice(symbols_small), x, self.page_height - frame_m - offset2, 11, rng.choice(colors))
            x += step2

        # Нижняя полоса (2-й слой)
        x = frame_m + offset2 + step2
        while x < self.page_width - frame_m - offset2:
            draw_sym(rng.choice(symbols_small), x, frame_m + offset2, 11, rng.choice(colors))
            x += step2

        # Левая полоса (2-й слой)
        y = frame_m + offset2 + step2
        while y < header_bottom - offset2:
            draw_sym(rng.choice(symbols_small), frame_m + offset2, y, 11, rng.choice(colors))
            y += step2

        # Правая полоса (2-й слой)
        y = frame_m + offset2 + step2
        while y < header_bottom - offset2:
            draw_sym(rng.choice(symbols_small), self.page_width - frame_m - offset2, y, 11, rng.choice(colors))
            y += step2

    def _render_maze(self, c: canvas.Canvas, maze: Maze, y_offset: float = 0, show_solution: bool = False) -> None:
        """
        Рендерит сетку лабиринта.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            y_offset: Вертикальное смещение лабиринта
            show_solution: Показывать ли путь решения
        """
        if maze.shape == MazeShape.SQUARE:
            self._render_square_maze(c, maze, y_offset, show_solution)
        elif maze.shape == MazeShape.TRIANGULAR:
            self._render_triangular_maze(c, maze, y_offset, show_solution)
        elif maze.shape == MazeShape.RANDOM:
            self._render_random_maze(c, maze, y_offset, show_solution)
        elif maze.shape == MazeShape.DIAMOND:
            self._render_diamond_maze(c, maze, y_offset, show_solution)
        elif maze.shape == MazeShape.HEART:
            self._render_heart_maze(c, maze, y_offset, show_solution)
        elif maze.shape == MazeShape.CIRCULAR:
            self._render_circular_maze(c, maze, y_offset, show_solution)
        elif maze.shape == MazeShape.CHAOTIC:
            self._render_chaotic_maze(c, maze, y_offset, show_solution)
        else:
            self._render_rectangular_maze(c, maze, y_offset, show_solution)

    def _render_rectangular_maze(self, c: canvas.Canvas, maze: Maze, y_offset: float = 0, show_solution: bool = False) -> None:
        """
        Рендерит прямоугольный лабиринт с линиями между ячейками.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            y_offset: Вертикальное смещение лабиринта
            show_solution: Показывать ли путь решения
        """
        self._render_maze_with_mask(c, maze, y_offset, None, show_solution)

    def _render_square_maze(self, c: canvas.Canvas, maze: Maze, y_offset: float = 0, show_solution: bool = False) -> None:
        """
        Рендерит квадратный лабиринт.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            y_offset: Вертикальное смещение лабиринта
            show_solution: Показывать ли путь решения
        """
        self._render_maze_with_mask(c, maze, y_offset, None, show_solution)

    def _render_triangular_maze(self, c: canvas.Canvas, maze: Maze, y_offset: float = 0, show_solution: bool = False) -> None:
        """
        Рендерит треугольный лабиринт.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            y_offset: Вертикальное смещение лабиринта
            show_solution: Показывать ли путь решения
        """
        # Используем grid как маску (1 = внутри треугольника, 0 = снаружи)
        mask = [[bool(maze.grid[y][x]) for x in range(maze.width)] for y in range(maze.height)]
        self._render_maze_with_mask(c, maze, y_offset, mask, show_solution)

    def _render_random_maze(self, c: canvas.Canvas, maze: Maze, y_offset: float = 0, show_solution: bool = False) -> None:
        """
        Рендерит лабиринт случайной формы.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            y_offset: Вертикальное смещение лабиринта
            show_solution: Показывать ли путь решения
        """
        # Используем grid как маску
        mask = [[bool(maze.grid[y][x]) for x in range(maze.width)] for y in range(maze.height)]
        self._render_maze_with_mask(c, maze, y_offset, mask, show_solution)

    def _render_diamond_maze(self, c: canvas.Canvas, maze: Maze, y_offset: float = 0, show_solution: bool = False) -> None:
        """Рендерит лабиринт в форме ромба."""
        mask = [[bool(maze.grid[y][x]) for x in range(maze.width)] for y in range(maze.height)]
        self._render_maze_with_mask(c, maze, y_offset, mask, show_solution)

    def _render_heart_maze(self, c: canvas.Canvas, maze: Maze, y_offset: float = 0, show_solution: bool = False) -> None:
        """Рендерит лабиринт в форме сердца."""
        mask = [[bool(maze.grid[y][x]) for x in range(maze.width)] for y in range(maze.height)]
        self._render_maze_with_mask(c, maze, y_offset, mask, show_solution)

    def _render_maze_with_mask(
        self,
        c: canvas.Canvas,
        maze: Maze,
        y_offset: float,
        mask: list[list[bool]] | None,
        show_solution: bool = False,
    ) -> None:
        """
        Рендерит лабиринт с линиями между ячейками, опционально с маской.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            y_offset: Вертикальное смещение лабиринта
            mask: Маска формы (None = все ячейки внутри)
        """
        # Вычисляем позицию лабиринта на странице
        maze_width_px = maze.width * self.cell_size
        maze_height_px = maze.height * self.cell_size

        start_x = (self.page_width - maze_width_px) / 2
        start_y = (self.page_height - maze_height_px) / 2 - y_offset

        # Рисуем стены как линии между ячейками
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1.0)

        if maze.walls:
            # Используем информацию о стенах для отрисовки линий
            for y in range(maze.height):
                for x in range(maze.width):
                    # Проверяем маску если она задана
                    if mask and not mask[y][x]:
                        continue

                    cell_x = start_x + x * self.cell_size
                    cell_y = start_y + (maze.height - 1 - y) * self.cell_size

                    walls = maze.walls[y][x]  # [верх, право, низ, лево]

                    # Верхняя стена
                    if walls[0]:
                        c.line(cell_x, cell_y + self.cell_size, cell_x + self.cell_size, cell_y + self.cell_size)
                    # Правая стена
                    if walls[1]:
                        c.line(cell_x + self.cell_size, cell_y, cell_x + self.cell_size, cell_y + self.cell_size)
                    # Нижняя стена
                    if walls[2]:
                        c.line(cell_x, cell_y, cell_x + self.cell_size, cell_y)
                    # Левая стена
                    if walls[3]:
                        c.line(cell_x, cell_y, cell_x, cell_y + self.cell_size)
        else:
            # Fallback на старый стиль если walls не задан
            for y in range(maze.height):
                for x in range(maze.width):
                    if mask and not mask[y][x]:
                        continue

                    cell_x = start_x + x * self.cell_size
                    cell_y = start_y + (maze.height - 1 - y) * self.cell_size

                    if maze.grid[y][x] == 0:
                        c.rect(
                            cell_x,
                            cell_y,
                            self.cell_size,
                            self.cell_size,
                            fill=0,
                            stroke=1,
                        )

        # Рисуем старт и конец
        self._render_start_end(c, maze, start_x, start_y)

        # Рисуем путь решения если нужно
        if show_solution and maze.solution_path:
            self._render_solution_path(c, maze, maze.solution_path, start_x, start_y)

    def _render_solution_path(self, c: canvas.Canvas, maze: Maze, solution_path: list[tuple[int, int]], start_x: float, start_y: float) -> None:
        """
        Рисует путь решения лабиринта.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            solution_path: Список ячеек пути решения
            start_x: Начальная координата X лабиринта
            start_y: Начальная координата Y лабиринта
        """
        if not solution_path or len(solution_path) < 2:
            return

        c.setStrokeColorRGB(1, 0, 0)  # Красный цвет для пути
        c.setLineWidth(2.0)

        for i in range(len(solution_path) - 1):
            x1, y1 = solution_path[i]
            x2, y2 = solution_path[i + 1]

            # Конвертируем координаты ячеек в координаты на странице
            screen_x1 = start_x + x1 * self.cell_size + self.cell_size / 2
            screen_y1 = start_y + (maze.height - 1 - y1) * self.cell_size + self.cell_size / 2
            screen_x2 = start_x + x2 * self.cell_size + self.cell_size / 2
            screen_y2 = start_y + (maze.height - 1 - y2) * self.cell_size + self.cell_size / 2

            c.line(screen_x1, screen_y1, screen_x2, screen_y2)

    def _render_circular_maze(self, c: canvas.Canvas, maze: Maze, y_offset: float = 0, show_solution: bool = False) -> None:
        """
        Рендерит настоящий круглый лабиринт с дугами и радиальными линиями.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            y_offset: Вертикальное смещение лабиринта
            show_solution: Показывать ли путь решения
        """
        # Если есть полярный граф, отрисовываем настоящий круглый лабиринт
        if maze.polar_connections and maze.num_rings and maze.cells_per_ring:
            self._render_polar_maze(c, maze, y_offset, show_solution)
        else:
            # Fallback на маску
            mask = [[bool(maze.grid[y][x]) for x in range(maze.width)] for y in range(maze.height)]
            self._render_maze_with_mask(c, maze, y_offset, mask, show_solution)

    def _render_polar_maze(self, c: canvas.Canvas, maze: Maze, y_offset: float = 0, show_solution: bool = False) -> None:
        """
        Рендерит полярный лабиринт с дугами и радиальными линиями на основе графовой структуры.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            y_offset: Вертикальное смещение лабиринта
            show_solution: Показывать ли путь решения
        """
        # Вычисляем позицию лабиринта на странице
        maze_size_px = maze.width * self.cell_size

        start_x = (self.page_width - maze_size_px) / 2
        start_y = (self.page_height - maze_size_px) / 2 - y_offset

        # Центр лабиринта
        center_x = start_x + maze_size_px / 2
        center_y = start_y + maze_size_px / 2

        # Максимальный радиус
        max_radius = maze_size_px / 2 - self.cell_size

        topology = PolarTopologyService(maze.cells_per_ring)
        connections = {cell: set(neighbors) for cell, neighbors in (maze.polar_connections or {}).items()}
        for cell in topology.iter_cells():
            connections.setdefault(cell, set())

        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1.0)

        end_cell = maze.solution_path[-1] if maze.solution_path else (topology.num_rings - 1, 0)

        for ring in range(topology.num_rings):
            count = topology.cells_per_ring[ring]
            for sector in range(count):
                cell = (ring, sector)
                linked = connections[cell]

                # Внутренние дуги (граница с предыдущим кольцом)
                inner_info = topology.inner_neighbor_interval(ring, sector)
                if inner_info:
                    neighbor, angle_start, angle_end = inner_info
                    if neighbor not in linked and angle_end > angle_start:
                        radius = max_radius * ring / topology.num_rings
                        self._draw_arc(c, center_x, center_y, radius, angle_start, angle_end)

                # Наружные дуги (границы с внешними кольцами)
                if ring < topology.num_rings - 1:
                    for neighbor, angle_start, angle_end in topology.outer_neighbor_intervals(ring, sector):
                        if neighbor not in linked and angle_end > angle_start:
                            radius = max_radius * (ring + 1) / topology.num_rings
                            self._draw_arc(c, center_x, center_y, radius, angle_start, angle_end)
                else:
                    sector_start, sector_end = topology.get_sector_bounds(ring, sector)
                    if cell == end_cell:
                        gap = (sector_end - sector_start) * 0.3
                        gap = min(gap, sector_end - sector_start)
                        left_end = sector_start + (sector_end - sector_start - gap) / 2
                        right_start = left_end + gap
                        self._draw_arc(c, center_x, center_y, max_radius, sector_start, left_end)
                        self._draw_arc(c, center_x, center_y, max_radius, right_start, sector_end)
                    else:
                        self._draw_arc(c, center_x, center_y, max_radius, sector_start, sector_end)

                # Радиальные стены (по часовой стрелке)
                if ring > 0:
                    cw_neighbor = topology.get_clockwise_neighbor(ring, sector)
                    if cw_neighbor not in linked:
                        _, sector_end = topology.get_sector_bounds(ring, sector)
                        inner_radius = max_radius * ring / topology.num_rings if ring > 0 else 0
                        outer_radius = max_radius * (ring + 1) / topology.num_rings
                        self._draw_radial_segment(c, center_x, center_y, sector_end, inner_radius, outer_radius)

        # Рисуем старт — маленький зелёный треугольник в центре лабиринта
        marker_r = max_radius / topology.num_rings * 0.45
        self._draw_triangle_marker(c, center_x, center_y, marker_r, angle=math.pi / 2, color=(0, 0.75, 0))

        # Рисуем конец — красная стрелка снаружи лабиринта, указывающая в проход
        end_angle = topology.get_sector_center_angle(*end_cell)
        arrow_tip_x = center_x + (max_radius + marker_r * 0.3) * math.cos(end_angle)
        arrow_tip_y = center_y + (max_radius + marker_r * 0.3) * math.sin(end_angle)
        self._draw_triangle_marker(c, arrow_tip_x, arrow_tip_y, marker_r, angle=end_angle + math.pi, color=(0.9, 0, 0))

        # Рисуем путь решения если нужно
        if show_solution and maze.solution_path:
            self._render_polar_solution_path(
                c,
                maze.solution_path,
                center_x,
                center_y,
                max_radius,
                topology,
            )

    def _render_polar_solution_path(
        self,
        c: canvas.Canvas,
        solution_path: list[tuple[int, int]],
        center_x: float,
        center_y: float,
        max_radius: float,
        topology: PolarTopologyService,
    ) -> None:
        """Рисует непрерывный путь решения полярного лабиринта по коридорам."""

        if not solution_path or len(solution_path) < 2:
            return

        c.setStrokeColorRGB(1, 0, 0)
        c.setLineWidth(2.5)

        def cell_ring_radius(ring: int) -> float:
            return max_radius * (ring + 0.5) / topology.num_rings

        def radial_overlap_angle(inner: tuple[int, int], outer: tuple[int, int]) -> float:
            """Центральный угол перекрытия двух секторов на разных кольцах."""
            i_start, i_end = topology.get_sector_bounds(*inner)
            o_start, o_end = topology.get_sector_bounds(*outer)
            ov_s = max(i_start, o_start)
            ov_e = min(i_end, o_end)
            if ov_e > ov_s:
                return (ov_s + ov_e) / 2
            return (i_start + i_end) / 2

        def polar_to_xy(radius: float, angle: float) -> tuple[float, float]:
            return center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)

        def shortest_arc_end(a1: float, a2_raw: float) -> float:
            """Возвращает a2 с поправкой на кратчайшую дугу от a1."""
            diff = (a2_raw - a1) % (2 * math.pi)
            if diff > math.pi:
                return a1 - (2 * math.pi - diff)
            return a1 + diff

        # Первая точка — центр первой ячейки
        ring0, sec0 = solution_path[0]
        cur_angle = topology.get_sector_center_angle(ring0, sec0)
        cur_radius = cell_ring_radius(ring0) if ring0 > 0 else 0.0
        cur_x, cur_y = polar_to_xy(cur_radius, cur_angle)

        for current, nxt in zip(solution_path, solution_path[1:]):
            ring1, sector1 = current
            ring2, sector2 = nxt

            if ring1 == ring2:
                # Угловой переход: дуга на радиусе середины кольца
                radius = cell_ring_radius(ring1)
                next_angle = topology.get_sector_center_angle(ring2, sector2)
                arc_end = shortest_arc_end(cur_angle, next_angle)

                # Если текущая точка не на этом радиусе (пришли с другого кольца) —
                # сначала соединяем радиальным отрезком до дуги
                if abs(cur_radius - radius) > 0.5:
                    start_x, start_y = polar_to_xy(radius, cur_angle)
                    c.line(cur_x, cur_y, start_x, start_y)

                cur_radius = radius
                self._draw_arc_from(c, center_x, center_y, radius, cur_angle, arc_end, segments=24)
                cur_angle = arc_end
                cur_x, cur_y = polar_to_xy(radius, cur_angle)

            else:
                # Радиальный переход: линия по углу перекрытия секторов
                inner = current if ring1 < ring2 else nxt
                outer = nxt if ring1 < ring2 else current
                trans_angle = radial_overlap_angle(inner, outer)
                inner_radius = cell_ring_radius(inner[0])
                outer_radius = cell_ring_radius(outer[0])

                # Шаг 1: если текущий радиус не совпадает с радиусом inner — выровнять
                if abs(cur_radius - inner_radius) > 0.5:
                    mid_x, mid_y = polar_to_xy(inner_radius, cur_angle)
                    c.line(cur_x, cur_y, mid_x, mid_y)
                    cur_x, cur_y = mid_x, mid_y

                # Шаг 2: дуга по inner_radius до угла trans_angle (всегда, если нужно)
                cur_angle_norm = cur_angle % (2 * math.pi)
                if abs(cur_angle_norm - trans_angle) > 1e-6:
                    arc_end = shortest_arc_end(cur_angle, trans_angle)
                    self._draw_arc_from(c, center_x, center_y, inner_radius, cur_angle, arc_end, segments=12)
                    cur_angle = arc_end
                    cur_x, cur_y = polar_to_xy(inner_radius, cur_angle)

                # Шаг 3: радиальный отрезок до середины следующего кольца
                end_x, end_y = polar_to_xy(outer_radius, trans_angle)
                c.line(cur_x, cur_y, end_x, end_y)
                cur_radius = outer_radius
                cur_angle = trans_angle
                cur_x, cur_y = end_x, end_y

        # Финальный отрезок к внешней границе
        end_x = center_x + max_radius * math.cos(cur_angle)
        end_y = center_y + max_radius * math.sin(cur_angle)
        c.line(cur_x, cur_y, end_x, end_y)

    def _angle_in_range(self, angle: float, start: float, end: float) -> bool:
        """Проверяет, лежит ли угол строго внутри диапазона [start, end].

        Учитывает wrap-around через 2π.

        Args:
            angle: Проверяемый угол (радианы)
            start: Начало диапазона
            end: Конец диапазона

        Returns:
            True если angle ∈ (start, end)
        """
        two_pi = 2 * math.pi
        a = angle % two_pi
        s = start % two_pi
        e = end % two_pi
        if s < e:
            return s < a < e
        return a > s or a < e

    def _draw_triangle_marker(
        self,
        c: canvas.Canvas,
        cx: float,
        cy: float,
        size: float,
        angle: float,
        color: tuple[float, float, float],
    ) -> None:
        """
        Рисует равносторонний треугольник-маркер.

        Острие указывает в сторону angle, основание позади.

        Args:
            c: Canvas для рисования
            cx: Центр X
            cy: Центр Y
            size: Радиус описанной окружности
            angle: Угол острия (радианы)
            color: RGB-цвет заливки (0..1)
        """
        tip_x = cx + size * math.cos(angle)
        tip_y = cy + size * math.sin(angle)
        left_x = cx + size * math.cos(angle + 2 * math.pi / 3)
        left_y = cy + size * math.sin(angle + 2 * math.pi / 3)
        right_x = cx + size * math.cos(angle - 2 * math.pi / 3)
        right_y = cy + size * math.sin(angle - 2 * math.pi / 3)

        p = c.beginPath()
        p.moveTo(tip_x, tip_y)
        p.lineTo(left_x, left_y)
        p.lineTo(right_x, right_y)
        p.close()
        c.setFillColorRGB(*color)
        c.setStrokeColorRGB(*color)
        c.drawPath(p, fill=1, stroke=0)

    def _draw_arc(
        self,
        c: canvas.Canvas,
        center_x: float,
        center_y: float,
        radius: float,
        angle_start: float,
        angle_end: float,
        segments: int = 16,
    ) -> None:
        """Рисует дугу от angle_start до angle_end (направление задаётся знаком разности)."""
        if radius <= 0:
            return
        step = (angle_end - angle_start) / max(segments, 1)
        prev_x = center_x + radius * math.cos(angle_start)
        prev_y = center_y + radius * math.sin(angle_start)
        for i in range(1, segments + 1):
            angle = angle_start + step * i
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            c.line(prev_x, prev_y, x, y)
            prev_x, prev_y = x, y

    def _draw_arc_from(
        self,
        c: canvas.Canvas,
        center_x: float,
        center_y: float,
        radius: float,
        angle_start: float,
        angle_end: float,
        segments: int = 16,
    ) -> None:
        """Рисует дугу от angle_start до angle_end без автоисправления направления."""
        if radius <= 0 or abs(angle_end - angle_start) < 1e-9:
            return
        step = (angle_end - angle_start) / max(segments, 1)
        prev_x = center_x + radius * math.cos(angle_start)
        prev_y = center_y + radius * math.sin(angle_start)
        for i in range(1, segments + 1):
            angle = angle_start + step * i
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            c.line(prev_x, prev_y, x, y)
            prev_x, prev_y = x, y

    def _draw_radial_segment(
        self,
        c: canvas.Canvas,
        center_x: float,
        center_y: float,
        angle: float,
        inner_radius: float,
        outer_radius: float,
    ) -> None:
        start_x = center_x + inner_radius * math.cos(angle)
        start_y = center_y + inner_radius * math.sin(angle)
        end_x = center_x + outer_radius * math.cos(angle)
        end_y = center_y + outer_radius * math.sin(angle)
        c.line(start_x, start_y, end_x, end_y)

    def _render_chaotic_maze(self, c: canvas.Canvas, maze: Maze, y_offset: float = 0, show_solution: bool = False) -> None:
        """
        Рендерит хаотичный лабиринт с линиями между ячейками.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            y_offset: Вертикальное смещение лабиринта
            show_solution: Показывать ли путь решения
        """
        mask = [[bool(maze.grid[y][x]) for x in range(maze.width)] for y in range(maze.height)]
        self._render_maze_with_mask(c, maze, y_offset, mask, show_solution)

    def _render_start_end(self, c: canvas.Canvas, maze: Maze, start_x: float, start_y: float) -> None:
        """
        Рисует маркеры старта и конца лабиринта в виде треугольников.

        Треугольник указывает в направлении входа/выхода из лабиринта.
        Направление определяется по положению ячейки на границе сетки.

        Args:
            c: Canvas для рисования
            maze: Объект лабиринта
            start_x: Начальная координата X лабиринта на странице
            start_y: Начальная координата Y лабиринта на странице
        """
        marker_r = self.cell_size * 0.45

        def cell_center(gx: int, gy: int) -> tuple[float, float]:
            cx = start_x + gx * self.cell_size + self.cell_size / 2
            cy = start_y + (maze.height - 1 - gy) * self.cell_size + self.cell_size / 2
            return cx, cy

        def border_angle(gx: int, gy: int) -> float:
            """Угол, указывающий внутрь лабиринта из граничной ячейки."""
            if gy == 0:
                return math.pi / 2        # снизу → вверх
            if gy == maze.height - 1:
                return -math.pi / 2       # сверху → вниз
            if gx == 0:
                return 0.0                # слева → вправо
            return math.pi                # справа → влево

        sx, sy = maze.start
        ex, ey = maze.end

        scx, scy = cell_center(sx, sy)
        angle_s = border_angle(sx, sy)
        self._draw_triangle_marker(c, scx, scy, marker_r, angle=angle_s, color=(0, 0.75, 0))

        ecx, ecy = cell_center(ex, ey)
        angle_e = border_angle(ex, ey)
        self._draw_triangle_marker(c, ecx, ecy, marker_r, angle=angle_e + math.pi, color=(0.9, 0, 0))
