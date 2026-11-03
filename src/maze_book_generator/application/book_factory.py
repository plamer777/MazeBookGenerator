"""Сборка книги: спецификация, страницы и стратегии сложности/формы."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from maze_book_generator.domain.maze import MazeGenerator
from maze_book_generator.domain.models import (
    BookConfig,
    BookPage,
    Difficulty,
    DifficultyMode,
    MazeShape,
    PagePrompt,
    Theme,
)
from maze_book_generator.localization import BookTexts, Language
from maze_book_generator.settings import (
    STORY_WAVE_AMPLITUDE,
    STORY_WAVE_TREND_SLOPE,
)


@dataclass(frozen=True)
class BookSpec:
    """Параметры генерации одной книги (все сценарии BookService)."""

    pages_per_book: int
    maze_size: tuple[int, int]
    difficulty_mode: DifficultyMode
    base_difficulty: Difficulty = Difficulty.MEDIUM
    language: Language = "en"
    book_config: BookConfig | None = None


def resolve_language(language: Language, config: BookConfig | None) -> Language:
    """Определяет итоговый язык: приоритет у BookConfig, параметр — fallback."""
    return config.language if config else language


def build_default_theme(
    title: str,
    language: Language,
    pages_per_book: int,
) -> Theme:
    """
    Собирает офлайн-тему без обращения к OpenAI.

    Задания и ключевые слова берутся из локализованных fallback-строк;
    маркетплейс-поля совпадают с названием и описанием книги.
    """
    texts = BookTexts(language)
    prompt_template = texts.get("fallback_maze_task_n")
    keywords = texts.get("fallback_keywords").split(",")
    return Theme(
        book_title=title,
        book_description=texts.get("fallback_book_description"),
        page_prompts=[
            PagePrompt(task=prompt_template.format(n=n), heroes=[])
            for n in range(1, pages_per_book + 1)
        ],
        image_keywords=[keywords for _ in range(pages_per_book)],
        marketplace_title=title,
        marketplace_description=texts.get("fallback_book_description"),
    )


def difficulty_label(difficulty: Difficulty, texts: BookTexts) -> str:
    """Возвращает локализованный читаемый уровень сложности."""
    if difficulty.level <= 2:
        return texts.get("difficulty_easy")
    if difficulty.level <= 4:
        return texts.get("difficulty_medium")
    return texts.get("difficulty_hard")


def page_difficulty(
    mode: DifficultyMode,
    page_num: int,
    total_pages: int,
    base_difficulty: Difficulty,
    rng: random.Random,
) -> Difficulty:
    """Реализует когнитивные стратегии распределения сложности по страницам."""
    # Безопасное приведение к строке для поддержки и Enum, и кастомных конфигураций
    mode_str = mode.name if hasattr(mode, "name") else str(mode)

    all_levels = [
        Difficulty.L1, Difficulty.L2, Difficulty.L3, Difficulty.L4,
        Difficulty.L5, Difficulty.L6, Difficulty.L7,
    ]

    if mode_str == "INCREMENTAL":
        progress = (page_num - 1) / max(total_pages - 1, 1)
        return all_levels[round(progress * (len(all_levels) - 1))]

    if mode_str == "RANDOM_RANGE":
        return rng.choice(all_levels)

    if mode_str == "KIDS_EASY":
        # Стратегия для малышей: строго самые простые и понятные структуры
        return rng.choice([Difficulty.L1, Difficulty.L2])

    if mode_str == "CHALLENGE_HARD":
        # Стратегия для продвинутых детей: только хардкор
        return rng.choice([Difficulty.L5, Difficulty.L6, Difficulty.L7])

    if mode_str == "STORY_WAVE":
        # Волнообразная нагрузка с общим восходящим трендом (предотвращает утомление)
        progress = (page_num - 1) / max(total_pages - 1, 1)
        base_idx = progress * STORY_WAVE_TREND_SLOPE
        wave_modifier = math.sin(page_num * STORY_WAVE_AMPLITUDE) * STORY_WAVE_AMPLITUDE
        index = max(0, min(6, round(base_idx + wave_modifier + STORY_WAVE_AMPLITUDE)))
        return all_levels[index]

    # FIXED и неизвестные режимы — базовая сложность
    return base_difficulty


def page_shape(
    page_num: int,
    total_pages: int,
    mode: DifficultyMode,
    rng: random.Random,
) -> MazeShape:
    """Подбирает форму лабиринта, соответствующую когнитивной нагрузке."""
    mode_str = mode.name if hasattr(mode, "name") else str(mode)

    if mode_str == "KIDS_EASY":
        # Для малышей убираем запутывающие сетки (круглые, треугольные, хаотичные).
        return rng.choice([MazeShape.RECTANGULAR, MazeShape.SQUARE, MazeShape.DIAMOND])

    if mode_str == "CHALLENGE_HARD":
        # Для экспертов сразу выкатываем сложные альтернативные топологии
        complex_shapes = [
            MazeShape.TRIANGULAR,
            MazeShape.CIRCULAR,
            MazeShape.CHAOTIC,
            MazeShape.RANDOM,
            MazeShape.DIAMOND,
            MazeShape.HEART,
        ]
        return complex_shapes[(page_num - 1) % len(complex_shapes)]

    if mode_str == "INCREMENTAL":
        return _incremental_shape(page_num, total_pages, rng)

    # Дефолтное классическое чередование для FIXED и RANDOM_RANGE
    shapes = [
        MazeShape.RECTANGULAR,
        MazeShape.SQUARE,
        MazeShape.TRIANGULAR,
        MazeShape.CIRCULAR,
        MazeShape.RANDOM,
        MazeShape.CHAOTIC,
        MazeShape.DIAMOND,
        MazeShape.HEART,
    ]
    return shapes[(page_num - 1) % len(shapes)]


def _incremental_shape(
    page_num: int, total_pages: int, rng: random.Random
) -> MazeShape:
    """Эволюция форм INCREMENTAL: от простых к сложным по мере пролистывания."""
    progress = (page_num - 1) / max(total_pages - 1, 1)
    if progress < 0.35:
        return rng.choice([MazeShape.RECTANGULAR, MazeShape.SQUARE, MazeShape.DIAMOND])
    if progress < 0.70:
        return rng.choice(
            [MazeShape.SQUARE, MazeShape.CIRCULAR, MazeShape.TRIANGULAR, MazeShape.DIAMOND]
        )
    return rng.choice(
        [
            MazeShape.CIRCULAR,
            MazeShape.TRIANGULAR,
            MazeShape.CHAOTIC,
            MazeShape.RANDOM,
            MazeShape.DIAMOND,
            MazeShape.HEART,
        ]
    )


def page_prompt(theme: Theme, index: int) -> str:
    """Получает текст задания для страницы из темы."""
    if index < len(theme.page_prompts):
        return theme.page_prompts[index].task
    return f"Find the path through maze {index + 1}"


def build_book_config(
    pages_per_book: int,
    language: Language,
    theme: Theme,
    base_difficulty: Difficulty,
    config: BookConfig | None,
) -> BookConfig:
    """Собирает итоговую конфигурацию книги с безопасными дефолтами."""
    effective_language = resolve_language(language, config)
    texts = BookTexts(effective_language)

    if config is None:
        return BookConfig(
            language=effective_language,
            title=theme.book_title,
            subtitle=texts.get("subtitle"),
            theme_name=theme.book_title,
            maze_count=pages_per_book,
            difficulty_label=difficulty_label(base_difficulty, texts),
        )

    return BookConfig(
        language=effective_language,
        title=config.title or theme.book_title,
        subtitle=config.subtitle or texts.get("subtitle"),
        theme_name=config.theme_name or theme.book_title,
        age_range=config.age_range,
        target_age=config.target_age,
        child_name=config.child_name,
        child_age=config.child_age,
        maze_count=config.maze_count or pages_per_book,
        include_contents_page=config.include_contents_page,
        show_start_finish_labels=config.show_start_finish_labels,
        generate_print_friendly_version=config.generate_print_friendly_version,
        difficulty_label=config.difficulty_label or difficulty_label(base_difficulty, texts),
    )


def build_pages(
    maze_generator: MazeGenerator,
    theme: Theme,
    spec: BookSpec,
    rng: random.Random,
    texts: BookTexts,
) -> list[BookPage]:
    """
    Собирает пары страниц (лабиринт + ответ) по спецификации книги.

    Сложность и форма каждой страницы вычисляются стратегиями
    page_difficulty/page_shape на основе difficulty_mode.
    """
    width, height = spec.maze_size
    answer_key_prompt = texts.get("answer_key_prompt")
    pages: list[BookPage] = []

    for page_num in range(1, spec.pages_per_book + 1):
        difficulty = page_difficulty(
            spec.difficulty_mode,
            page_num,
            spec.pages_per_book,
            spec.base_difficulty,
            rng,
        )
        shape = page_shape(page_num, spec.pages_per_book, spec.difficulty_mode, rng)
        maze = maze_generator.generate(width, height, difficulty, shape)
        label = difficulty_label(difficulty, texts)

        pages.append(
            BookPage(
                maze=maze,
                title=f"Maze {page_num}",
                prompt=page_prompt(theme, page_num - 1),
                page_number=page_num,
                difficulty_label=label,
            )
        )
        pages.append(
            BookPage(
                maze=maze,
                title=f"Maze {page_num}",
                prompt=answer_key_prompt,
                page_number=page_num,
                is_solution=True,
                difficulty_label=label,
            )
        )

    return pages
