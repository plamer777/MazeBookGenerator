"""Локализация текстов для поддержки English / Russian."""

from typing import Literal

Language = Literal["en", "ru"]


class BookTexts:
    """Контейнер локализованных строк для рендеринга книги."""

    def __init__(self, language: Language) -> None:
        """Инициализация набора строк по выбранному языку."""
        self._t = _TEXTS[language]

    def get(self, key: str) -> str:
        """Возвращает локализованную строку по ключу."""
        return self._t[key]


_TEXTS: dict[str, dict[str, str]] = {
    "en": {
        # Обложка
        "subtitle": "Maze Book",
        # Страница с лабиринтом
        "maze_title": "Maze {n}",
        "answer_key_prompt": "Answer Key",
        "answer_page_suffix": "Answer",
        # Intro-страница
        "intro_heading": "Welcome to Your Maze Adventure!",
        "intro_body": (
            "Hi there, brave explorer!\n"
            "\n"
            "Here's how to play:\n"
            "• Find the START point (green triangle).\n"
            "• Draw a path to the END point (red arrow).\n"
            "• Stay inside the lines — no cutting through walls!\n"
            "• Have fun and don't give up!\n"
            "\n"
            "Each maze is a new adventure.\n"
            "Are you ready? Let's go!"
        ),
        # Outro-страница
        "outro_heading": "Amazing Job, Explorer!",
        "outro_body": (
            "You completed all the mazes!\n"
            "Great work staying on the path.\n"
            "Keep exploring and having fun.\n"
            "\n"
            "See you on your next adventure!"
        ),
        "outro_signature": "With love, your Maze Book \u2665",
        # Fallback-значения при ошибке парсинга OpenAI
        "fallback_book_title": "Maze Adventure",
        "fallback_book_description": "An exciting maze adventure.",
        "fallback_maze_task": "Find the path through the maze",
        "fallback_maze_task_n": "Find the path through maze #{n}",
        "fallback_keywords": "maze,adventure",
    },
    "ru": {
        # Обложка
        "subtitle": "Книга лабиринтов",
        # Страница с лабиринтом
        "maze_title": "Лабиринт {n}",
        "answer_key_prompt": "Ответ",
        "answer_page_suffix": "Ответ",
        # Intro-страница
        "intro_heading": "Добро пожаловать в мир лабиринтов!",
        "intro_body": (
            "Привет, отважный исследователь!\n"
            "\n"
            "Как играть:\n"
            "• Найди точку СТАРТ (зелёный треугольник).\n"
            "• Проведи путь до точки ФИНИШ (красная стрелка).\n"
            "• Не выходи за линии — сквозь стены нельзя!\n"
            "• Получай удовольствие и не сдавайся!\n"
            "\n"
            "Каждый лабиринт — новое приключение.\n"
            "Готов? Вперёд!"
        ),
        # Outro-страница
        "outro_heading": "Молодец, исследователь!",
        "outro_body": (
            "Ты прошёл все лабиринты!\n"
            "Отличная работа — ты не сдался!\n"
            "Продолжай исследовать и получать удовольствие.\n"
            "\n"
            "До новых приключений!"
        ),
        "outro_signature": "С любовью, твоя Книга лабиринтов ♥",
        # Fallback-значения при ошибке парсинга OpenAI
        "fallback_book_title": "Приключение в лабиринте",
        "fallback_book_description": "Захватывающее путешествие по лабиринтам.",
        "fallback_maze_task": "Найди путь через лабиринт",
        "fallback_maze_task_n": "Найди путь через лабиринт #{n}",
        "fallback_keywords": "maze,adventure",
    },
}
