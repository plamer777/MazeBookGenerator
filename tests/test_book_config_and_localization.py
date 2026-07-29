"""Smoke-тесты новых параметров конфигурации и локализации книги."""

import unittest

from src.domain.models import BookConfig
from src.localization import BookTexts


class BookConfigAndLocalizationTests(unittest.TestCase):
    """Проверяет базовые сценарии конфигурации и i18n для книги."""

    def test_book_config_defaults_for_new_flags(self) -> None:
        """Новые флаги должны иметь безопасные дефолты для обратной совместимости."""
        config = BookConfig()

        self.assertTrue(config.include_contents_page)
        self.assertTrue(config.show_start_finish_labels)
        self.assertFalse(config.generate_print_friendly_version)

    def test_localized_start_finish_labels_exist(self) -> None:
        """Подписи START/FINISH должны быть локализованы для en/ru."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        self.assertEqual(en_texts.get("start_label"), "START")
        self.assertEqual(en_texts.get("finish_label"), "FINISH")
        self.assertEqual(ru_texts.get("start_label"), "СТАРТ")
        self.assertEqual(ru_texts.get("finish_label"), "ФИНИШ")

    def test_localized_cover_and_contents_templates(self) -> None:
        """Ключевые шаблоны обложки/contents должны корректно форматироваться."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        self.assertEqual(en_texts.format("cover_mazes", count=10), "10 Mazes")
        self.assertEqual(ru_texts.format("cover_mazes", count=10), "10 лабиринтов")
        self.assertEqual(en_texts.format("contents_mazes", count=8), "Mazes: 8")
        self.assertEqual(ru_texts.format("contents_mazes", count=8), "Лабиринтов: 8")


if __name__ == "__main__":
    unittest.main()
