"""Unit-тесты для PDFRenderer."""

import unittest
from unittest.mock import MagicMock, patch

from src.domain.models import Book, BookConfig, BookPage, Difficulty, Maze, MazeShape, Theme
from src.infrastructure.pdf_renderer import PDFRenderer


class TestPDFRenderer(unittest.TestCase):
    """Проверяет логику PDF рендерера с моками внешних зависимостей."""

    def setUp(self) -> None:
        """Инициализация рендерера с тестовой конфигурацией."""
        self.config = BookConfig(language="en")
        self.renderer = PDFRenderer(language="en", book_config=self.config)

    def test_initialization(self) -> None:
        """Инициализация рендерера должна устанавливать корректные параметры."""
        self.assertIsNotNone(self.renderer.page_width)
        self.assertIsNotNone(self.renderer.page_height)
        self.assertIsNotNone(self.renderer.margin)
        self.assertIsNotNone(self.renderer.cell_size)

    def test_book_title_from_config(self) -> None:
        """Название книги должно браться из конфигурации, если задано."""
        book = self._create_test_book()
        self.config.title = "Custom Title"

        title = self.renderer._book_title(book)
        self.assertEqual(title, "Custom Title")

    def test_book_title_from_theme(self) -> None:
        """Название книги должно браться из темы, если не задано в конфигурации."""
        book = self._create_test_book()
        self.config.title = None

        title = self.renderer._book_title(book)
        self.assertEqual(title, "Test Theme")

    def test_book_subtitle_from_config(self) -> None:
        """Подзаголовок должен браться из конфигурации, если задан."""
        self.config.subtitle = "Custom Subtitle"

        subtitle = self.renderer._book_subtitle()
        self.assertEqual(subtitle, "Custom Subtitle")

    def test_book_maze_count_from_config(self) -> None:
        """Количество лабиринтов должно браться из конфигурации, если задано."""
        book = self._create_test_book()
        self.config.maze_count = 15

        count = self.renderer._book_maze_count(book)
        self.assertEqual(count, 15)

    def test_book_maze_count_from_book(self) -> None:
        """Количество лабиринтов должно считаться из страниц, если не задано в конфигурации."""
        book = self._create_test_book()
        self.config.maze_count = None

        count = self.renderer._book_maze_count(book)
        self.assertEqual(count, 2)  # 2 maze pages

    def test_book_age_label_from_config(self) -> None:
        """Возрастная метка должна браться из конфигурации."""
        self.config.age_range = "5-8 years"

        label = self.renderer._book_age_label()
        self.assertIsNotNone(label)
        self.assertIn("5-8", label)

    def test_book_age_label_from_target_age(self) -> None:
        """Возрастная метка должна браться из target_age, если age_range не задан."""
        self.config.age_range = None
        self.config.target_age = "6-9 years"

        label = self.renderer._book_age_label()
        self.assertIsNotNone(label)
        self.assertIn("6-9", label)

    def test_book_age_label_none(self) -> None:
        """Возрастная метка должна быть None, если не задано."""
        self.config.age_range = None
        self.config.target_age = None

        label = self.renderer._book_age_label()
        self.assertIsNone(label)

    def test_cover_mazes_label_english(self) -> None:
        """Метка количества лабиринтов должна быть локализована для английского."""
        self.config.language = "en"
        renderer = PDFRenderer(language="en", book_config=self.config)

        label = renderer._cover_mazes_label(5)
        self.assertEqual(label, "5 Mazes")

    def test_cover_mazes_label_russian(self) -> None:
        """Метка количества лабиринтов должна быть локализована для русского."""
        self.config.language = "ru"
        renderer = PDFRenderer(language="ru", book_config=self.config)

        label = renderer._cover_mazes_label(5)
        self.assertEqual(label, "5 лабиринтов")

    def test_cover_palette_deterministic(self) -> None:
        """Палитра должна быть детерминированной для одного и того же seed."""
        palette1 = self.renderer._cover_palette("Test")
        palette2 = self.renderer._cover_palette("Test")

        self.assertEqual(palette1, palette2)

    def test_cover_palette_different_seeds(self) -> None:
        """Разные seed должны давать разные палитры."""
        palette1 = self.renderer._cover_palette("Seed1")
        palette2 = self.renderer._cover_palette("Seed2")

        # Палитры могут совпадать случайно, но с высокой вероятностью разные
        # Проверяем, что хотя бы один цвет отличается
        self.assertNotEqual(palette1, palette2)

    def test_wrap_text_to_width_short_text(self) -> None:
        """Короткий текст не должен переноситься."""
        mock_canvas = MagicMock()
        mock_canvas.stringWidth.return_value = 50  # ширина меньше max_width

        lines = self.renderer._wrap_text_to_width(mock_canvas, "Short text", "font", 12, 100)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "Short text")

    def test_wrap_text_to_width_long_text(self) -> None:
        """Длинный текст должен переноситься по словам."""
        mock_canvas = MagicMock()
        # Первое слово влезает, второе - нет
        def stringWidth_side_effect(text, font, size):
            if text == "Hello":
                return 40
            elif text == "Hello world":
                return 120
            elif text == "world":
                return 50
            return 0

        mock_canvas.stringWidth.side_effect = stringWidth_side_effect

        lines = self.renderer._wrap_text_to_width(mock_canvas, "Hello world", "font", 12, 100)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "Hello")
        self.assertEqual(lines[1], "world")

    def test_split_long_word(self) -> None:
        """Длинное слово должно разбиваться на части."""
        mock_canvas = MagicMock()

        # Каждая буква занимает 10 единиц
        def stringWidth_side_effect(text, font, size):
            return len(text) * 10

        mock_canvas.stringWidth.side_effect = stringWidth_side_effect

        chunks = self.renderer._split_long_word(mock_canvas, "VeryLongWord", "font", 12, 20)
        self.assertGreater(len(chunks), 1)
        # Проверяем, что общая длина соответствует исходному слову
        joined = "".join(chunks)
        self.assertEqual(joined, "VeryLongWord")

    def test_fit_cover_title_layout_fits_in_one_line(self) -> None:
        """Заголовок, который влезает в одну строку, должен быть без переносов."""
        mock_canvas = MagicMock()
        mock_canvas.stringWidth.return_value = 100  # влезает в max_width

        font_size, lines = self.renderer._fit_cover_title_layout(mock_canvas, "Short Title", 200)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "Short Title")
        self.assertGreater(font_size, 18)

    def test_fit_cover_title_layout_wraps_to_multiple_lines(self) -> None:
        """Длинный заголовок должен переноситься на несколько строк."""
        mock_canvas = MagicMock()
        # Каждое слово занимает много места
        def stringWidth_side_effect(text, font, size):
            return len(text) * 30

        mock_canvas.stringWidth.side_effect = stringWidth_side_effect

        font_size, lines = self.renderer._fit_cover_title_layout(mock_canvas, "Very Long Title Here", 100)
        self.assertGreater(len(lines), 1)

    def test_fit_cover_title_layout_reduces_font_size(self) -> None:
        """Если текст не влезает, размер шрифта должен уменьшаться."""
        mock_canvas = MagicMock()
        # Большой размер шрифта даёт большую ширину
        def stringWidth_side_effect(text, font, size):
            return len(text) * size * 2

        mock_canvas.stringWidth.side_effect = stringWidth_side_effect

        font_size, lines = self.renderer._fit_cover_title_layout(mock_canvas, "Very Long Title", 100)
        self.assertLess(font_size, 34)  # начальный размер

    def test_render_book_calls_render_cover(self) -> None:
        """Рендер книги должен вызывать рендер обложки."""
        book = self._create_test_book()
        output_path = MagicMock()

        with patch.object(self.renderer, "_render_cover"):
            with patch.object(self.renderer, "_render_intro_page"):
                with patch.object(self.renderer, "_render_maze_page"):
                    with patch.object(self.renderer, "_render_solution_page"):
                        with patch.object(self.renderer, "_render_outro_page"):
                            with patch("src.infrastructure.pdf_renderer.canvas.Canvas") as mock_canvas_class:
                                mock_canvas = MagicMock()
                                mock_canvas_class.return_value = mock_canvas

                                self.renderer.render_book(book, output_path)

                                self.renderer._render_cover.assert_called_once()

    def test_render_book_with_contents_page(self) -> None:
        """При include_contents_page=True должна рендериться страница contents."""
        book = self._create_test_book()
        self.config.include_contents_page = True
        output_path = MagicMock()

        with patch.object(self.renderer, "_render_cover"):
            with patch.object(self.renderer, "_render_contents_page") as mock_contents:
                with patch.object(self.renderer, "_render_intro_page"):
                    with patch.object(self.renderer, "_render_maze_page"):
                        with patch.object(self.renderer, "_render_solution_page"):
                            with patch.object(self.renderer, "_render_outro_page"):
                                with patch("src.infrastructure.pdf_renderer.canvas.Canvas") as mock_canvas_class:
                                    mock_canvas = MagicMock()
                                    mock_canvas_class.return_value = mock_canvas

                                    self.renderer.render_book(book, output_path)

                                    mock_contents.assert_called_once()

    def test_render_book_without_contents_page(self) -> None:
        """При include_contents_page=False страница contents не должна рендериться."""
        book = self._create_test_book()
        self.config.include_contents_page = False
        output_path = MagicMock()

        with patch.object(self.renderer, "_render_cover"):
            with patch.object(self.renderer, "_render_contents_page") as mock_contents:
                with patch.object(self.renderer, "_render_intro_page"):
                    with patch.object(self.renderer, "_render_maze_page"):
                        with patch.object(self.renderer, "_render_solution_page"):
                            with patch.object(self.renderer, "_render_outro_page"):
                                with patch("src.infrastructure.pdf_renderer.canvas.Canvas") as mock_canvas_class:
                                    mock_canvas = MagicMock()
                                    mock_canvas_class.return_value = mock_canvas

                                    self.renderer.render_book(book, output_path)

                                    mock_contents.assert_not_called()

    def _create_test_book(self) -> Book:
        """Создаёт тестовый объект Book."""
        from src.domain.models import PagePrompt

        theme = Theme(
            book_title="Test Theme",
            book_description="Test description",
            marketplace_title="Marketplace Title",
            marketplace_description="Marketplace description",
            page_prompts=[
                PagePrompt(task="Task 1", heroes=["hero1"]),
                PagePrompt(task="Task 2", heroes=["hero2"]),
            ],
            image_keywords=[["key1", "key2"], ["key3", "key4"]],
        )

        maze1 = Maze(
            grid=[[1 for _ in range(10)] for _ in range(8)],
            width=10,
            height=8,
            start=(0, 0),
            end=(9, 7),
            difficulty=Difficulty.MEDIUM,
            shape=MazeShape.RECTANGULAR,
            solution_path=[(0, 0), (9, 7)],
            walls=[[[True, True, True, True] for _ in range(10)] for _ in range(8)],
        )

        maze2 = Maze(
            grid=[[1 for _ in range(10)] for _ in range(8)],
            width=10,
            height=8,
            start=(0, 0),
            end=(9, 7),
            difficulty=Difficulty.MEDIUM,
            shape=MazeShape.RECTANGULAR,
            solution_path=[(0, 0), (9, 7)],
            walls=[[[True, True, True, True] for _ in range(10)] for _ in range(8)],
        )

        page1 = BookPage(
            page_number=1,
            maze=maze1,
            title="Page 1",
            prompt="Task 1",
            is_solution=False,
        )

        page2 = BookPage(
            page_number=2,
            maze=maze2,
            title="Page 2",
            prompt="Task 2",
            is_solution=False,
        )

        return Book(
            id=1,
            theme=theme,
            pages=[page1, page2],
            output_dir="/tmp/test",
            config=self.config,
        )


if __name__ == "__main__":
    unittest.main()
