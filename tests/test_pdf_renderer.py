"""Unit-тесты для PDFRenderer и функций pdf-пакета."""

from unittest.mock import MagicMock, patch

from maze_book_generator.domain.models import Book, BookConfig, BookPage, Difficulty, Maze, MazeShape, Theme
from maze_book_generator.infrastructure.pdf import PDFRenderer, cover, text


class TestPDFRenderer:
    """Проверяет логику PDF рендерера с моками внешних зависимостей."""

    def setup_method(self) -> None:
        """Инициализация рендерера с тестовой конфигурацией."""
        self.config = BookConfig(language="en")
        self.renderer = PDFRenderer(language="en", book_config=self.config)

    def test_initialization(self) -> None:
        """Инициализация рендерера должна устанавливать корректные параметры."""
        ctx = self.renderer.ctx
        assert ctx.page_width is not None
        assert ctx.page_height is not None
        assert ctx.margin is not None
        assert ctx.cell_size is not None

    def test_book_title_from_config(self) -> None:
        """Название книги должно браться из конфигурации, если задано."""
        book = _create_test_book()
        self.config.title = "Custom Title"

        title = cover.book_title(self.renderer.ctx, book)
        assert title == "Custom Title"

    def test_book_title_from_theme(self) -> None:
        """Название книги должно браться из темы, если не задано в конфигурации."""
        book = _create_test_book()
        self.config.title = None

        title = cover.book_title(self.renderer.ctx, book)
        assert title == "Test Theme"

    def test_book_subtitle_from_config(self) -> None:
        """Подзаголовок должен браться из конфигурации, если задан."""
        self.config.subtitle = "Custom Subtitle"

        subtitle = cover.book_subtitle(self.renderer.ctx)
        assert subtitle == "Custom Subtitle"

    def test_book_maze_count_from_config(self) -> None:
        """Количество лабиринтов должно браться из конфигурации, если задано."""
        book = _create_test_book()
        self.config.maze_count = 15

        count = cover.book_maze_count(self.renderer.ctx, book)
        assert count == 15

    def test_book_maze_count_from_book(self) -> None:
        """Количество лабиринтов должно считаться из страниц, если не задано в конфигурации."""
        book = _create_test_book()
        self.config.maze_count = None

        count = cover.book_maze_count(self.renderer.ctx, book)
        assert count == 2  # 2 maze pages

    def test_book_age_label_from_config(self) -> None:
        """Возрастная метка должна браться из конфигурации."""
        self.config.age_range = "5-8 years"

        label = cover.book_age_label(self.renderer.ctx)
        assert label is not None
        assert "5-8" in label

    def test_book_age_label_from_target_age(self) -> None:
        """Возрастная метка должна браться из target_age, если age_range не задан."""
        self.config.age_range = None
        self.config.target_age = "6-9 years"

        label = cover.book_age_label(self.renderer.ctx)
        assert label is not None
        assert "6-9" in label

    def test_book_age_label_none(self) -> None:
        """Возрастная метка должна быть None, если не задано."""
        self.config.age_range = None
        self.config.target_age = None

        label = cover.book_age_label(self.renderer.ctx)
        assert label is None

class TestCoverAndText:
    """Набор тестов."""

    def setup_method(self) -> None:
        """Инициализация рендерера с тестовой конфигурацией."""
        self.config = BookConfig(language="en")
        self.renderer = PDFRenderer(language="en", book_config=self.config)


    def test_cover_mazes_label_english(self) -> None:
        """Метка количества лабиринтов должна быть локализована для английского."""
        self.config.language = "en"
        renderer = PDFRenderer(language="en", book_config=self.config)

        label = cover.cover_mazes_label(renderer.ctx, 5)
        assert label == "5 Mazes"

    def test_cover_mazes_label_russian(self) -> None:
        """Метка количества лабиринтов должна быть локализована для русского."""
        self.config.language = "ru"
        renderer = PDFRenderer(language="ru", book_config=self.config)

        label = cover.cover_mazes_label(renderer.ctx, 5)
        assert label == "5 лабиринтов"

    def test_cover_palette_deterministic(self) -> None:
        """Палитра должна быть детерминированной для одного и того же seed."""
        palette1 = cover.cover_palette("Test")
        palette2 = cover.cover_palette("Test")

        assert palette1 == palette2

    def test_cover_palette_different_seeds(self) -> None:
        """Разные seed должны давать разные палитры."""
        palette1 = cover.cover_palette("Seed1")
        palette2 = cover.cover_palette("Seed2")

        # Палитры могут совпадать случайно, но с высокой вероятностью разные
        # Проверяем, что хотя бы один цвет отличается
        assert palette1 != palette2

    def test_wrap_text_to_width_short_text(self) -> None:
        """Короткий текст не должен переноситься."""
        mock_canvas = MagicMock()
        mock_canvas.stringWidth.return_value = 50  # ширина меньше max_width

        lines = text.wrap_text_to_width(mock_canvas, "Short text", "font", 12, 100)
        assert len(lines) == 1
        assert lines[0] == "Short text"

    def test_wrap_text_to_width_long_text(self) -> None:
        """Длинный текст должен переноситься по словам."""
        mock_canvas = MagicMock()
        # Первое слово влезает, второе - нет
        def string_width_side_effect(text, _font, _size):
            if text == "Hello":
                return 40
            if text == "Hello world":
                return 120
            if text == "world":
                return 50
            return 0

        mock_canvas.stringWidth.side_effect = string_width_side_effect

        lines = text.wrap_text_to_width(mock_canvas, "Hello world", "font", 12, 100)
        assert len(lines) == 2
        assert lines[0] == "Hello"
        assert lines[1] == "world"

    def test_split_long_word(self) -> None:
        """Длинное слово должно разбиваться на части."""
        mock_canvas = MagicMock()

        # Каждая буква занимает 10 единиц
        def string_width_side_effect(text, _font, _size):
            return len(text) * 10

        mock_canvas.stringWidth.side_effect = string_width_side_effect

        chunks = text.split_long_word(mock_canvas, "VeryLongWord", "font", 12, 20)
        assert len(chunks) > 1
        # Проверяем, что общая длина соответствует исходному слову
        joined = "".join(chunks)
        assert joined == "VeryLongWord"

    def test_fit_cover_title_layout_fits_in_one_line(self) -> None:
        """Заголовок, который влезает в одну строку, должен быть без переносов."""
        mock_canvas = MagicMock()
        mock_canvas.stringWidth.return_value = 100  # влезает в max_width

        font_size, lines = cover.fit_cover_title_layout(self.renderer.ctx, mock_canvas, "Short Title", 200)
        assert len(lines) == 1
        assert lines[0] == "Short Title"
        assert font_size > 18

    def test_fit_cover_title_layout_wraps_to_multiple_lines(self) -> None:
        """Длинный заголовок должен переноситься на несколько строк."""
        mock_canvas = MagicMock()
        # Каждое слово занимает много места
        def string_width_side_effect(text, _font, _size):
            return len(text) * 30

        mock_canvas.stringWidth.side_effect = string_width_side_effect

        _font_size, lines = cover.fit_cover_title_layout(
            self.renderer.ctx, mock_canvas, "Very Long Title Here", 100,
        )
        assert len(lines) > 1

    def test_fit_cover_title_layout_reduces_font_size(self) -> None:
        """Если текст не влезает, размер шрифта должен уменьшаться."""
        mock_canvas = MagicMock()
        # Большой размер шрифта даёт большую ширину
        def string_width_side_effect(text, _font, size):
            return len(text) * size * 2

        mock_canvas.stringWidth.side_effect = string_width_side_effect

        font_size, _lines = cover.fit_cover_title_layout(
            self.renderer.ctx, mock_canvas, "Very Long Title", 100,
        )
        assert font_size < 34  # начальный размер

class TestRenderBook:
    """Набор тестов."""

    def setup_method(self) -> None:
        """Инициализация рендерера с тестовой конфигурацией."""
        self.config = BookConfig(language="en")
        self.renderer = PDFRenderer(language="en", book_config=self.config)


    def test_render_book_calls_render_cover(self) -> None:
        """Рендер книги должен вызывать рендер обложки."""
        book = _create_test_book()
        output_path = MagicMock()

        with (
            patch("maze_book_generator.infrastructure.pdf.cover.render_cover") as mock_cover,
            patch("maze_book_generator.infrastructure.pdf.front_pages.render_intro_page"),
            patch("maze_book_generator.infrastructure.pdf.maze_pages.render_maze_page"),
            patch("maze_book_generator.infrastructure.pdf.maze_pages.render_solution_page"),
            patch("maze_book_generator.infrastructure.pdf.outro.render_outro_page"),
            patch("maze_book_generator.infrastructure.pdf.renderer.canvas.Canvas") as mock_canvas_class,
        ):
            mock_canvas = MagicMock()
            mock_canvas_class.return_value = mock_canvas

            self.renderer.render_book(book, output_path)

            mock_cover.assert_called_once()

    def test_render_book_with_contents_page(self) -> None:
        """При include_contents_page=True должна рендериться страница contents."""
        book = _create_test_book()
        self.config.include_contents_page = True
        output_path = MagicMock()

        with (
            patch("maze_book_generator.infrastructure.pdf.cover.render_cover"),
            patch("maze_book_generator.infrastructure.pdf.front_pages.render_contents_page") as mock_contents,
            patch("maze_book_generator.infrastructure.pdf.front_pages.render_intro_page"),
            patch("maze_book_generator.infrastructure.pdf.maze_pages.render_maze_page"),
            patch("maze_book_generator.infrastructure.pdf.maze_pages.render_solution_page"),
            patch("maze_book_generator.infrastructure.pdf.outro.render_outro_page"),
            patch("maze_book_generator.infrastructure.pdf.renderer.canvas.Canvas") as mock_canvas_class,
        ):
            mock_canvas = MagicMock()
            mock_canvas_class.return_value = mock_canvas

            self.renderer.render_book(book, output_path)

            mock_contents.assert_called_once()

    def test_render_book_without_contents_page(self) -> None:
        """При include_contents_page=False страница contents не должна рендериться."""
        book = _create_test_book()
        self.config.include_contents_page = False
        output_path = MagicMock()

        with (
            patch("maze_book_generator.infrastructure.pdf.cover.render_cover"),
            patch("maze_book_generator.infrastructure.pdf.front_pages.render_contents_page") as mock_contents,
            patch("maze_book_generator.infrastructure.pdf.front_pages.render_intro_page"),
            patch("maze_book_generator.infrastructure.pdf.maze_pages.render_maze_page"),
            patch("maze_book_generator.infrastructure.pdf.maze_pages.render_solution_page"),
            patch("maze_book_generator.infrastructure.pdf.outro.render_outro_page"),
            patch("maze_book_generator.infrastructure.pdf.renderer.canvas.Canvas") as mock_canvas_class,
        ):
            mock_canvas = MagicMock()
            mock_canvas_class.return_value = mock_canvas

            self.renderer.render_book(book, output_path)

            mock_contents.assert_not_called()


def _create_test_book() -> Book:
    """Создаёт тестовый объект Book."""
    book_config = BookConfig(language="en")
    from maze_book_generator.domain.models import PagePrompt

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
        output_dir="test_output",
        config=book_config,
    )
