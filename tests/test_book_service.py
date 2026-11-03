"""Unit-тесты для BookService и функций book_factory/marketplace с моками."""

from pathlib import Path
from unittest.mock import MagicMock

from maze_book_generator.application.book_factory import (
    build_book_config,
    build_default_theme,
    difficulty_label,
    page_difficulty,
    page_prompt,
    page_shape,
    resolve_language,
)
from maze_book_generator.domain.models import (
    BookConfig,
    Difficulty,
    DifficultyMode,
    MazeShape,
    Theme,
)
from maze_book_generator.infrastructure.storage.marketplace import (
    next_free_book_id,
    save_marketplace_info,
)
from maze_book_generator.localization import BookTexts
from maze_book_generator.utils import create_rng


class TestBookService:
    """Проверяет логику сервиса генерации книг с моками."""


    def test_resolve_language_with_config(self) -> None:
        """Язык из BookConfig имеет приоритет."""
        config = BookConfig(language="ru")
        result = resolve_language("en", config)
        assert result == "ru"

    def test_build_default_theme_offline(self) -> None:
        """Офлайн-тема: локализованные задания и keywords без OpenAI."""
        theme = build_default_theme("Моя тема", "ru", pages_per_book=3)

        assert theme.book_title == "Моя тема"
        assert len(theme.page_prompts) == 3
        assert len(theme.image_keywords) == 3
        assert theme.marketplace_title == "Моя тема"
        assert "1" in theme.page_prompts[0].task
        assert "3" in theme.page_prompts[2].task

    def test_resolve_language_without_config(self) -> None:
        """Язык из параметра при отсутствии config."""
        result = resolve_language("ru", None)
        assert result == "ru"

    def test_difficulty_to_label_easy(self) -> None:
        """Лейбл для лёгкой сложности."""
        texts = BookTexts("en")
        label = difficulty_label(Difficulty.L1, texts)
        assert label == "Easy"

    def test_difficulty_to_label_medium(self) -> None:
        """Лейбл для средней сложности."""
        texts = BookTexts("en")
        label = difficulty_label(Difficulty.L4, texts)
        assert label == "Medium"

    def test_difficulty_to_label_hard(self) -> None:
        """Лейбл для сложной сложности."""
        texts = BookTexts("en")
        label = difficulty_label(Difficulty.L7, texts)
        assert label == "Hard"

    def test_difficulty_to_label_russian(self) -> None:
        """Лейбл для сложности на русском."""
        texts = BookTexts("ru")
        label = difficulty_label(Difficulty.L1, texts)
        assert label == "Легкий"

    def test_build_book_config_without_input(self) -> None:
        """Построение конфигурации без входного config."""
        theme = Theme(
            book_title="Test Theme",
            book_description="Test Description",
            page_prompts=[],
            image_keywords=[],
        )

        config = build_book_config(
            pages_per_book=5,
            language="en",
            theme=theme,
            base_difficulty=Difficulty.MEDIUM,
            config=None,
        )

        assert config.language == "en"
        assert config.title == "Test Theme"
        assert config.maze_count == 5
        assert config.difficulty_label is not None

    def test_build_book_config_with_input(self) -> None:
        """Построение конфигурации с входным config."""
        theme = Theme(
            book_title="Test Theme",
            book_description="Test Description",
            page_prompts=[],
            image_keywords=[],
        )
        input_config = BookConfig(
            language="ru",
            title="Custom Title",
            age_range="5-8 years",
            maze_count=10,
        )

        config = build_book_config(
            pages_per_book=5,
            language="en",
            theme=theme,
            base_difficulty=Difficulty.MEDIUM,
            config=input_config,
        )

        assert config.language == "ru"
        assert config.title == "Custom Title"
        assert config.age_range == "5-8 years"
        assert config.maze_count == 10

class TestPageStrategies:
    """Набор тестов."""


    def test_get_page_difficulty_fixed(self) -> None:
        """Режим FIXED возвращает базовую сложность."""
        difficulty = page_difficulty(
            DifficultyMode.FIXED, 1, 10, Difficulty.HARD, create_rng()
        )
        assert difficulty == Difficulty.HARD

    def test_get_page_difficulty_incremental(self) -> None:
        """Режим INCREMENTAL увеличивает сложность."""
        difficulty_start = page_difficulty(
            DifficultyMode.INCREMENTAL, 1, 10, Difficulty.L1, create_rng()
        )
        difficulty_end = page_difficulty(
            DifficultyMode.INCREMENTAL, 10, 10, Difficulty.L1, create_rng()
        )

        assert difficulty_start.level < difficulty_end.level

    def test_get_page_difficulty_random_range(self) -> None:
        """Режим RANDOM_RANGE возвращает случайную сложность."""
        difficulty = page_difficulty(
            DifficultyMode.RANDOM_RANGE, 1, 10, Difficulty.MEDIUM, create_rng()
        )
        assert difficulty in [
            Difficulty.L1, Difficulty.L2, Difficulty.L3, Difficulty.L4,
            Difficulty.L5, Difficulty.L6, Difficulty.L7,
        ]

    def test_get_page_difficulty_kids_easy(self) -> None:
        """Режим KIDS_EASY возвращает только простые уровни."""
        difficulty = page_difficulty(
            DifficultyMode.KIDS_EASY, 1, 10, Difficulty.MEDIUM, create_rng()
        )
        assert difficulty in [Difficulty.L1, Difficulty.L2]

    def test_get_page_difficulty_challenge_hard(self) -> None:
        """Режим CHALLENGE_HARD возвращает только сложные уровни."""
        difficulty = page_difficulty(
            DifficultyMode.CHALLENGE_HARD, 1, 10, Difficulty.MEDIUM, create_rng()
        )
        assert difficulty in [Difficulty.L5, Difficulty.L6, Difficulty.L7]

    def test_get_page_difficulty_story_wave(self) -> None:
        """Режим STORY_WAVE создаёт волновую сложность."""
        rng = create_rng()
        difficulties = [
            page_difficulty(DifficultyMode.STORY_WAVE, i, 10, Difficulty.L1, rng)
            for i in range(1, 11)
        ]
        # Проверяем, что есть вариация
        levels = [d.level for d in difficulties]
        assert max(levels) - min(levels) > 0

    def test_get_page_shape_kids_easy(self) -> None:
        """Режим KIDS_EASY использует простые формы."""
        shape = page_shape(1, 10, DifficultyMode.KIDS_EASY, create_rng())
        assert shape in [MazeShape.RECTANGULAR, MazeShape.SQUARE, MazeShape.DIAMOND]

    def test_get_page_shape_challenge_hard(self) -> None:
        """Режим CHALLENGE_HARD использует сложные формы."""
        shape = page_shape(1, 10, DifficultyMode.CHALLENGE_HARD, create_rng())
        complex_shapes = [
            MazeShape.TRIANGULAR, MazeShape.CIRCULAR, MazeShape.CHAOTIC,
            MazeShape.RANDOM, MazeShape.DIAMOND, MazeShape.HEART,
        ]
        assert shape in complex_shapes

    def test_get_page_shape_incremental_progression(self) -> None:
        """Режим INCREMENTAL эволюционирует от простых к сложным."""
        shape_early = page_shape(1, 10, DifficultyMode.INCREMENTAL, create_rng())
        shape_late = page_shape(9, 10, DifficultyMode.INCREMENTAL, create_rng())

        # Ранние страницы - простые формы
        assert shape_early in [
            MazeShape.RECTANGULAR, MazeShape.SQUARE, MazeShape.DIAMOND,
            MazeShape.TRIANGULAR, MazeShape.CIRCULAR,
        ]
        # Поздние страницы - все формы
        assert shape_late in [
            MazeShape.CIRCULAR, MazeShape.TRIANGULAR, MazeShape.CHAOTIC,
            MazeShape.RANDOM, MazeShape.DIAMOND, MazeShape.HEART,
        ]

    def test_get_page_shape_default_rotation(self) -> None:
        """Дефолтный режим чередует все формы."""
        shapes = [
            page_shape(i, 10, DifficultyMode.FIXED, create_rng())
            for i in range(1, 9)
        ]
        # Проверяем, что формы чередуются
        assert len(set(shapes)) == 8

    def test_get_page_prompt_from_theme(self) -> None:
        """Получение промпта из темы."""
        theme = Theme(
            book_title="Test",
            book_description="Test",
            page_prompts=[
                MagicMock(task="Task 1", heroes=[]),
                MagicMock(task="Task 2", heroes=[]),
            ],
            image_keywords=[],
        )

        prompt = page_prompt(theme, 0)
        assert prompt == "Task 1"

    def test_get_page_prompt_fallback(self) -> None:
        """Fallback промпт при отсутствии в теме."""
        theme = Theme(
            book_title="Test",
            book_description="Test",
            page_prompts=[],
            image_keywords=[],
        )

        prompt = page_prompt(theme, 5)
        assert "maze" in prompt.lower()
        assert "6" in prompt  # index + 1

class TestMarketplaceStorage:
    """Набор тестов."""


    def test_next_free_book_id_empty_dir(self, tmp_path: Path) -> None:
        """Следующий ID в пустой директории."""
        book_id = next_free_book_id(tmp_path)
        assert book_id == 1

    def test_next_free_book_id_with_existing(self, tmp_path: Path) -> None:
        """Следующий ID с существующими папками."""
        (tmp_path / "book_1").mkdir()
        (tmp_path / "book_3").mkdir()

        book_id = next_free_book_id(tmp_path)
        assert book_id == 4

    def test_save_marketplace_info_english(self, tmp_path: Path) -> None:
        """Сохранение маркетинговой информации на английском."""
        theme = Theme(
            book_title="Test Title",
            book_description="Test Description",
            marketplace_title="Marketplace Title",
            marketplace_description="Marketplace Description",
            page_prompts=[],
            image_keywords=[],
        )

        output_dir = tmp_path

        save_marketplace_info(output_dir, theme, "en")

        info_path = output_dir / "book_into.txt"
        assert info_path.exists()
        content = info_path.read_text(encoding="utf-8")
        assert "Marketplace title" in content
        assert "Marketplace Title" in content

    def test_save_marketplace_info_russian(self, tmp_path: Path) -> None:
        """Сохранение маркетинговой информации на русском."""
        theme = Theme(
            book_title="Тест",
            book_description="Описание",
            marketplace_title="Маркетплейс заголовок",
            marketplace_description="Маркетплейс описание",
            page_prompts=[],
            image_keywords=[],
        )

        output_dir = tmp_path

        save_marketplace_info(output_dir, theme, "ru")

        info_path = output_dir / "book_into.txt"
        assert info_path.exists()
        content = info_path.read_text(encoding="utf-8")
        assert "Заголовок для маркетплейса" in content
        assert "Маркетплейс заголовок" in content

    def test_save_marketplace_info_fallback(self, tmp_path: Path) -> None:
        """Fallback на базовые поля при отсутствии marketplace полей."""
        theme = Theme(
            book_title="Base Title",
            book_description="Base Description",
            page_prompts=[],
            image_keywords=[],
        )

        output_dir = tmp_path

        save_marketplace_info(output_dir, theme, "en")

        info_path = output_dir / "book_into.txt"
        content = info_path.read_text(encoding="utf-8")
        assert "Base Title" in content
        assert "Base Description" in content
