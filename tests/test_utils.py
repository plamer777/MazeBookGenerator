"""Unit-тесты для утилит работы с текстом."""


from src.utils import plural_form_ru, format_count_with_plural_ru


class TestRussianPluralization:
    """Проверяет логику русской плюрализации."""

    def test_plural_form_ru_one(self) -> None:
        """Единственное число (1, 21, 31...)."""
        forms = ("лабиринт", "лабиринта", "лабиринтов")
        assert plural_form_ru(1, forms) == "лабиринт"
        assert plural_form_ru(21, forms) == "лабиринт"
        assert plural_form_ru(31, forms) == "лабиринт"
        assert plural_form_ru(101, forms) == "лабиринт"

    def test_plural_form_ru_few(self) -> None:
        """Форма для 2-4 (2, 3, 4, 22, 23, 24...)."""
        forms = ("лабиринт", "лабиринта", "лабиринтов")
        assert plural_form_ru(2, forms) == "лабиринта"
        assert plural_form_ru(3, forms) == "лабиринта"
        assert plural_form_ru(4, forms) == "лабиринта"
        assert plural_form_ru(22, forms) == "лабиринта"
        assert plural_form_ru(23, forms) == "лабиринта"
        assert plural_form_ru(24, forms) == "лабиринта"

    def test_plural_form_ru_many(self) -> None:
        """Форма для 5+ (5, 6, 7, 11-14, 15-20...)."""
        forms = ("лабиринт", "лабиринта", "лабиринтов")
        assert plural_form_ru(5, forms) == "лабиринтов"
        assert plural_form_ru(6, forms) == "лабиринтов"
        assert plural_form_ru(10, forms) == "лабиринтов"
        assert plural_form_ru(11, forms) == "лабиринтов"
        assert plural_form_ru(12, forms) == "лабиринтов"
        assert plural_form_ru(13, forms) == "лабиринтов"
        assert plural_form_ru(14, forms) == "лабиринтов"
        assert plural_form_ru(15, forms) == "лабиринтов"
        assert plural_form_ru(20, forms) == "лабиринтов"

    def test_plural_form_ru_edge_cases(self) -> None:
        """Пограничные случаи (0, большие числа)."""
        forms = ("шаг", "шага", "шагов")
        assert plural_form_ru(0, forms) == "шагов"
        assert plural_form_ru(100, forms) == "шагов"
        assert plural_form_ru(111, forms) == "шагов"
        assert plural_form_ru(121, forms) == "шаг"
        assert plural_form_ru(122, forms) == "шага"
        assert plural_form_ru(125, forms) == "шагов"

    def test_format_count_with_plural_ru_raw(self) -> None:
        """Форматирование без изменения регистра."""
        result = format_count_with_plural_ru(5, ("шаг", "шага", "шагов"), "raw")
        assert result == "5 шагов"

    def test_format_count_with_plural_ru_lower(self) -> None:
        """Форматирование с приведением к нижнему регистру."""
        result = format_count_with_plural_ru(5, ("Шаг", "Шага", "Шагов"), "lower")
        assert result == "5 шагов"

    def test_format_count_with_plural_ru_upper(self) -> None:
        """Форматирование с приведением к верхнему регистру."""
        result = format_count_with_plural_ru(5, ("шаг", "шага", "шагов"), "upper")
        assert result == "5 ШАГОВ"

    def test_format_count_with_plural_ru_capitalize(self) -> None:
        """Форматирование с капитализацией."""
        result = format_count_with_plural_ru(5, ("шаг", "шага", "шагов"), "capitalize")
        assert result == "5 Шагов"

    def test_format_count_with_plural_ru_zero(self) -> None:
        """Форматирование для нуля."""
        result = format_count_with_plural_ru(0, ("шаг", "шага", "шагов"))
        assert result == "0 шагов"
