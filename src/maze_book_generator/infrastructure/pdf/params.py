"""Параметр-объекты для функций рендеринга PDF."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    """Прямоугольная область страницы в пунктах (left-bottom origin)."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class MazeDrawParams:
    """Флаги отрисовки лабиринта."""

    show_solution: bool = False
    show_labels: bool = False


@dataclass(frozen=True)
class TextBlock:
    """Параметры центрированного многострочного текстового блока."""

    text: str
    font_name: str
    font_size: float
    start_y: float
    max_width: float
    line_height: float
    max_height: float
    min_font_size: float = 10


@dataclass(frozen=True)
class MarkerLabelSpec:
    """Спецификация подписей для маркеров старта и финиша."""

    start_marker: tuple[float, float]
    finish_marker: tuple[float, float]
    start_text: str
    finish_text: str
    marker_radius: float


@dataclass(frozen=True)
class DecoRingSpec:
    """Параметры кольца декоративных символов по периметру страницы."""

    edge_offset: float
    start_pad: float
    step: float
    size: float
    y_limit: float
    symbols: list[str]


@dataclass(frozen=True)
class PolarView:
    """Геометрия полярного лабиринта на странице."""

    center_x: float
    center_y: float
    max_radius: float


@dataclass(frozen=True)
class BorderSideSpec:
    """Спецификация одной стороны рваной рамки лабиринта."""

    start: tuple[float, float]
    end: tuple[float, float]
    horizontal: bool
    direction: int
    indent_direction: int
    min_indent: float
    max_indent: float
