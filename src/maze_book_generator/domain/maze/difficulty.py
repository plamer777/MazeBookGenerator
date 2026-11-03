"""Параметрическая шкала сложности генерации лабиринтов."""

from maze_book_generator.domain.models import Difficulty
from maze_book_generator.settings import (
    EFFECTIVE_LEVEL_MAX,
    EFFECTIVE_LEVEL_MIN,
    EFFECTIVE_LEVEL_POWER,
)


def lerp(level: float, lo: float, hi: float) -> float:
    """
    Линейная интерполяция параметра по уровню сложности 1-7.

    Args:
        level: Уровень 1..7 (допускается float)
        lo: Значение для уровня 1
        hi: Значение для уровня 7

    Returns:
        Интерполированное значение между lo и hi
    """
    return lo + (hi - lo) * (level - 1) / 6.0


def effective_level(difficulty: Difficulty) -> float:
    """
    Перекалиброванный уровень сложности для более плавной градации.

    Цели:
    - поднять минимальный порог (L1 ≈ прежний L3–L4),
    - сохранить верхнюю границу L7 = 7.0 без изменений,
    - сделать шаги между уровнями плавными через степенную кривую
      (power < 1 даёт concave-профиль: нижние уровни поднимаются сильно,
      верхние почти не затрагиваются).

    Таблица значений (lo=3.5, hi=7.0, power=0.55):
        L1 → 3.50  |  L2 → 4.27  |  L3 → 4.90
        L4 → 5.44  |  L5 → 5.93  |  L6 → 6.47  |  L7 → 7.00

    Returns:
        Эффективный уровень в диапазоне [3.5 .. 7.0]
    """
    lvl = difficulty.level
    t = (lvl - 1) / 6.0  # нормированное значение 0..1
    return EFFECTIVE_LEVEL_MIN + (EFFECTIVE_LEVEL_MAX - EFFECTIVE_LEVEL_MIN) * (t ** EFFECTIVE_LEVEL_POWER)
