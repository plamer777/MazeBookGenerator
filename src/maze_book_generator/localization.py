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

    def format(self, key: str, **kwargs: str | int) -> str:
        """Возвращает локализованную строку с подстановкой параметров."""
        return self._t[key].format(**kwargs)


_TEXTS: dict[str, dict[str, str]] = {
    "en": {
        # Обложка
        "subtitle": "Maze Book",
        "cover_printable": "Printable PDF",
        "cover_language": "English",
        "cover_age": "Ages {age}",
        "cover_mazes": "{count} Mazes",
        "cover_for_child": "For {name}",
        "cover_child_age": "Age {age}",
        # Страница contents
        "contents_heading": "What's Inside",
        "contents_theme": "Theme: {value}",
        "contents_language": "Language: {value}",
        "contents_mazes": "Mazes: {count}",
        "contents_answers": "Answers included",
        "contents_printable": "Format: Printable PDF",
        "contents_difficulty": "Level: {value}",
        "contents_child": "For: {name}",
        "contents_child_age": "Child age: {age}",
        # Страница с лабиринтом
        "maze_title": "Maze {n}",
        "answer_key_prompt": "Answer Key",
        "answer_page_suffix": "Answer",
        "difficulty_caption": "Level: {value}",
        "difficulty_easy": "Easy",
        "difficulty_medium": "Medium",
        "difficulty_hard": "Hard",
        "start_label": "START",
        "finish_label": "FINISH",
        # Intro-страница
        "intro_heading": "Welcome to Your Maze Adventure!",
        "intro_body": (
            "Hi there, brave explorer!\n"
            "\n"
            "Here's how to play:\n"
            "• Find the START marker (green triangle).\n"
            "• Draw a path to the FINISH marker (red arrow).\n"
            "• Stay inside the lines — no cutting through walls!\n"
            "• Have fun and don't give up!\n"
            "\n"
            "Each maze is a new adventure.\n"
            "Are you ready? Let's go!"
        ),
        "intro_legend_title": "Legend",
        "intro_legend_start": "START",
        "intro_legend_finish": "FINISH",
        # Outro-страница
        "outro_heading": "Amazing Job, Explorer!",
        "outro_heading_personal": "Great work, {name}!",
        "outro_body": (
            "You completed all the mazes!\n"
            "Great work staying on the path.\n"
            "Keep exploring and having fun.\n"
            "\n"
            "See you on your next adventure!"
        ),
        "outro_signature": "With love, {book_title}",
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
        "cover_printable": "PDF для печати",
        "cover_language": "Русский",
        "cover_age": "Возраст {age}",
        "cover_mazes": "{count} лабиринтов",
        "cover_for_child": "Для {name}",
        "cover_child_age": "Возраст {age}",
        # Страница contents
        "contents_heading": "Что внутри",
        "contents_theme": "Тема: {value}",
        "contents_language": "Язык: {value}",
        "contents_mazes": "Лабиринтов: {count}",
        "contents_answers": "Ответы включены",
        "contents_printable": "Формат: PDF для печати",
        "contents_difficulty": "Уровень: {value}",
        "contents_child": "Для: {name}",
        "contents_child_age": "Возраст ребенка: {age}",
        # Страница с лабиринтом
        "maze_title": "Лабиринт {n}",
        "answer_key_prompt": "Ответ",
        "answer_page_suffix": "Ответ",
        "difficulty_caption": "Уровень: {value}",
        "difficulty_easy": "Легкий",
        "difficulty_medium": "Средний",
        "difficulty_hard": "Сложный",
        "start_label": "СТАРТ",
        "finish_label": "ФИНИШ",
        # Intro-страница
        "intro_heading": "Добро пожаловать в мир лабиринтов!",
        "intro_body": (
            "Привет, отважный исследователь!\n"
            "\n"
            "Как играть:\n"
            "• Найди маркер СТАРТ (зелёный треугольник).\n"
            "• Проведи путь до маркера ФИНИШ (красная стрелка).\n"
            "• Не выходи за линии — сквозь стены нельзя!\n"
            "• Получай удовольствие и не сдавайся!\n"
            "\n"
            "Каждый лабиринт — новое приключение.\n"
            "Готов? Вперёд!"
        ),
        "intro_legend_title": "Легенда",
        "intro_legend_start": "СТАРТ",
        "intro_legend_finish": "ФИНИШ",
        # Outro-страница
        "outro_heading": "Отличная работа, исследователь!",
        "outro_heading_personal": "Отличная работа, {name}!",
        "outro_body": (
            "Ты прошёл все лабиринты!\n"
            "Отличная работа — ты не сдался!\n"
            "Продолжай исследовать и получать удовольствие.\n"
            "\n"
            "До новых приключений!"
        ),
        "outro_signature": "С любовью, {book_title}",
        # Fallback-значения при ошибке парсинга OpenAI
        "fallback_book_title": "Приключение в лабиринте",
        "fallback_book_description": "Захватывающее путешествие по лабиринтам.",
        "fallback_maze_task": "Найди путь через лабиринт",
        "fallback_maze_task_n": "Найди путь через лабиринт #{n}",
        "fallback_keywords": "maze,adventure",
    },
}
