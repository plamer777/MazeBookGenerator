"""Unit-тесты для PreviewGenerator с моками."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.infrastructure.preview_generator import PreviewGenerator


class TestPreviewGenerator(unittest.TestCase):
    """Проверяет логику генератора preview с моками."""

    def setUp(self) -> None:
        """Инициализация генератора."""
        self.generator = PreviewGenerator()

    def test_maze_count_label_english(self) -> None:
        """Бейдж количества лабиринтов для английского."""
        number, noun = self.generator._maze_count_label(5, "en")
        self.assertEqual(number, "5")
        self.assertEqual(noun, "MAZES")

    def test_maze_count_label_russian_singular(self) -> None:
        """Бейдж количества лабиринтов для русского (1)."""
        number, noun = self.generator._maze_count_label(1, "ru")
        self.assertEqual(number, "1")
        self.assertEqual(noun, "ЛАБИРИНТ")

    def test_maze_count_label_russian_few(self) -> None:
        """Бейдж количества лабиринтов для русского (2-4)."""
        number, noun = self.generator._maze_count_label(3, "ru")
        self.assertEqual(number, "3")
        self.assertEqual(noun, "ЛАБИРИНТА")

    def test_maze_count_label_russian_many(self) -> None:
        """Бейдж количества лабиринтов для русского (5+)."""
        number, noun = self.generator._maze_count_label(10, "ru")
        self.assertEqual(number, "10")
        self.assertEqual(noun, "ЛАБИРИНТОВ")

    def test_load_cover_from_pdf(self) -> None:
        """Загрузка обложки из PDF."""
        with patch("src.infrastructure.preview_generator.convert_from_path") as mock_convert:
            mock_image = MagicMock()
            mock_image.convert.return_value = mock_image
            mock_convert.return_value = [mock_image]

            output_dir = Path("/tmp/test")
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "book.pdf").touch()

            cover = self.generator._load_cover(output_dir)

            self.assertIsNotNone(cover)
            mock_convert.assert_called_once()

    def test_load_cover_no_pdf(self) -> None:
        """Загрузка обложки при отсутствии PDF."""
        output_dir = Path("/tmp/test_no_pdf")
        output_dir.mkdir(parents=True, exist_ok=True)

        cover = self.generator._load_cover(output_dir)

        self.assertIsNone(cover)

    def test_load_cover_conversion_error(self) -> None:
        """Обработка ошибки при конвертации PDF."""
        with patch("src.infrastructure.preview_generator.convert_from_path") as mock_convert:
            mock_convert.side_effect = Exception("Conversion error")

            output_dir = Path("/tmp/test_error")
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "book.pdf").touch()

            cover = self.generator._load_cover(output_dir)

            self.assertIsNone(cover)

    def test_load_pages_from_pdf(self) -> None:
        """Загрузка страниц из PDF."""
        with patch("src.infrastructure.preview_generator.convert_from_path") as mock_convert:
            mock_images = [MagicMock() for _ in range(5)]
            for img in mock_images:
                img.convert.return_value = img
            mock_convert.return_value = mock_images

            output_dir = Path("/tmp/test_pages")
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "book.pdf").touch()

            pages = self.generator._load_pages_from_pdf(output_dir, count=3)

            self.assertEqual(len(pages), 3)
            mock_convert.assert_called_once()

    def test_load_pages_no_pdf(self) -> None:
        """Загрузка страниц при отсутствии PDF (плейсхолдеры)."""
        output_dir = Path("/tmp/test_no_pages")
        output_dir.mkdir(parents=True, exist_ok=True)

        pages = self.generator._load_pages_from_pdf(output_dir, count=3)

        self.assertEqual(len(pages), 3)

    def test_load_pages_conversion_error(self) -> None:
        """Обработка ошибки при конвертации страниц."""
        with patch("src.infrastructure.preview_generator.convert_from_path") as mock_convert:
            mock_convert.side_effect = Exception("Conversion error")

            output_dir = Path("/tmp/test_pages_error")
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "book.pdf").touch()

            pages = self.generator._load_pages_from_pdf(output_dir, count=3)

            self.assertEqual(len(pages), 3)  # плейсхолдеры

    def test_generate_previews_with_mock_dependencies(self) -> None:
        """Генерация preview с моками зависимостей."""
        with patch.object(self.generator, "_load_cover") as mock_load_cover:
            with patch.object(self.generator, "_load_pages_from_pdf") as mock_load_pages:
                with patch.object(self.generator, "_load_solution_page") as mock_load_solution:
                    with patch.object(self.generator, "_save_thumbnail") as mock_save_thumb:
                        with patch.object(self.generator, "_generate_book_spread") as mock_spread:
                            with patch.object(self.generator, "_generate_collage") as mock_collage:
                                with patch.object(self.generator, "_generate_answer_preview") as mock_answer:
                                    with patch.object(self.generator, "_generate_promo_banner") as mock_promo:
                                        mock_cover = MagicMock()
                                        mock_pages = [MagicMock() for _ in range(3)]
                                        mock_solution = MagicMock()

                                        mock_load_cover.return_value = mock_cover
                                        mock_load_pages.return_value = mock_pages
                                        mock_load_solution.return_value = mock_solution

                                        output_dir = Path("/tmp/test_preview")
                                        output_dir.mkdir(parents=True, exist_ok=True)

                                        paths = self.generator.generate_previews(
                                            output_dir, maze_count=5, language="en"
                                        )

                                        self.assertGreater(len(paths), 0)
                                        mock_save_thumb.assert_called()
                                        mock_spread.assert_called_once()
                                        mock_collage.assert_called_once()
                                        mock_answer.assert_called_once()
                                        mock_promo.assert_called_once()

    def test_generate_previews_no_cover(self) -> None:
        """Генерация preview без обложки."""
        with patch.object(self.generator, "_load_cover") as mock_load_cover:
            with patch.object(self.generator, "_load_pages_from_pdf") as mock_load_pages:
                with patch.object(self.generator, "_load_solution_page") as mock_load_solution:
                    with patch.object(self.generator, "_save_thumbnail") as mock_save_thumb:
                        with patch.object(self.generator, "_generate_book_spread") as mock_spread:
                            with patch.object(self.generator, "_generate_collage") as mock_collage:
                                with patch.object(self.generator, "_generate_answer_preview") as mock_answer:
                                    with patch.object(self.generator, "_generate_promo_banner") as mock_promo:
                                        mock_load_cover.return_value = None
                                        mock_pages = [MagicMock() for _ in range(3)]
                                        mock_solution = MagicMock()

                                        mock_load_pages.return_value = mock_pages
                                        mock_load_solution.return_value = mock_solution

                                        output_dir = Path("/tmp/test_no_cover")
                                        output_dir.mkdir(parents=True, exist_ok=True)

                                        paths = self.generator.generate_previews(
                                            output_dir, maze_count=0, language="en"
                                        )

                                        # Без обложки не должно быть cover thumbnail и promo
                                        self.assertGreater(len(paths), 0)
                                        mock_promo.assert_not_called()

    def test_generate_previews_no_solution(self) -> None:
        """Генерация preview без страницы ответов."""
        with patch.object(self.generator, "_load_cover") as mock_load_cover:
            with patch.object(self.generator, "_load_pages_from_pdf") as mock_load_pages:
                with patch.object(self.generator, "_load_solution_page") as mock_load_solution:
                    with patch.object(self.generator, "_save_thumbnail") as mock_save_thumb:
                        with patch.object(self.generator, "_generate_book_spread") as mock_spread:
                            with patch.object(self.generator, "_generate_collage") as mock_collage:
                                with patch.object(self.generator, "_generate_answer_preview") as mock_answer:
                                    with patch.object(self.generator, "_generate_promo_banner") as mock_promo:
                                        mock_cover = MagicMock()
                                        mock_pages = [MagicMock() for _ in range(3)]

                                        mock_load_cover.return_value = mock_cover
                                        mock_load_pages.return_value = mock_pages
                                        mock_load_solution.return_value = None

                                        output_dir = Path("/tmp/test_no_solution")
                                        output_dir.mkdir(parents=True, exist_ok=True)

                                        paths = self.generator.generate_previews(
                                            output_dir, maze_count=5, language="en"
                                        )

                                        # Без solution не должно быть answer preview
                                        self.assertGreater(len(paths), 0)
                                        mock_answer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
