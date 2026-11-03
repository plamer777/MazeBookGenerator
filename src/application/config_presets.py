"""Готовые пресеты BookConfig для типовых сценариев генерации книги с лабиринтами.

Использование в main.py:
    from src.application.config_presets import PRESETS
    book_config = PRESETS["en_kids_basic"]
"""

from src.domain.models import BookConfig


PRESETS: dict[str, BookConfig] = {

    # ------------------------------------------------------------------
    # Английский язык
    # ------------------------------------------------------------------

    "en_kids_basic": BookConfig(
        language="en",
        subtitle="Maze Book",
        age_range="4–7",
        include_contents_page=True,
        show_start_finish_labels=True,
        generate_print_friendly_version=False,
    ),

    "en_kids_printable": BookConfig(
        language="en",
        subtitle="Maze Book",
        age_range="4–7",
        include_contents_page=True,
        show_start_finish_labels=True,
        generate_print_friendly_version=True,
    ),

    "en_school": BookConfig(
        language="en",
        subtitle="Maze Book",
        age_range="7–12",
        include_contents_page=True,
        show_start_finish_labels=False,
        generate_print_friendly_version=False,
    ),

    "en_school_printable": BookConfig(
        language="en",
        subtitle="Maze Book",
        age_range="7–12",
        include_contents_page=True,
        show_start_finish_labels=False,
        generate_print_friendly_version=True,
    ),

    "en_challenge": BookConfig(
        language="en",
        subtitle="Expert Maze Book",
        age_range="10+",
        include_contents_page=False,
        show_start_finish_labels=False,
        generate_print_friendly_version=False,
    ),

    # ------------------------------------------------------------------
    # Русский язык
    # ------------------------------------------------------------------
    "ru_kids_easy": BookConfig(
        language="ru",
        subtitle="Книга лабиринтов",
        age_range="4–5",
        include_contents_page=True,
        show_start_finish_labels=True,
        generate_print_friendly_version=True,
    ),
    "ru_kids_basic": BookConfig(
        language="ru",
        subtitle="Книга лабиринтов",
        age_range="4–7",
        include_contents_page=True,
        show_start_finish_labels=True,
        generate_print_friendly_version=False,
    ),

    "ru_kids_printable": BookConfig(
        language="ru",
        subtitle="Книга лабиринтов",
        age_range="4–7",
        include_contents_page=True,
        show_start_finish_labels=True,
        generate_print_friendly_version=True,
    ),

    "ru_school": BookConfig(
        language="ru",
        subtitle="Книга лабиринтов",
        age_range="7–12",
        include_contents_page=True,
        show_start_finish_labels=False,
        generate_print_friendly_version=False,
    ),

    "ru_school_printable": BookConfig(
        language="ru",
        subtitle="Книга лабиринтов",
        age_range="7–12",
        include_contents_page=True,
        show_start_finish_labels=False,
        generate_print_friendly_version=True,
    ),

    "ru_challenge": BookConfig(
        language="ru",
        subtitle="Экспертная книга лабиринтов",
        age_range="10+",
        include_contents_page=False,
        show_start_finish_labels=False,
        generate_print_friendly_version=False,
    ),
}


def personalized(
    preset_name: str,
    child_name: str,
    child_age: str | None = None,
) -> BookConfig:
    """Возвращает копию пресета с добавленными данными ребёнка.

    Args:
        preset_name: Ключ из PRESETS.
        child_name: Имя ребёнка для персонализации обложки и финальной страницы.
        child_age: Возраст ребёнка (опционально).

    Returns:
        Новый BookConfig с заполненными child_name / child_age.

    Raises:
        KeyError: Если пресет с таким именем не существует.
    """
    base = PRESETS[preset_name]
    return BookConfig(
        language=base.language,
        title=base.title,
        subtitle=base.subtitle,
        theme_name=base.theme_name,
        age_range=base.age_range,
        target_age=base.target_age,
        child_name=child_name,
        child_age=child_age,
        maze_count=base.maze_count,
        include_contents_page=base.include_contents_page,
        show_start_finish_labels=base.show_start_finish_labels,
        generate_print_friendly_version=base.generate_print_friendly_version,
        difficulty_label=base.difficulty_label,
    )
