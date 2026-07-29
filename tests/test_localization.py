"""Unit-тесты для локализации."""

import unittest

from src.localization import BookTexts, Language


class TestBookTexts(unittest.TestCase):
    """Проверяет локализацию текстов книги."""

    def test_english_initialization(self) -> None:
        """Инициализация с английским языком."""
        texts = BookTexts("en")
        self.assertEqual(texts.get("subtitle"), "Maze Book")

    def test_russian_initialization(self) -> None:
        """Инициализация с русским языком."""
        texts = BookTexts("ru")
        self.assertEqual(texts.get("subtitle"), "Книга лабиринтов")

    def test_get_simple_key(self) -> None:
        """Получение простой строки по ключу."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        self.assertEqual(en_texts.get("start_label"), "START")
        self.assertEqual(ru_texts.get("start_label"), "СТАРТ")

    def test_format_with_one_parameter(self) -> None:
        """Форматирование с одним параметром."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        self.assertEqual(en_texts.format("cover_age", age="5-8"), "Ages 5-8")
        self.assertEqual(ru_texts.format("cover_age", age="5-8"), "Возраст 5-8")

    def test_format_with_count_parameter(self) -> None:
        """Форматирование с параметром count."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        self.assertEqual(en_texts.format("cover_mazes", count=10), "10 Mazes")
        self.assertEqual(ru_texts.format("cover_mazes", count=10), "10 лабиринтов")

    def test_format_with_multiple_parameters(self) -> None:
        """Форматирование с несколькими параметрами."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        self.assertEqual(en_texts.format("outro_heading_personal", name="Alex"), "Great work, Alex!")
        self.assertEqual(ru_texts.format("outro_heading_personal", name="Алекс"), "Отличная работа, Алекс!")

    def test_cover_texts_english(self) -> None:
        """Проверка текстов обложки для английского."""
        texts = BookTexts("en")

        self.assertEqual(texts.get("subtitle"), "Maze Book")
        self.assertEqual(texts.get("cover_printable"), "Printable PDF")
        self.assertEqual(texts.get("cover_language"), "English")
        self.assertEqual(texts.format("cover_mazes", count=5), "5 Mazes")

    def test_cover_texts_russian(self) -> None:
        """Проверка текстов обложки для русского."""
        texts = BookTexts("ru")

        self.assertEqual(texts.get("subtitle"), "Книга лабиринтов")
        self.assertEqual(texts.get("cover_printable"), "PDF для печати")
        self.assertEqual(texts.get("cover_language"), "Русский")
        self.assertEqual(texts.format("cover_mazes", count=5), "5 лабиринтов")

    def test_contents_texts_english(self) -> None:
        """Проверка текстов страницы contents для английского."""
        texts = BookTexts("en")

        self.assertEqual(texts.get("contents_heading"), "What's Inside")
        self.assertEqual(texts.format("contents_theme", value="Forest"), "Theme: Forest")
        self.assertEqual(texts.format("contents_mazes", count=8), "Mazes: 8")
        self.assertEqual(texts.get("contents_answers"), "Answers included")

    def test_contents_texts_russian(self) -> None:
        """Проверка текстов страницы contents для русского."""
        texts = BookTexts("ru")

        self.assertEqual(texts.get("contents_heading"), "Что внутри")
        self.assertEqual(texts.format("contents_theme", value="Лес"), "Тема: Лес")
        self.assertEqual(texts.format("contents_mazes", count=8), "Лабиринтов: 8")
        self.assertEqual(texts.get("contents_answers"), "Ответы включены")

    def test_maze_texts_english(self) -> None:
        """Проверка текстов страницы с лабиринтом для английского."""
        texts = BookTexts("en")

        self.assertEqual(texts.format("maze_title", n=1), "Maze 1")
        self.assertEqual(texts.get("answer_key_prompt"), "Answer Key")
        self.assertEqual(texts.get("start_label"), "START")
        self.assertEqual(texts.get("finish_label"), "FINISH")

    def test_maze_texts_russian(self) -> None:
        """Проверка текстов страницы с лабиринтом для русского."""
        texts = BookTexts("ru")

        self.assertEqual(texts.format("maze_title", n=1), "Лабиринт 1")
        self.assertEqual(texts.get("answer_key_prompt"), "Ответ")
        self.assertEqual(texts.get("start_label"), "СТАРТ")
        self.assertEqual(texts.get("finish_label"), "ФИНИШ")

    def test_difficulty_texts_english(self) -> None:
        """Проверка текстов сложности для английского."""
        texts = BookTexts("en")

        self.assertEqual(texts.get("difficulty_easy"), "Easy")
        self.assertEqual(texts.get("difficulty_medium"), "Medium")
        self.assertEqual(texts.get("difficulty_hard"), "Hard")
        self.assertEqual(texts.format("difficulty_caption", value="Medium"), "Level: Medium")

    def test_difficulty_texts_russian(self) -> None:
        """Проверка текстов сложности для русского."""
        texts = BookTexts("ru")

        self.assertEqual(texts.get("difficulty_easy"), "Легкий")
        self.assertEqual(texts.get("difficulty_medium"), "Средний")
        self.assertEqual(texts.get("difficulty_hard"), "Сложный")
        self.assertEqual(texts.format("difficulty_caption", value="Средний"), "Уровень: Средний")

    def test_intro_texts_english(self) -> None:
        """Проверка текстов intro-страницы для английского."""
        texts = BookTexts("en")

        self.assertEqual(texts.get("intro_heading"), "Welcome to Your Maze Adventure!")
        self.assertIn("Find the START marker", texts.get("intro_body"))
        self.assertEqual(texts.get("intro_legend_start"), "START")
        self.assertEqual(texts.get("intro_legend_finish"), "FINISH")

    def test_intro_texts_russian(self) -> None:
        """Проверка текстов intro-страницы для русского."""
        texts = BookTexts("ru")

        self.assertEqual(texts.get("intro_heading"), "Добро пожаловать в мир лабиринтов!")
        self.assertIn("Найди маркер СТАРТ", texts.get("intro_body"))
        self.assertEqual(texts.get("intro_legend_start"), "СТАРТ")
        self.assertEqual(texts.get("intro_legend_finish"), "ФИНИШ")

    def test_outro_texts_english(self) -> None:
        """Проверка текстов outro-страницы для английского."""
        texts = BookTexts("en")

        self.assertEqual(texts.get("outro_heading"), "Amazing Job, Explorer!")
        self.assertIn("You completed all the mazes", texts.get("outro_body"))
        self.assertEqual(texts.format("outro_signature", book_title="Maze Adventure"), "With love, Maze Adventure")

    def test_outro_texts_russian(self) -> None:
        """Проверка текстов outro-страницы для русского."""
        texts = BookTexts("ru")

        self.assertEqual(texts.get("outro_heading"), "Отличная работа, исследователь!")
        self.assertIn("Ты прошёл все лабиринты", texts.get("outro_body"))
        self.assertEqual(texts.format("outro_signature", book_title="Приключение"), "С любовью, Приключение")

    def test_fallback_texts_english(self) -> None:
        """Проверка fallback-текстов для английского."""
        texts = BookTexts("en")

        self.assertEqual(texts.get("fallback_book_title"), "Maze Adventure")
        self.assertEqual(texts.get("fallback_book_description"), "An exciting maze adventure.")
        self.assertEqual(texts.format("fallback_maze_task_n", n=5), "Find the path through maze #5")

    def test_fallback_texts_russian(self) -> None:
        """Проверка fallback-текстов для русского."""
        texts = BookTexts("ru")

        self.assertEqual(texts.get("fallback_book_title"), "Приключение в лабиринте")
        self.assertEqual(texts.get("fallback_book_description"), "Захватывающее путешествие по лабиринтам.")
        self.assertEqual(texts.format("fallback_maze_task_n", n=5), "Найди путь через лабиринт #5")


if __name__ == "__main__":
    unittest.main()
