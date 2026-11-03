"""Unit-тесты для локализации."""


from maze_book_generator.localization import BookTexts


class TestBookTexts:
    """Проверяет локализацию текстов книги."""

    def test_english_initialization(self) -> None:
        """Инициализация с английским языком."""
        texts = BookTexts("en")
        assert texts.get("subtitle") == "Maze Book"

    def test_russian_initialization(self) -> None:
        """Инициализация с русским языком."""
        texts = BookTexts("ru")
        assert texts.get("subtitle") == "Книга лабиринтов"

    def test_get_simple_key(self) -> None:
        """Получение простой строки по ключу."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        assert en_texts.get("start_label") == "START"
        assert ru_texts.get("start_label") == "СТАРТ"

    def test_format_with_one_parameter(self) -> None:
        """Форматирование с одним параметром."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        assert en_texts.format("cover_age", age="5-8") == "Ages 5-8"
        assert ru_texts.format("cover_age", age="5-8") == "Возраст 5-8"

    def test_format_with_count_parameter(self) -> None:
        """Форматирование с параметром count."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        assert en_texts.format("cover_mazes", count=10) == "10 Mazes"
        assert ru_texts.format("cover_mazes", count=10) == "10 лабиринтов"

    def test_format_with_multiple_parameters(self) -> None:
        """Форматирование с несколькими параметрами."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        assert en_texts.format("outro_heading_personal", name="Alex") == "Great work, Alex!"
        assert ru_texts.format("outro_heading_personal", name="Алекс") == "Отличная работа, Алекс!"

class TestBookTextsSections:
    """Набор тестов."""


    def test_cover_texts_english(self) -> None:
        """Проверка текстов обложки для английского."""
        texts = BookTexts("en")

        assert texts.get("subtitle") == "Maze Book"
        assert texts.get("cover_printable") == "Printable PDF"
        assert texts.get("cover_language") == "English"
        assert texts.format("cover_mazes", count=5) == "5 Mazes"

    def test_cover_texts_russian(self) -> None:
        """Проверка текстов обложки для русского."""
        texts = BookTexts("ru")

        assert texts.get("subtitle") == "Книга лабиринтов"
        assert texts.get("cover_printable") == "PDF для печати"
        assert texts.get("cover_language") == "Русский"
        assert texts.format("cover_mazes", count=5) == "5 лабиринтов"

    def test_contents_texts_english(self) -> None:
        """Проверка текстов страницы contents для английского."""
        texts = BookTexts("en")

        assert texts.get("contents_heading") == "What's Inside"
        assert texts.format("contents_theme", value="Forest") == "Theme: Forest"
        assert texts.format("contents_mazes", count=8) == "Mazes: 8"
        assert texts.get("contents_answers") == "Answers included"

    def test_contents_texts_russian(self) -> None:
        """Проверка текстов страницы contents для русского."""
        texts = BookTexts("ru")

        assert texts.get("contents_heading") == "Что внутри"
        assert texts.format("contents_theme", value="Лес") == "Тема: Лес"
        assert texts.format("contents_mazes", count=8) == "Лабиринтов: 8"
        assert texts.get("contents_answers") == "Ответы включены"

    def test_maze_texts_english(self) -> None:
        """Проверка текстов страницы с лабиринтом для английского."""
        texts = BookTexts("en")

        assert texts.format("maze_title", n=1) == "Maze 1"
        assert texts.get("answer_key_prompt") == "Answer Key"
        assert texts.get("start_label") == "START"
        assert texts.get("finish_label") == "FINISH"

    def test_maze_texts_russian(self) -> None:
        """Проверка текстов страницы с лабиринтом для русского."""
        texts = BookTexts("ru")

        assert texts.format("maze_title", n=1) == "Лабиринт 1"
        assert texts.get("answer_key_prompt") == "Ответ"
        assert texts.get("start_label") == "СТАРТ"
        assert texts.get("finish_label") == "ФИНИШ"

    def test_difficulty_texts_english(self) -> None:
        """Проверка текстов сложности для английского."""
        texts = BookTexts("en")

        assert texts.get("difficulty_easy") == "Easy"
        assert texts.get("difficulty_medium") == "Medium"
        assert texts.get("difficulty_hard") == "Hard"
        assert texts.format("difficulty_caption", value="Medium") == "Level: Medium"

    def test_difficulty_texts_russian(self) -> None:
        """Проверка текстов сложности для русского."""
        texts = BookTexts("ru")

        assert texts.get("difficulty_easy") == "Легкий"
        assert texts.get("difficulty_medium") == "Средний"
        assert texts.get("difficulty_hard") == "Сложный"
        assert texts.format("difficulty_caption", value="Средний") == "Уровень: Средний"

class TestBookTextsIntroOutro:
    """Набор тестов."""


    def test_intro_texts_english(self) -> None:
        """Проверка текстов intro-страницы для английского."""
        texts = BookTexts("en")

        assert texts.get("intro_heading") == "Welcome to Your Maze Adventure!"
        assert "Find the START marker" in texts.get("intro_body")
        assert texts.get("intro_legend_start") == "START"
        assert texts.get("intro_legend_finish") == "FINISH"

    def test_intro_texts_russian(self) -> None:
        """Проверка текстов intro-страницы для русского."""
        texts = BookTexts("ru")

        assert texts.get("intro_heading") == "Добро пожаловать в мир лабиринтов!"
        assert "Найди маркер СТАРТ" in texts.get("intro_body")
        assert texts.get("intro_legend_start") == "СТАРТ"
        assert texts.get("intro_legend_finish") == "ФИНИШ"

    def test_outro_texts_english(self) -> None:
        """Проверка текстов outro-страницы для английского."""
        texts = BookTexts("en")

        assert texts.get("outro_heading") == "Amazing Job, Explorer!"
        assert "You completed all the mazes" in texts.get("outro_body")
        assert texts.format("outro_signature", book_title="Maze Adventure") == "With love, Maze Adventure"

    def test_outro_texts_russian(self) -> None:
        """Проверка текстов outro-страницы для русского."""
        texts = BookTexts("ru")

        assert texts.get("outro_heading") == "Отличная работа, исследователь!"
        assert "Ты прошёл все лабиринты" in texts.get("outro_body")
        assert texts.format("outro_signature", book_title="Приключение") == "С любовью, Приключение"

    def test_fallback_texts_english(self) -> None:
        """Проверка fallback-текстов для английского."""
        texts = BookTexts("en")

        assert texts.get("fallback_book_title") == "Maze Adventure"
        assert texts.get("fallback_book_description") == "An exciting maze adventure."
        assert texts.format("fallback_maze_task_n", n=5) == "Find the path through maze #5"

    def test_fallback_texts_russian(self) -> None:
        """Проверка fallback-текстов для русского."""
        texts = BookTexts("ru")

        assert texts.get("fallback_book_title") == "Приключение в лабиринте"
        assert texts.get("fallback_book_description") == "Захватывающее путешествие по лабиринтам."
        assert texts.format("fallback_maze_task_n", n=5) == "Найди путь через лабиринт #5"
