"""Доменный пакет генерации лабиринтов.

Одна топология — один конвейер:
- grid-формы (masks → carving → solver → grid.build_*) различаются только фабрикой маски;
- полярный лабиринт (polar.py) — отдельный граф ячеек (кольцо, сектор).
"""

from maze_book_generator.domain.maze.generator import MazeGenerator
from maze_book_generator.domain.maze.polar import PolarTopologyService
from maze_book_generator.domain.maze.types import Cell, Connections, Grid, Mask, Point, Walls

__all__ = [
    "Cell",
    "Connections",
    "Grid",
    "Mask",
    "MazeGenerator",
    "Point",
    "PolarTopologyService",
    "Walls",
]
