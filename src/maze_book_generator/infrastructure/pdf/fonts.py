"""Регистрация шрифтов DejaVu в ReportLab."""

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from maze_book_generator.settings import FONT_DEJAVU_BOLD, FONT_DEJAVU_REGULAR


def register_fonts() -> None:
    """Регистрирует шрифты DejaVu Sans (regular и bold) для PDF."""
    pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_DEJAVU_REGULAR))
    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", FONT_DEJAVU_BOLD))
