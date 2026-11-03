"""Общие утилиты: текстовые формы, создание генераторов случайных чисел."""

import random
from typing import Literal

TextCase = Literal["raw", "lower", "upper", "capitalize"]


def plural_form_ru(count: int, forms: tuple[str, str, str]) -> str:
    """
    Возвращает корректную словоформу для русского языка.

    Args:
        count: Число, определяющее форму
        forms: Кортеж из 3 форм в порядке
            (ед. число, 2-4, 5+), например:
            ("лабиринт", "лабиринта", "лабиринтов")

    Returns:
        Подходящая словоформа
    """
    one, few, many = forms
    last2 = count % 100
    last1 = count % 10

    if 11 <= last2 <= 14:
        return many
    if last1 == 1:
        return one
    if 2 <= last1 <= 4:
        return few
    return many


def format_count_with_plural_ru(
    count: int,
    forms: tuple[str, str, str],
    text_case: TextCase = "raw",
) -> str:
    """
    Формирует строку вида "<число> <словоформа>" для русского языка.

    Args:
        count: Количество
        forms: Формы слова для plural_form_ru
        text_case: Преобразование регистра словоформы

    Returns:
        Готовая строка, например "40 лабиринтов"
    """
    noun = plural_form_ru(count, forms)

    if text_case == "lower":
        noun = noun.lower()
    elif text_case == "upper":
        noun = noun.upper()
    elif text_case == "capitalize":
        noun = noun.capitalize()

    return f"{count} {noun}"


def create_rng(seed: int | None = None) -> random.Random:
    """
    Создаёт экземплярный генератор случайных чисел.

    Используется для лабиринтов и декоративных элементов, где нужна
    воспроизводимость по seed и недопустимо изменение глобального
    состояния модуля random.

    Args:
        seed: Зерно генератора (None — непредсказуемая последовательность)

    Returns:
        Независимый экземпляр random.Random
    """
    return random.Random(seed)  # noqa: S311 — криптостойкость не требуется
