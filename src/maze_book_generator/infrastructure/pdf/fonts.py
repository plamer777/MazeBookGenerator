"""Регистрация шрифтов DejaVu в ReportLab."""

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from maze_book_generator.infrastructure.fonts import (
    find_dejavu_bold,
    find_dejavu_regular,
)


def register_fonts() -> None:
    """
    Регистрирует шрифты DejaVu Sans (regular и bold) для PDF.

    Ищет шрифты по кандидатным путям (Linux/macOS/Windows). Если DejaVu
    не найден — бросает FileNotFoundError с подсказкой по установке,
    т.к. без Unicode-шрифта кириллица в PDF не отрисуется.
    """
    regular = find_dejavu_regular()
    bold = find_dejavu_bold()
    if regular is None or bold is None:
        msg = (
            "Шрифты DejaVu не найдены. Установите пакет fonts-dejavu "
            "(Linux: apt install fonts-dejavu, macOS: brew install --cask font-dejavu)"
        )
        raise FileNotFoundError(msg)
    pdfmetrics.registerFont(TTFont("DejaVuSans", regular))
    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold))
