"""Smoke-тесты новых параметров конфигурации и локализации книги."""


from src.domain.models import BookConfig
from src.localization import BookTexts


class TestBookConfigAndLocalization:
    """Проверяет базовые сценарии конфигурации и i18n для книги."""

    def test_book_config_defaults_for_new_flags(self) -> None:
        """Новые флаги должны иметь безопасные дефолты для обратной совместимости."""
        config = BookConfig()

        assert config.include_contents_page
        assert config.show_start_finish_labels
        assert not config.generate_print_friendly_version

    def test_localized_start_finish_labels_exist(self) -> None:
        """Подписи START/FINISH должны быть локализованы для en/ru."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        assert en_texts.get("start_label") == "START"
        assert en_texts.get("finish_label") == "FINISH"
        assert ru_texts.get("start_label") == "СТАРТ"
        assert ru_texts.get("finish_label") == "ФИНИШ"

    def test_localized_cover_and_contents_templates(self) -> None:
        """Ключевые шаблоны обложки/contents должны корректно форматироваться."""
        en_texts = BookTexts("en")
        ru_texts = BookTexts("ru")

        assert en_texts.format("cover_mazes", count=10) == "10 Mazes"
        assert ru_texts.format("cover_mazes", count=10) == "10 лабиринтов"
        assert en_texts.format("contents_mazes", count=8) == "Mazes: 8"
        assert ru_texts.format("contents_mazes", count=8) == "Лабиринтов: 8"
