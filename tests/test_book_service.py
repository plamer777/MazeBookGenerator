"""Unit-тесты для BookService с моками зависимостей."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.application.book_service import BookService
from src.domain.models import BookConfig, Difficulty, DifficultyMode, MazeShape, Theme
from src.localization import BookTexts


class TestBookService(unittest.TestCase):
    """Проверяет логику сервиса генерации книг с моками."""

    def setUp(self) -> None:
        """Инициализация сервиса с моками контейнера."""
        with patch("src.application.book_service.container") as mock_container:
            mock_container.maze_generator = MagicMock()
            mock_container.pdf_renderer = MagicMock()
            mock_container.ai_client = MagicMock()
            mock_container.mongodb_client = MagicMock()
            mock_container.image_generator = MagicMock()
            mock_container.preview_generator = MagicMock()
            mock_container.hf_client = MagicMock()
            mock_container.pollinations_client = MagicMock()
            mock_container.replicate_client = MagicMock()

            self.service = BookService()

    def test_resolve_language_with_config(self) -> None:
        """Язык из BookConfig имеет приоритет."""
        config = BookConfig(language="ru")
        result = BookService._resolve_language("en", config)
        self.assertEqual(result, "ru")

    def test_resolve_language_without_config(self) -> None:
        """Язык из параметра при отсутствии config."""
        result = BookService._resolve_language("ru", None)
        self.assertEqual(result, "ru")

    def test_difficulty_to_label_easy(self) -> None:
        """Лейбл для лёгкой сложности."""
        texts = BookTexts("en")
        label = self.service._difficulty_to_label(Difficulty.L1, texts)
        self.assertEqual(label, "Easy")

    def test_difficulty_to_label_medium(self) -> None:
        """Лейбл для средней сложности."""
        texts = BookTexts("en")
        label = self.service._difficulty_to_label(Difficulty.L4, texts)
        self.assertEqual(label, "Medium")

    def test_difficulty_to_label_hard(self) -> None:
        """Лейбл для сложной сложности."""
        texts = BookTexts("en")
        label = self.service._difficulty_to_label(Difficulty.L7, texts)
        self.assertEqual(label, "Hard")

    def test_difficulty_to_label_russian(self) -> None:
        """Лейбл для сложности на русском."""
        texts = BookTexts("ru")
        label = self.service._difficulty_to_label(Difficulty.L1, texts)
        self.assertEqual(label, "Легкий")

    def test_build_book_config_without_input(self) -> None:
        """Построение конфигурации без входного config."""
        theme = Theme(
            book_title="Test Theme",
            book_description="Test Description",
            page_prompts=[],
            image_keywords=[],
        )

        config = self.service._build_book_config(
            pages_per_book=5,
            language="en",
            theme=theme,
            base_difficulty=Difficulty.MEDIUM,
            config=None,
        )

        self.assertEqual(config.language, "en")
        self.assertEqual(config.title, "Test Theme")
        self.assertEqual(config.maze_count, 5)
        self.assertIsNotNone(config.difficulty_label)

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

        config = self.service._build_book_config(
            pages_per_book=5,
            language="en",
            theme=theme,
            base_difficulty=Difficulty.MEDIUM,
            config=input_config,
        )

        self.assertEqual(config.language, "ru")
        self.assertEqual(config.title, "Custom Title")
        self.assertEqual(config.age_range, "5-8 years")
        self.assertEqual(config.maze_count, 10)

    def test_get_page_difficulty_fixed(self) -> None:
        """Режим FIXED возвращает базовую сложность."""
        difficulty = self.service._get_page_difficulty(
            DifficultyMode.FIXED, 1, 10, Difficulty.HARD
        )
        self.assertEqual(difficulty, Difficulty.HARD)

    def test_get_page_difficulty_incremental(self) -> None:
        """Режим INCREMENTAL увеличивает сложность."""
        difficulty_start = self.service._get_page_difficulty(
            DifficultyMode.INCREMENTAL, 1, 10, Difficulty.L1
        )
        difficulty_end = self.service._get_page_difficulty(
            DifficultyMode.INCREMENTAL, 10, 10, Difficulty.L1
        )

        self.assertLess(difficulty_start.level, difficulty_end.level)

    def test_get_page_difficulty_random_range(self) -> None:
        """Режим RANDOM_RANGE возвращает случайную сложность."""
        difficulty = self.service._get_page_difficulty(
            DifficultyMode.RANDOM_RANGE, 1, 10, Difficulty.MEDIUM
        )
        self.assertIn(difficulty, [
            Difficulty.L1, Difficulty.L2, Difficulty.L3, Difficulty.L4,
            Difficulty.L5, Difficulty.L6, Difficulty.L7,
        ])

    def test_get_page_difficulty_kids_easy(self) -> None:
        """Режим KIDS_EASY возвращает только простые уровни."""
        difficulty = self.service._get_page_difficulty(
            DifficultyMode.KIDS_EASY, 1, 10, Difficulty.MEDIUM
        )
        self.assertIn(difficulty, [Difficulty.L1, Difficulty.L2])

    def test_get_page_difficulty_challenge_hard(self) -> None:
        """Режим CHALLENGE_HARD возвращает только сложные уровни."""
        difficulty = self.service._get_page_difficulty(
            DifficultyMode.CHALLENGE_HARD, 1, 10, Difficulty.MEDIUM
        )
        self.assertIn(difficulty, [Difficulty.L5, Difficulty.L6, Difficulty.L7])

    def test_get_page_difficulty_story_wave(self) -> None:
        """Режим STORY_WAVE создаёт волновую сложность."""
        difficulties = [
            self.service._get_page_difficulty(DifficultyMode.STORY_WAVE, i, 10, Difficulty.L1)
            for i in range(1, 11)
        ]
        # Проверяем, что есть вариация
        levels = [d.level for d in difficulties]
        self.assertGreater(max(levels) - min(levels), 0)

    def test_get_page_shape_kids_easy(self) -> None:
        """Режим KIDS_EASY использует простые формы."""
        shape = self.service._get_page_shape(1, 10, DifficultyMode.KIDS_EASY)
        self.assertIn(shape, [MazeShape.RECTANGULAR, MazeShape.SQUARE, MazeShape.DIAMOND])

    def test_get_page_shape_challenge_hard(self) -> None:
        """Режим CHALLENGE_HARD использует сложные формы."""
        shape = self.service._get_page_shape(1, 10, DifficultyMode.CHALLENGE_HARD)
        complex_shapes = [
            MazeShape.TRIANGULAR, MazeShape.CIRCULAR, MazeShape.CHAOTIC,
            MazeShape.RANDOM, MazeShape.DIAMOND, MazeShape.HEART,
        ]
        self.assertIn(shape, complex_shapes)

    def test_get_page_shape_incremental_progression(self) -> None:
        """Режим INCREMENTAL эволюционирует от простых к сложным."""
        shape_early = self.service._get_page_shape(1, 10, DifficultyMode.INCREMENTAL)
        shape_late = self.service._get_page_shape(9, 10, DifficultyMode.INCREMENTAL)

        # Ранние страницы - простые формы
        self.assertIn(shape_early, [
            MazeShape.RECTANGULAR, MazeShape.SQUARE, MazeShape.DIAMOND,
            MazeShape.TRIANGULAR, MazeShape.CIRCULAR,
        ])
        # Поздние страницы - все формы
        self.assertIn(shape_late, [
            MazeShape.CIRCULAR, MazeShape.TRIANGULAR, MazeShape.CHAOTIC,
            MazeShape.RANDOM, MazeShape.DIAMOND, MazeShape.HEART,
        ])

    def test_get_page_shape_default_rotation(self) -> None:
        """Дефолтный режим чередует все формы."""
        shapes = [
            self.service._get_page_shape(i, 10, DifficultyMode.FIXED)
            for i in range(1, 9)
        ]
        # Проверяем, что формы чередуются
        self.assertEqual(len(set(shapes)), 8)

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

        prompt = self.service._get_page_prompt(theme, 0)
        self.assertEqual(prompt, "Task 1")

    def test_get_page_prompt_fallback(self) -> None:
        """Fallback промпт при отсутствии в теме."""
        theme = Theme(
            book_title="Test",
            book_description="Test",
            page_prompts=[],
            image_keywords=[],
        )

        prompt = self.service._get_page_prompt(theme, 5)
        self.assertIn("maze", prompt.lower())
        self.assertIn("6", prompt)  # index + 1

    def test_next_free_book_id_empty_dir(self) -> None:
        """Следующий ID в пустой директории."""
        with patch("src.application.book_service.settings") as mock_settings:
            mock_settings.OUTPUT_DIR = Path("/tmp/test_empty")
            Path("/tmp/test_empty").mkdir(parents=True, exist_ok=True)

            book_id = BookService._next_free_book_id(mock_settings.OUTPUT_DIR)
            self.assertEqual(book_id, 1)

    def test_next_free_book_id_with_existing(self) -> None:
        """Следующий ID с существующими папками."""
        import shutil
        with patch("src.application.book_service.settings") as mock_settings:
            mock_settings.OUTPUT_DIR = Path("/tmp/test_existing_unique")
            if Path("/tmp/test_existing_unique").exists():
                shutil.rmtree("/tmp/test_existing_unique")
            Path("/tmp/test_existing_unique").mkdir(parents=True, exist_ok=True)
            (Path("/tmp/test_existing_unique") / "book_1").mkdir()
            (Path("/tmp/test_existing_unique") / "book_3").mkdir()

            book_id = BookService._next_free_book_id(mock_settings.OUTPUT_DIR)
            self.assertEqual(book_id, 4)

    def test_save_marketplace_info_english(self) -> None:
        """Сохранение маркетинговой информации на английском."""
        theme = Theme(
            book_title="Test Title",
            book_description="Test Description",
            marketplace_title="Marketplace Title",
            marketplace_description="Marketplace Description",
            page_prompts=[],
            image_keywords=[],
        )

        output_dir = Path("/tmp/test_marketplace_en")
        output_dir.mkdir(parents=True, exist_ok=True)

        self.service._save_marketplace_info(output_dir, theme, "en")

        info_path = output_dir / "book_into.txt"
        self.assertTrue(info_path.exists())
        content = info_path.read_text(encoding="utf-8")
        self.assertIn("Marketplace title", content)
        self.assertIn("Marketplace Title", content)

    def test_save_marketplace_info_russian(self) -> None:
        """Сохранение маркетинговой информации на русском."""
        theme = Theme(
            book_title="Тест",
            book_description="Описание",
            marketplace_title="Маркетплейс заголовок",
            marketplace_description="Маркетплейс описание",
            page_prompts=[],
            image_keywords=[],
        )

        output_dir = Path("/tmp/test_marketplace_ru")
        output_dir.mkdir(parents=True, exist_ok=True)

        self.service._save_marketplace_info(output_dir, theme, "ru")

        info_path = output_dir / "book_into.txt"
        self.assertTrue(info_path.exists())
        content = info_path.read_text(encoding="utf-8")
        self.assertIn("Заголовок для маркетплейса", content)
        self.assertIn("Маркетплейс заголовок", content)

    def test_save_marketplace_info_fallback(self) -> None:
        """Fallback на базовые поля при отсутствии marketplace полей."""
        theme = Theme(
            book_title="Base Title",
            book_description="Base Description",
            page_prompts=[],
            image_keywords=[],
        )

        output_dir = Path("/tmp/test_marketplace_fallback")
        output_dir.mkdir(parents=True, exist_ok=True)

        self.service._save_marketplace_info(output_dir, theme, "en")

        info_path = output_dir / "book_into.txt"
        content = info_path.read_text(encoding="utf-8")
        self.assertIn("Base Title", content)
        self.assertIn("Base Description", content)


if __name__ == "__main__":
    unittest.main()
