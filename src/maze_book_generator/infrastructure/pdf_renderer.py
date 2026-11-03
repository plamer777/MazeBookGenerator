"""PDF рендерер для генерации книг с лабиринтами."""

import io
import math
import random
from itertools import pairwise
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from maze_book_generator.domain.models import Book, BookConfig, BookPage, Maze, MazeShape
from maze_book_generator.domain.polar_topology_service import PolarTopologyService
from maze_book_generator.localization import BookTexts, Language
from maze_book_generator.settings import (
    WATERMARK_ALPHA,
    WATERMARK_BG_DIFF_GAIN,
    WATERMARK_BG_DIFF_THRESHOLD,
    WATERMARK_EDGE_FADE_BLUR_RATIO,
    WATERMARK_EDGE_FADE_INSET_RATIO,
    settings,
)
from maze_book_generator.utils import format_count_with_plural_ru

_DEJAVU_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
pdfmetrics.registerFont(TTFont("DejaVuSans", _DEJAVU_REGULAR))
pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", _DEJAVU_BOLD))


class PDFRenderer:
    """Рендерер PDF документов с лабиринтами."""

    def __init__(
        self,
        language: Language = "en",
        book_config: BookConfig | None = None,
        print_friendly: bool = False,
    ) -> None:
        """Инициализация рендерера с настройками из settings."""
        self.page_width = settings.PDF_PAGE_WIDTH * mm
        self.page_height = settings.PDF_PAGE_HEIGHT * mm
        self.margin = settings.PDF_MARGIN * mm
        self.cell_size = settings.DEFAULT_CELL_SIZE * mm
        self._t = BookTexts(language)
        self._book_config = book_config or BookConfig(language=language)
        self._print_friendly = print_friendly
        self._font = "DejaVuSans"
        self._font_bold = "DejaVuSans-Bold"

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

        if self._book_config.include_contents_page:
            self._render_contents_page(c, book)
            c.showPage()

        # Страница с введением и правилами
        self._render_intro_page(c, book)
        c.showPage()

        # Страницы с лабиринтами
        for page in book.pages:
            if page.is_solution:
                self._render_solution_page(c, page, book.theme.book_title)
            else:
                self._render_maze_page(c, page, book.theme.book_title)
            c.showPage()

        # Последняя страница с коллажем и напутствием
        self._render_outro_page(c, book)

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
            ((0.10, 0.15, 0.35), (0.20, 0.30, 0.55), (0.95, 0.70, 0.10)),  # синий + золото
            ((0.08, 0.28, 0.15), (0.15, 0.42, 0.28), (0.95, 0.65, 0.05)),  # зелёный + золото
            ((0.38, 0.08, 0.12), (0.55, 0.15, 0.20), (1.00, 0.55, 0.05)),  # бордо + яркий оранже
            ((0.12, 0.22, 0.42), (0.25, 0.42, 0.62), (1.00, 0.55, 0.10)),  # стальной + оранжевый
            ((0.22, 0.08, 0.42), (0.38, 0.18, 0.58), (0.95, 0.40, 0.85)),  # фиолетовый + мажента
        ]
        idx = sum(ord(ch) for ch in seed) % len(palettes)
        return palettes[idx]

    def _book_title(self, book: Book) -> str:
        """Возвращает отображаемое название книги с учётом BookConfig."""
        return self._book_config.title or book.theme.book_title

    def _book_subtitle(self) -> str:
        """Возвращает подзаголовок книги с учётом BookConfig."""
        return self._book_config.subtitle or self._t.get("subtitle")

    def _book_maze_count(self, book: Book) -> int:
        """Возвращает количество лабиринтов в книге."""
        if self._book_config.maze_count is not None:
            return self._book_config.maze_count
        return sum(1 for page in book.pages if not page.is_solution)

    def _book_age_label(self) -> str | None:
        """Возвращает подпись возрастного диапазона для обложки/contents."""
        age_value = self._book_config.age_range or self._book_config.target_age
        if not age_value:
            return None
        return self._t.format("cover_age", age=age_value)

    def _cover_mazes_label(self, count: int) -> str:
        """Возвращает подпись количества лабиринтов для обложки с учетом локали."""
        if self._book_config.language == "ru":
            return format_count_with_plural_ru(
                count=count,
                forms=("лабиринт", "лабиринта", "лабиринтов"),
                text_case="lower",
            )
        return self._t.format("cover_mazes", count=count)

    def _book_language_label(self) -> str:
        """Возвращает локализованное имя языка книги."""
        return self._t.get("cover_language")

    def _wrap_text_to_width(self, c: canvas.Canvas, text: str, font_name: str, font_size: int, max_width: float) -> list[str]:
        """Переносит строку на несколько строк так, чтобы каждая помещалась по ширине."""
        words = [part for part in text.split() if part]
        if not words:
            return [text.strip() or ""]

        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if c.stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
                continue

            if c.stringWidth(current, font_name, font_size) > max_width:
                lines.extend(self._split_long_word(c, current, font_name, font_size, max_width))
            else:
                lines.append(current)
            current = word

        if c.stringWidth(current, font_name, font_size) > max_width:
            lines.extend(self._split_long_word(c, current, font_name, font_size, max_width))
        else:
            lines.append(current)
        return [line for line in lines if line]

    def _split_long_word(self, c: canvas.Canvas, word: str, font_name: str, font_size: int, max_width: float) -> list[str]:
        """Разбивает слишком длинное слово на части, чтобы не выйти за пределы рамки."""
        chunks: list[str] = []
        current = ""
        for char in word:
            candidate = f"{current}{char}"
            if current and c.stringWidth(candidate, font_name, font_size) > max_width:
                chunks.append(current)
                current = char
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks or [word]

    def _fit_cover_title_layout(
        self,
        c: canvas.Canvas,
        title: str,
        max_width: float,
        max_lines: int = 5,
        max_title_block_height: float | None = None,
    ) -> tuple[int, list[str]]:
        """Подбирает размер шрифта и переносы строк для заголовка обложки."""
        min_size = 18
        for font_size in range(34, min_size - 1, -1):
            lines = self._wrap_text_to_width(c, title, self._font_bold, font_size, max_width)
            line_height = font_size * 1.2
            title_block_h = len(lines) * line_height
            if len(lines) <= max_lines and (
                max_title_block_height is None or title_block_h <= max_title_block_height
            ):
                return font_size, lines

        fallback_lines = self._wrap_text_to_width(c, title, self._font_bold, min_size, max_width)
        return min_size, fallback_lines

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
        title = self._book_title(book)
        subtitle = self._book_subtitle()
        maze_count = self._book_maze_count(book)
        bg_top, bg_bottom, accent = self._cover_palette(title)
        cover_accent = (0.0, 0.0, 0.0) if self._print_friendly else accent

        # --- Фон ---
        if self._print_friendly:
            c.setFillColorRGB(1, 1, 1)
            c.rect(0, 0, self.page_width, self.page_height, fill=1, stroke=0)
        else:
            # Вертикальный псевдо-градиент через горизонтальные полосы
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
        if not self._print_friendly:
            band_h = 28 * mm
            cell = 7 * mm
            self._render_maze_band(c, y_bottom=self.page_height - band_h, band_h=band_h, cell=cell, accent=accent)
            self._render_maze_band(c, y_bottom=0, band_h=band_h, cell=cell, accent=accent)

        # --- Рамка-меандр ---
        self._render_meander_border(c, cover_accent)

        # Информационный блок обложки (для расчета высоты центральной рамки)
        info_lines = [
            self._cover_mazes_label(maze_count),
        ]
        age_label = self._book_age_label()
        if age_label:
            info_lines.insert(0, age_label)
        if self._book_config.child_name:
            info_lines.append(self._t.format("cover_for_child", name=self._book_config.child_name))
        if self._book_config.child_age:
            info_lines.append(self._t.format("cover_child_age", age=self._book_config.child_age))

        # --- Блок названия по центру страницы ---
        center_y = self.page_height / 2
        base_box_h = 84 * mm
        box_margin = 22 * mm
        box_w = self.page_width - 2 * box_margin
        padding_x = 10 * mm
        padding_y = 8 * mm

        title_max_w = box_w - 2 * padding_x
        title_size, title_lines = self._fit_cover_title_layout(c, title, title_max_w)

        subtitle_size = 16
        info_size = 12
        title_line_h = title_size * 1.2
        subtitle_line_h = subtitle_size * 1.25
        info_line_h = 5.2 * mm
        gap_title_subtitle = 5 * mm
        gap_subtitle_info = 3.8 * mm if info_lines else 0
        info_block_h = len(info_lines) * info_line_h if info_lines else 0

        content_h = (
            len(title_lines) * title_line_h
            + gap_title_subtitle
            + subtitle_line_h
            + gap_subtitle_info
            + info_block_h
        )

        box_h = max(base_box_h, content_h + 2 * padding_y)
        max_box_h = self.page_height - (62 * mm if not self._print_friendly else 46 * mm)

        if box_h > max_box_h:
            available_title_h = max(
                20 * mm,
                max_box_h - 2 * padding_y - gap_title_subtitle - subtitle_line_h - gap_subtitle_info - info_block_h,
            )
            title_size, title_lines = self._fit_cover_title_layout(
                c,
                title,
                title_max_w,
                max_title_block_height=available_title_h,
            )
            title_line_h = title_size * 1.2
            content_h = (
                len(title_lines) * title_line_h
                + gap_title_subtitle
                + subtitle_line_h
                + gap_subtitle_info
                + info_block_h
            )
            box_h = min(max_box_h, max(base_box_h, content_h + 2 * padding_y))

        if not self._print_friendly:
            # Полупрозрачная плашка под текстом
            c.saveState()
            c.setFillColorRGB(0, 0, 0)
            c.setFillAlpha(0.45)
            c.rect(box_margin, center_y - box_h / 2, box_w, box_h, fill=1, stroke=0)
            c.restoreState()

        # Тонкие линии-акценты над и под плашкой
        c.setStrokeColorRGB(*cover_accent)
        c.setLineWidth(0.9 if self._print_friendly else 1.5)
        c.line(box_margin, center_y + box_h / 2, self.page_width - box_margin, center_y + box_h / 2)
        c.line(box_margin, center_y - box_h / 2, self.page_width - box_margin, center_y - box_h / 2)

        # Вертикальная компоновка текста внутри рамки с центрированием
        text_block_top = center_y + content_h / 2
        center_x = self.page_width / 2

        # Название (тень + основной текст) с переносами строк
        c.setFont(self._font_bold, title_size)
        title_cursor_top = text_block_top
        for line in title_lines:
            baseline_y = title_cursor_top - title_size
            if not self._print_friendly:
                c.saveState()
                c.setFillColorRGB(0, 0, 0)
                c.setFillAlpha(0.5)
                c.drawCentredString(center_x + 1.2, baseline_y - 1.2, line)
                c.restoreState()
            c.setFillColorRGB(*cover_accent)
            c.drawCentredString(center_x, baseline_y, line)
            title_cursor_top -= title_line_h

        # Подзаголовок
        subtitle_baseline_y = title_cursor_top - gap_title_subtitle - subtitle_size
        c.setFont(self._font, subtitle_size)
        if self._print_friendly:
            c.setFillColorRGB(0, 0, 0)
            c.drawCentredString(center_x, subtitle_baseline_y, subtitle)
        else:
            c.saveState()
            c.setFillColorRGB(1, 1, 1)
            c.setFillAlpha(0.80)
            c.drawCentredString(center_x, subtitle_baseline_y, subtitle)
            c.restoreState()

        # Информационный блок обложки
        if self._print_friendly:
            c.setFillColorRGB(0, 0, 0)
        else:
            c.setFillColorRGB(1, 1, 1)
        c.setFont(self._font, info_size)
        info_baseline_y = subtitle_baseline_y - gap_subtitle_info - info_size
        for line in info_lines:
            c.drawCentredString(center_x, info_baseline_y, line)
            info_baseline_y -= info_line_h

        # Декоративные уголки
        if not self._print_friendly:
            self._render_corner_ornaments(c, accent)

    def _render_contents_page(self, c: canvas.Canvas, book: Book) -> None:
        """Рендерит страницу "What's Inside / Что внутри"."""
        _, _, accent = self._cover_palette(self._book_title(book))
        bg = (1.0, 1.0, 1.0) if self._print_friendly else (0.98, 0.98, 1.0)
        c.setFillColorRGB(*bg)
        c.rect(0, 0, self.page_width, self.page_height, fill=1, stroke=0)

        margin = 16 * mm
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(2.0)
        c.roundRect(
            margin,
            margin,
            self.page_width - 2 * margin,
            self.page_height - 2 * margin,
            radius=6 * mm,
            fill=0,
            stroke=1,
        )

        title = self._t.get("contents_heading")
        c.setFillColorRGB(*accent)
        c.setFont(self._font_bold, 26)
        tw = c.stringWidth(title, self._font_bold, 26)
        c.drawString((self.page_width - tw) / 2, self.page_height - 38 * mm, title)

        lines = [
            self._t.format("contents_theme", value=self._book_config.theme_name or book.theme.book_title),
            self._t.format("contents_language", value=self._book_language_label()),
            self._t.format("contents_mazes", count=self._book_maze_count(book)),
            self._t.get("contents_answers"),
            self._t.get("contents_printable"),
        ]
        if self._book_config.difficulty_label:
            lines.append(self._t.format("contents_difficulty", value=self._book_config.difficulty_label))
        if self._book_config.child_name:
            lines.append(self._t.format("contents_child", name=self._book_config.child_name))
        if self._book_config.child_age:
            lines.append(self._t.format("contents_child_age", age=self._book_config.child_age))

        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.setFont(self._font, 14)
        y = self.page_height - 58 * mm
        for line in lines:
            c.drawString(34 * mm, y, f"• {line}")
            y -= 8 * mm

    def _render_intro_page(self, c: canvas.Canvas, book: Book) -> None:
        """
        Рендерит страницу с введением и правилами (страница 2 книги).

        Простой минималистичный дизайн с дружелюбным текстом на английском.

        Args:
            c: Canvas для рисования
            book: Объект книги
        """
        _, _, accent = self._cover_palette(book.theme.book_title)

        # --- Фон ---
        bg = (1.0, 1.0, 1.0) if self._print_friendly else (0.98, 0.98, 1.0)
        c.setFillColorRGB(*bg)
        c.rect(0, 0, self.page_width, self.page_height, fill=1, stroke=0)

        # --- Простая рамка ---
        margin = 15 * mm
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(2.0)
        c.rect(margin, margin, self.page_width - 2 * margin, self.page_height - 2 * margin, fill=0, stroke=1)

        # --- Заголовок ---
        c.setFillColorRGB(*accent)
        c.setFont(self._font_bold, 28)
        title = self._t.get("intro_heading")
        tw = c.stringWidth(title, self._font_bold, 28)
        c.drawString((self.page_width - tw) / 2, self.page_height - 40 * mm, title)

        # --- Текст правил ---
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.setFont(self._font, 14)

        intro_text = self._t.get("intro_body")
        self._draw_centered_wrapped_text(
            c=c,
            text=intro_text,
            font_name=self._font,
            font_size=14,
            start_y=self.page_height - 65 * mm,
            max_width=self.page_width - 70 * mm,
            line_height=6 * mm,
            max_height=self.page_height - 110 * mm,
            min_font_size=11,
        )

        self._render_intro_legend(c, accent, margin)

        # --- Декоративный элемент внизу ---
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(1.5)
        c.line(margin + 20 * mm, margin + 15 * mm, self.page_width - margin - 20 * mm, margin + 15 * mm)

    def _render_intro_legend(self, c: canvas.Canvas, accent: tuple[float, float, float], margin: float) -> None:
        """Рисует компактную легенду START/FINISH на странице инструкции."""
        legend_title = self._t.get("intro_legend_title")
        start_label = self._t.get("intro_legend_start")
        finish_label = self._t.get("intro_legend_finish")

        base_y = margin + 30 * mm
        c.setFillColorRGB(*accent)
        c.setFont(self._font_bold, 14)
        c.drawString(margin + 16 * mm, base_y + 11 * mm, legend_title)

        marker_size = 3.3 * mm
        start_x = margin + 24 * mm
        finish_x = margin + 86 * mm

        self._draw_triangle_marker(c, start_x, base_y + 3 * mm, marker_size, angle=math.pi / 2, color=(0, 0.75, 0))
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.setFont(self._font_bold, 11)
        c.drawString(start_x + 7 * mm, base_y + 1 * mm, start_label)

        self._draw_triangle_marker(c, finish_x, base_y + 3 * mm, marker_size, angle=-math.pi / 2, color=(0.9, 0, 0))
        c.drawString(finish_x + 7 * mm, base_y + 1 * mm, finish_label)

    def _draw_centered_wrapped_text(
        self,
        c: canvas.Canvas,
        text: str,
        font_name: str,
        font_size: float,
        start_y: float,
        max_width: float,
        line_height: float,
        max_height: float,
        min_font_size: float = 10,
    ) -> float:
        """Рисует многострочный центрированный текст с переносами и автоподбором размера."""
        current_size = font_size

        while current_size >= min_font_size:
            lines = self._wrap_text_lines(c, text, font_name, current_size, max_width)
            current_line_height = line_height * (current_size / font_size)
            total_height = len(lines) * current_line_height
            if total_height <= max_height:
                break
            current_size -= 1

        current_size = max(current_size, min_font_size)

        c.setFont(font_name, current_size)
        y = start_y
        current_line_height = line_height * (current_size / font_size)

        for line in lines:
            if line:
                lw = c.stringWidth(line, font_name, current_size)
                c.drawString((self.page_width - lw) / 2, y, line)
            y -= current_line_height

        return y

    def _wrap_text_lines(
        self,
        c: canvas.Canvas,
        text: str,
        font_name: str,
        font_size: float,
        max_width: float,
    ) -> list[str]:
        """Разбивает текст на строки с переносами по ширине."""
        c.setFont(font_name, font_size)
        wrapped: list[str] = []

        for paragraph in text.split("\n"):
            if not paragraph.strip():
                wrapped.append("")
                continue

            words = paragraph.split()
            current_line = ""
            for word in words:
                test_line = word if not current_line else f"{current_line} {word}"
                if c.stringWidth(test_line, font_name, font_size) <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        wrapped.append(current_line)
                    current_line = word

            if current_line:
                wrapped.append(current_line)

        return wrapped

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
        c.setLineWidth(1.3 if self._print_friendly else 2.5)
        c.rect(margin, margin, self.page_width - 2 * margin, self.page_height - 2 * margin, fill=0, stroke=1)

        # Внутренняя меандровая рамка
        c.setLineWidth(0.7 if self._print_friendly else 1.2)
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
        bg = (1.0, 1.0, 1.0) if self._print_friendly else (0.97, 0.97, 1.0)
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
        if not self._print_friendly:
            self._render_page_corner_deco(c, accent, page.page_number)

        # --- Плашка заголовка ---
        header_h = 22 * mm
        header_y = self.page_height - frame_m - header_h
        c.setFillColorRGB(*accent)
        c.roundRect(frame_m, header_y,
                    self.page_width - 2 * frame_m, header_h,
                    radius=4 * mm, fill=1, stroke=0)

        c.setFillColorRGB(1, 1, 1)
        c.setFont(self._font_bold, 18)
        maze_title = self._t.get("maze_title").replace("{n}", str(page.page_number))
        tw = c.stringWidth(maze_title, self._font_bold, 18)
        c.drawString((self.page_width - tw) / 2, header_y + 7 * mm, maze_title)

        # Подсказка под плашкой
        prompt_y = header_y - 8 * mm
        if self._print_friendly:
            c.setFillColorRGB(0.12, 0.12, 0.12)
        else:
            c.setFillColorRGB(*accent)
        c.setFont(self._font, 11)
        pw = c.stringWidth(page.prompt, self._font, 11)
        c.drawString((self.page_width - pw) / 2, prompt_y, page.prompt)

        if page.difficulty_label:
            difficulty_caption = self._t.format("difficulty_caption", value=page.difficulty_label)
            c.setFont(self._font_bold, 10)
            dw = c.stringWidth(difficulty_caption, self._font_bold, 10)
            c.drawString((self.page_width - dw) / 2, prompt_y - 5 * mm, difficulty_caption)

        # --- Лабиринт максимального размера ---
        # Верхняя граница строго под подсказкой (с зазором 5mm)
        deco_margin = 20 * mm
        maze_top = prompt_y - 11 * mm
        maze_area_x = frame_m + deco_margin
        maze_area_y = frame_m + deco_margin
        maze_area_w = self.page_width - 2 * (frame_m + deco_margin)
        maze_area_h = maze_top - maze_area_y

        # --- Водяной знак-иллюстрация под лабиринтом ---
        if page.image_path and not self._print_friendly:
            self._render_watermark_image(c, page.image_path, maze_area_x, maze_area_y, maze_area_w, maze_area_h)

        self._render_maze_fitted(
            c,
            page.maze,
            maze_area_x,
            maze_area_y,
            maze_area_w,
            maze_area_h,
            show_labels=self._book_config.show_start_finish_labels,
        )

        # --- Номер страницы ---
        c.setFillColorRGB(*accent)
        c.setFont(self._font, 9)
        c.drawRightString(self.page_width - frame_m - 4 * mm, frame_m + 3 * mm, f"#{page.page_number}")

    def _render_solution_page(self, c: canvas.Canvas, page: BookPage, book_title: str = "") -> None:
        """
        Рендерит страницу с ответом в том же детском стиле.

        Args:
            c: Canvas для рисования
            page: Объект страницы
        """
        _, _, accent = self._cover_palette(book_title or page.title)

        bg = (1.0, 1.0, 1.0) if self._print_friendly else (0.97, 0.97, 1.0)
        c.setFillColorRGB(*bg)
        c.rect(0, 0, self.page_width, self.page_height, fill=1, stroke=0)

        frame_m = 8 * mm
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(2.5)
        c.roundRect(frame_m, frame_m,
                    self.page_width - 2 * frame_m,
                    self.page_height - 2 * frame_m,
                    radius=6 * mm, fill=0, stroke=1)

        if not self._print_friendly:
            self._render_page_corner_deco(c, accent, page.page_number)

        header_h = 22 * mm
        header_y = self.page_height - frame_m - header_h
        c.setFillColorRGB(*accent)
        c.roundRect(frame_m, header_y,
                    self.page_width - 2 * frame_m, header_h,
                    radius=4 * mm, fill=1, stroke=0)

        sol_title = f"{self._t.get('maze_title').replace('{n}', str(page.page_number))} — {self._t.get('answer_page_suffix')}"
        c.setFillColorRGB(1, 1, 1)
        c.setFont(self._font_bold, 18)
        tw = c.stringWidth(sol_title, self._font_bold, 18)
        c.drawString((self.page_width - tw) / 2, header_y + 7 * mm, sol_title)

        deco_margin = 20 * mm
        maze_top = header_y - 5 * mm
        maze_area_x = frame_m + deco_margin
        maze_area_y = frame_m + deco_margin
        maze_area_w = self.page_width - 2 * (frame_m + deco_margin)
        maze_area_h = maze_top - maze_area_y

        if page.image_path and not self._print_friendly:
            self._render_watermark_image(c, page.image_path, maze_area_x, maze_area_y, maze_area_w, maze_area_h)

        self._render_maze_fitted(
            c,
            page.maze,
            maze_area_x,
            maze_area_y,
            maze_area_w,
            maze_area_h,
            show_solution=True,
            show_labels=self._book_config.show_start_finish_labels,
        )

        c.setFillColorRGB(*accent)
        c.setFont(self._font, 9)
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
            img = self._prepare_watermark_rgba(img, alpha)

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
        except Exception:
            pass

    def _prepare_watermark_rgba(self, img: Image.Image, alpha: float) -> Image.Image:
        """Подготавливает RGBA-изображение watermark с мягким смешиванием в фоне."""
        rgb = img.convert("RGB")
        r, g, b, src_alpha = img.split()

        scaled_alpha = src_alpha.point(lambda v: int(max(0, min(255, v * alpha))))
        bg_color = self._estimate_image_background_color(rgb)

        bg_layer = Image.new("RGB", rgb.size, bg_color)
        diff = ImageChops.difference(rgb, bg_layer)
        fg_strength = ImageOps.grayscale(diff)

        threshold = WATERMARK_BG_DIFF_THRESHOLD
        gain = WATERMARK_BG_DIFF_GAIN
        fg_mask = fg_strength.point(
            lambda v: int(max(0, min(255, (v - threshold) * gain)))
        )
        fg_mask = fg_mask.filter(ImageFilter.GaussianBlur(1.2))

        edge_mask = self._build_edge_fade_mask(rgb.width, rgb.height)
        alpha_mask = ImageChops.multiply(scaled_alpha, fg_mask)
        alpha_mask = ImageChops.multiply(alpha_mask, edge_mask)

        return Image.merge("RGBA", (r, g, b, alpha_mask))

    def _estimate_image_background_color(self, img: Image.Image) -> tuple[int, int, int]:
        """Оценивает фон по среднему цвету четырёх углов изображения."""
        w, h = img.size
        sample_points = [
            (0, 0),
            (w - 1, 0),
            (0, h - 1),
            (w - 1, h - 1),
        ]
        samples = [img.getpixel(point) for point in sample_points]
        red = int(sum(pixel[0] for pixel in samples) / len(samples))
        green = int(sum(pixel[1] for pixel in samples) / len(samples))
        blue = int(sum(pixel[2] for pixel in samples) / len(samples))
        return red, green, blue

    def _build_edge_fade_mask(self, width: int, height: int) -> Image.Image:
        """Строит маску мягкого затухания по краям (центр читаемее, края прозрачнее)."""
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)

        inset_x = max(2, int(width * WATERMARK_EDGE_FADE_INSET_RATIO))
        inset_y = max(2, int(height * WATERMARK_EDGE_FADE_INSET_RATIO))
        draw.ellipse(
            (inset_x, inset_y, width - inset_x, height - inset_y),
            fill=255,
        )

        blur_radius = max(2.0, min(width, height) * WATERMARK_EDGE_FADE_BLUR_RATIO)
        return mask.filter(ImageFilter.GaussianBlur(blur_radius))

    def _render_image_collage(
        self,
        c: canvas.Canvas,
        illustrations_dir: Path,
        alpha: float = WATERMARK_ALPHA,
        seed: int | None = None,
    ) -> None:
        """
        Рендерит коллаж: 1 крупное изображение по центру + 4 мелких по углам.

        Структура:
        - Центр: одно изображение 62–70% ширины страницы, поворот ±8°.
        - Углы (TL, TR, BL, BR): по одному изображению 20–28% ширины, поворот ±15°.

        Args:
            c: Canvas для рисования
            illustrations_dir: Папка с PNG-файлами
            alpha: Прозрачность изображений (не изменяется)
            seed: Seed для детерминированной вариативности коллажа
        """
        if not illustrations_dir.exists():
            return

        images = list(illustrations_dir.glob("*.png"))
        if not images:
            return

        rng = random.Random(seed)

        # Перемешиваем и при необходимости повторяем, чтобы хватило на 5 слотов
        pool = images.copy()
        rng.shuffle(pool)
        while len(pool) < 5:
            pool.append(rng.choice(images))

        pw, ph = self.page_width, self.page_height
        margin = 12 * mm

        # Слоты: (img_path, scale_range, cx_frac, cy_frac, angle_range)
        # cx/cy — доля от размера страницы для центра изображения
        slots = [
            # --- центральное крупное ---
            (pool[0], (0.62, 0.70), 0.50, 0.50, (-8.0, 8.0)),
            # --- углы: TL, TR, BL, BR ---
            (pool[1], (0.20, 0.28), 0.0, 1.0, (-15.0, 15.0)),  # TL (пересчитывается ниже)
            (pool[2], (0.20, 0.28), 1.0, 1.0, (-15.0, 15.0)),  # TR
            (pool[3], (0.20, 0.28), 0.0, 0.0, (-15.0, 15.0)),  # BL
            (pool[4], (0.20, 0.28), 1.0, 0.0, (-15.0, 15.0)),  # BR
        ]

        for i, (img_path, scale_range, cx_frac, cy_frac, angle_range) in enumerate(slots):
            try:
                img = Image.open(img_path).convert("RGBA")

                r, g, b, a = img.split()
                a = a.point(lambda v: int(v * alpha))
                img = Image.merge("RGBA", (r, g, b, a))

                # Размер
                scale = rng.uniform(*scale_range)
                draw_w = pw * scale
                draw_h = draw_w * (img.height / img.width)

                # Поворот
                angle = rng.uniform(*angle_range)
                img = img.rotate(angle, expand=True)
                # После rotate размер расширяется — пересчитываем
                rot_w = draw_w * abs(math.cos(math.radians(angle))) + draw_h * abs(math.sin(math.radians(angle)))
                rot_h = draw_w * abs(math.sin(math.radians(angle))) + draw_h * abs(math.cos(math.radians(angle)))

                # Позиция центра слота с небольшим случайным смещением
                jitter_x = rng.uniform(-margin * 0.5, margin * 0.5)
                jitter_y = rng.uniform(-margin * 0.5, margin * 0.5)
                cx = cx_frac * pw + jitter_x
                cy = cy_frac * ph + jitter_y

                # Для угловых — прижимаем к краю с отступом
                if i > 0:
                    half_w = rot_w / 2
                    half_h = rot_h / 2
                    cx = margin + half_w if cx_frac < 0.5 else pw - margin - half_w
                    cy = margin + half_h if cy_frac < 0.5 else ph - margin - half_h
                    cx += jitter_x
                    cy += jitter_y

                draw_x = cx - rot_w / 2
                draw_y = cy - rot_h / 2

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)

                c.drawImage(
                    ImageReader(buf),
                    draw_x, draw_y,
                    width=rot_w, height=rot_h,
                    mask="auto",
                )
            except Exception:
                pass

    def _render_outro_page(self, c: canvas.Canvas, book: Book) -> None:
        """
        Рендерит последнюю страницу с коллажем иллюстраций и напутствием.

        Args:
            c: Canvas для рисования
            book: Объект книги
        """
        _, _, accent = self._cover_palette(book.theme.book_title)

        # --- Фон ---
        bg = (1.0, 1.0, 1.0) if self._print_friendly else (0.95, 0.95, 1.0)
        c.setFillColorRGB(*bg)
        c.rect(0, 0, self.page_width, self.page_height, fill=1, stroke=0)

        # --- Коллаж изображений ---
        if not self._print_friendly:
            illustrations_dir = Path(book.output_dir) / "illustrations"
            collage_seed = book.id * 1009 + sum(ord(ch) for ch in book.theme.book_title)
            self._render_image_collage(
                c,
                illustrations_dir,
                alpha=WATERMARK_ALPHA,
                seed=collage_seed,
            )

        # --- Полупрозрачная плашка под текстом ---
        # padding — симметричный внутренний отступ от рамки до контента сверху и снизу
        padding = 7 * mm
        content_h = 36 * mm  # высота зоны контента (заголовок + тело текста)
        box_h = content_h + 2 * padding
        box_margin = 30 * mm
        # Центр плашки совпадает с центром страницы
        center_y = self.page_height / 2
        box_bottom = center_y - box_h / 2
        # Верхняя граница контента: верх плашки минус padding
        content_top = box_bottom + box_h - padding

        c.saveState()
        c.setFillColorRGB(1, 1, 1)
        c.setFillAlpha(0.85)
        c.roundRect(box_margin, box_bottom,
                    self.page_width - 2 * box_margin, box_h,
                    radius=8 * mm, fill=1, stroke=0)
        c.restoreState()

        # --- Рамка плашки ---
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(2.0)
        c.roundRect(box_margin, box_bottom,
                    self.page_width - 2 * box_margin, box_h,
                    radius=8 * mm, fill=0, stroke=1)

        # --- Текст напутствия ---
        # Заголовок прижат к верху контентной зоны
        title_font_size = 24
        title_y = content_top - title_font_size * 0.4  # baseline чуть ниже верхней границы
        c.setFillColorRGB(*accent)
        c.setFont(self._font_bold, title_font_size)
        title = (
            self._t.format("outro_heading_personal", name=self._book_config.child_name)
            if self._book_config.child_name
            else self._t.get("outro_heading")
        )
        tw = c.stringWidth(title, self._font_bold, title_font_size)
        c.drawString((self.page_width - tw) / 2, title_y, title)

        # Тело текста начинается через один интервал ниже заголовка
        body_start_y = title_y - 9 * mm
        c.setFillColorRGB(0.3, 0.3, 0.3)
        outro_text = self._t.get("outro_body")
        self._draw_centered_wrapped_text(
            c=c,
            text=outro_text,
            font_name=self._font,
            font_size=14,
            start_y=body_start_y,
            max_width=self.page_width - 90 * mm,
            line_height=5.5 * mm,
            max_height=content_h - title_font_size * 0.4 - 9 * mm,
            min_font_size=11,
        )

        # --- Подпись в правом нижнем углу страницы ---
        signature = self._t.format("outro_signature", book_title=self._book_title(book))
        sig_font_size = 10
        sig_margin = 10 * mm
        c.saveState()
        c.setFillColorRGB(*accent)
        c.setFillAlpha(0.65)
        c.setFont(self._font, sig_font_size)
        sw = c.stringWidth(signature, self._font, sig_font_size)
        c.drawString(self.page_width - sig_margin - sw, sig_margin, signature)
        c.restoreState()

    def _render_maze_fitted(
        self,
        c: canvas.Canvas,
        maze: Maze,
        area_x: float,
        area_y: float,
        area_w: float,
        area_h: float,
        show_solution: bool = False,
        show_labels: bool = False,
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
            self._render_polar_maze_at(c, maze, offset_x, offset_y, diameter, show_solution, show_labels)
        else:
            cell_w = area_w / maze.width
            cell_h = area_h / maze.height
            fit_cell = min(cell_w, cell_h)
            maze_w_px = maze.width * fit_cell
            maze_h_px = maze.height * fit_cell
            offset_x = area_x + (area_w - maze_w_px) / 2
            offset_y = area_y + (area_h - maze_h_px) / 2
            self.cell_size = fit_cell
            self._render_maze_at(c, maze, offset_x, offset_y, show_solution, show_labels)

        self.cell_size = orig_cell

    def _render_maze_at(
        self,
        c: canvas.Canvas,
        maze: Maze,
        start_x: float,
        start_y: float,
        show_solution: bool = False,
        show_labels: bool = False,
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

        self._render_start_end(c, maze, start_x, start_y, show_labels=show_labels)

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
        show_labels: bool = False,
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

        if show_labels:
            start_text = self._t.get("start_label")
            finish_text = self._t.get("finish_label")
            start_pos, finish_pos = self._compute_marker_label_positions(
                c,
                start_marker=(center_x, center_y),
                finish_marker=(arrow_tip_x, arrow_tip_y),
                start_text=start_text,
                finish_text=finish_text,
                marker_r=marker_r,
            )
            self._draw_marker_label(c, start_pos[0], start_pos[1], start_text)
            self._draw_marker_label(c, finish_pos[0], finish_pos[1], finish_text)

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
            c.setFont(self._font_bold, size)
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
        for cx, cy in corners:
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

        for current, nxt in pairwise(solution_path):
            ring1, _sector1 = current
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

    def _compute_marker_label_positions(
        self,
        c: canvas.Canvas,
        start_marker: tuple[float, float],
        finish_marker: tuple[float, float],
        start_text: str,
        finish_text: str,
        marker_r: float,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Вычисляет позиции подписей START/FINISH без визуального наложения."""
        font_size = 7.5
        text_height = font_size * 1.25
        pad = 0.7 * mm

        start_w = c.stringWidth(start_text, self._font_bold, font_size)
        finish_w = c.stringWidth(finish_text, self._font_bold, font_size)

        horizontal_gap = marker_r + 1.6 * mm
        vertical_gap = marker_r + 1.2 * mm

        def label_bbox(cx: float, baseline_y: float, width: float) -> tuple[float, float, float, float]:
            """Возвращает bbox подписи как (left, bottom, right, top)."""
            left = cx - width / 2 - pad
            right = cx + width / 2 + pad
            bottom = baseline_y - pad
            top = baseline_y + text_height + pad
            return left, bottom, right, top

        def overlaps(
            first: tuple[float, float, float, float],
            second: tuple[float, float, float, float],
        ) -> bool:
            """Проверяет пересечение двух прямоугольников."""
            f_left, f_bottom, f_right, f_top = first
            s_left, s_bottom, s_right, s_top = second
            return not (
                f_right <= s_left
                or s_right <= f_left
                or f_top <= s_bottom
                or s_top <= f_bottom
            )

        sx, sy = start_marker
        fx, fy = finish_marker

        start_candidates = [
            (sx - (horizontal_gap + start_w / 2), sy + vertical_gap),
            (sx - (horizontal_gap + start_w / 2), sy),
            (sx - (horizontal_gap + start_w / 2), sy - vertical_gap),
            (sx, sy + 1.5 * vertical_gap),
            (sx, sy - 1.5 * vertical_gap),
            (sx + (horizontal_gap + start_w / 2), sy + vertical_gap),
        ]
        finish_candidates = [
            (fx + (horizontal_gap + finish_w / 2), fy + vertical_gap),
            (fx + (horizontal_gap + finish_w / 2), fy),
            (fx + (horizontal_gap + finish_w / 2), fy - vertical_gap),
            (fx, fy + 1.5 * vertical_gap),
            (fx, fy - 1.5 * vertical_gap),
            (fx - (horizontal_gap + finish_w / 2), fy + vertical_gap),
        ]

        for start_pos in start_candidates:
            for finish_pos in finish_candidates:
                start_bbox = label_bbox(start_pos[0], start_pos[1], start_w)
                finish_bbox = label_bbox(finish_pos[0], finish_pos[1], finish_w)
                if not overlaps(start_bbox, finish_bbox):
                    return start_pos, finish_pos

        start_pos = start_candidates[0]
        finish_pos = finish_candidates[0]
        push = 1.8 * mm
        if sx <= fx:
            start_pos = (start_pos[0] - push, start_pos[1] + 0.8 * mm)
            finish_pos = (finish_pos[0] + push, finish_pos[1] - 0.8 * mm)
        else:
            start_pos = (start_pos[0] + push, start_pos[1] + 0.8 * mm)
            finish_pos = (finish_pos[0] - push, finish_pos[1] - 0.8 * mm)
        return start_pos, finish_pos

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

    def _render_start_end(
        self,
        c: canvas.Canvas,
        maze: Maze,
        start_x: float,
        start_y: float,
        show_labels: bool = False,
    ) -> None:
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

        if show_labels:
            start_text = self._t.get("start_label")
            finish_text = self._t.get("finish_label")
            start_pos, finish_pos = self._compute_marker_label_positions(
                c,
                start_marker=(scx, scy),
                finish_marker=(ecx, ecy),
                start_text=start_text,
                finish_text=finish_text,
                marker_r=marker_r,
            )
            self._draw_marker_label(c, start_pos[0], start_pos[1], start_text)
            self._draw_marker_label(c, finish_pos[0], finish_pos[1], finish_text)

    def _draw_marker_label(self, c: canvas.Canvas, x: float, y: float, text: str) -> None:
        """Рисует компактную подпись маркера START/FINISH рядом с треугольником."""
        c.saveState()
        c.setFillColorRGB(0.12, 0.12, 0.12)
        c.setFont(self._font_bold, 7.5)
        c.drawCentredString(x, y, text)
        c.restoreState()
