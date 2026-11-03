"""Пакет рендеринга PDF книг лабиринтов.

Структура: facade PDFRenderer (renderer.py) собирает документ из страниц,
RenderContext несёт общие параметры, отрисовка лабиринтов — в drawing/.
"""

from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.renderer import PDFRenderer

__all__ = ["PDFRenderer", "RenderContext"]
