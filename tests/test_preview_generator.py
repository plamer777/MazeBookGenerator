"""Unit-тесты для PreviewGenerator с моками."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from maze_book_generator.infrastructure.preview_generator import PreviewGenerator


class TestPreviewGenerator:
    """Проверяет логику генератора preview с моками."""

    def setup_method(self) -> None:
        """Инициализация генератора."""
        self.generator = PreviewGenerator()

    def test_maze_count_label_english(self) -> None:
        """Бейдж количества лабиринтов для английского."""
        number, noun = self.generator._maze_count_label(5, "en")
        assert number == "5"
        assert noun == "MAZES"

    def test_maze_count_label_russian_singular(self) -> None:
        """Бейдж количества лабиринтов для русского (1)."""
        number, noun = self.generator._maze_count_label(1, "ru")
        assert number == "1"
        assert noun == "ЛАБИРИНТ"

    def test_maze_count_label_russian_few(self) -> None:
        """Бейдж количества лабиринтов для русского (2-4)."""
        number, noun = self.generator._maze_count_label(3, "ru")
        assert number == "3"
        assert noun == "ЛАБИРИНТА"

    def test_maze_count_label_russian_many(self) -> None:
        """Бейдж количества лабиринтов для русского (5+)."""
        number, noun = self.generator._maze_count_label(10, "ru")
        assert number == "10"
        assert noun == "ЛАБИРИНТОВ"

    def test_load_cover_from_pdf(self, tmp_path: Path) -> None:
        """Загрузка обложки из PDF."""
        with patch("maze_book_generator.infrastructure.preview_generator.convert_from_path") as mock_convert:
            mock_image = MagicMock()
            mock_image.convert.return_value = mock_image
            mock_convert.return_value = [mock_image]

            (tmp_path / "book.pdf").touch()

            cover = self.generator._load_cover(tmp_path)

            assert cover is not None
            mock_convert.assert_called_once()

    def test_load_cover_no_pdf(self, tmp_path: Path) -> None:
        """Загрузка обложки при отсутствии PDF."""
        cover = self.generator._load_cover(tmp_path)

        assert cover is None

    def test_load_cover_conversion_error(self, tmp_path: Path) -> None:
        """Обработка ошибки при конвертации PDF."""
        with patch("maze_book_generator.infrastructure.preview_generator.convert_from_path") as mock_convert:
            mock_convert.side_effect = Exception("Conversion error")

            (tmp_path / "book.pdf").touch()

            cover = self.generator._load_cover(tmp_path)

            assert cover is None

    def test_load_pages_from_pdf(self, tmp_path: Path) -> None:
        """Загрузка страниц из PDF."""
        with patch("maze_book_generator.infrastructure.preview_generator.convert_from_path") as mock_convert:
            mock_images = [MagicMock() for _ in range(5)]
            for img in mock_images:
                img.convert.return_value = img
            mock_convert.return_value = mock_images

            (tmp_path / "book.pdf").touch()

            pages = self.generator._load_pages_from_pdf(tmp_path, count=3)

            assert len(pages) == 3
            mock_convert.assert_called_once()

    def test_load_pages_no_pdf(self, tmp_path: Path) -> None:
        """Загрузка страниц при отсутствии PDF (плейсхолдеры)."""
        pages = self.generator._load_pages_from_pdf(tmp_path, count=3)

        assert len(pages) == 3

    def test_load_pages_conversion_error(self, tmp_path: Path) -> None:
        """Обработка ошибки при конвертации страниц."""
        with patch("maze_book_generator.infrastructure.preview_generator.convert_from_path") as mock_convert:
            mock_convert.side_effect = Exception("Conversion error")

            (tmp_path / "book.pdf").touch()

            pages = self.generator._load_pages_from_pdf(tmp_path, count=3)

            assert len(pages) == 3  # плейсхолдеры

    def test_generate_previews_with_mock_dependencies(self, tmp_path: Path) -> None:
        """Генерация preview с моками зависимостей."""
        with (
            patch.object(self.generator, "_load_cover") as mock_load_cover,
            patch.object(self.generator, "_load_pages_from_pdf") as mock_load_pages,
            patch.object(self.generator, "_load_solution_page") as mock_load_solution,
            patch.object(self.generator, "_save_thumbnail") as mock_save_thumb,
            patch.object(self.generator, "_generate_book_spread") as mock_spread,
            patch.object(self.generator, "_generate_collage") as mock_collage,
            patch.object(self.generator, "_generate_answer_preview") as mock_answer,
            patch.object(self.generator, "_generate_promo_banner") as mock_promo,
        ):
            mock_load_cover.return_value = MagicMock()
            mock_load_pages.return_value = [MagicMock() for _ in range(3)]
            mock_load_solution.return_value = MagicMock()

            paths = self.generator.generate_previews(
                tmp_path, maze_count=5, language="en"
            )

            assert len(paths) > 0
            mock_save_thumb.assert_called()
            mock_spread.assert_called_once()
            mock_collage.assert_called_once()
            mock_answer.assert_called_once()
            mock_promo.assert_called_once()

    def test_generate_previews_no_cover(self, tmp_path: Path) -> None:
        """Генерация preview без обложки."""
        with (
            patch.object(self.generator, "_load_cover") as mock_load_cover,
            patch.object(self.generator, "_load_pages_from_pdf") as mock_load_pages,
            patch.object(self.generator, "_load_solution_page") as mock_load_solution,
            patch.object(self.generator, "_save_thumbnail"),
            patch.object(self.generator, "_generate_book_spread"),
            patch.object(self.generator, "_generate_collage"),
            patch.object(self.generator, "_generate_answer_preview"),
            patch.object(self.generator, "_generate_promo_banner") as mock_promo,
        ):
            mock_load_cover.return_value = None
            mock_load_pages.return_value = [MagicMock() for _ in range(3)]
            mock_load_solution.return_value = MagicMock()

            paths = self.generator.generate_previews(
                tmp_path, maze_count=0, language="en"
            )

            # Без обложки не должно быть cover thumbnail и promo
            assert len(paths) > 0
            mock_promo.assert_not_called()

    def test_generate_previews_no_solution(self, tmp_path: Path) -> None:
        """Генерация preview без страницы ответов."""
        with (
            patch.object(self.generator, "_load_cover") as mock_load_cover,
            patch.object(self.generator, "_load_pages_from_pdf") as mock_load_pages,
            patch.object(self.generator, "_load_solution_page") as mock_load_solution,
            patch.object(self.generator, "_save_thumbnail"),
            patch.object(self.generator, "_generate_book_spread"),
            patch.object(self.generator, "_generate_collage"),
            patch.object(self.generator, "_generate_answer_preview") as mock_answer,
            patch.object(self.generator, "_generate_promo_banner"),
        ):
            mock_load_cover.return_value = MagicMock()
            mock_load_pages.return_value = [MagicMock() for _ in range(3)]
            mock_load_solution.return_value = None

            paths = self.generator.generate_previews(
                tmp_path, maze_count=5, language="en"
            )

            # Без solution не должно быть answer preview
            assert len(paths) > 0
            mock_answer.assert_not_called()
