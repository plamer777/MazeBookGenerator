"""Декоративные элементы страниц: меандр, рамки, орнаменты, уголки."""

from __future__ import annotations

import math
import random

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.drawing.grid import draw_cell_walls
from maze_book_generator.infrastructure.pdf.params import DecoRingSpec, Rect
from maze_book_generator.utils import create_rng

_symbols_big = ["★", "✿", "♥", "♦", "☀", "❤", "✦", "◆"]
_symbols_mid = ["•", "♥", "★", "▲", "✿", "●", "♦", "✶"]
_symbols_small = ["·", "◦", "․", "⋅", "•", "▪"]


def render_maze_band(ctx: RenderContext,
    c: canvas.Canvas,
    y_bottom: float,
    band_h: float,
    cell: float,
    *,
    accent: tuple[float, float, float],
) -> None:
    """
    Рисует горизонтальную полосу с паттерном из лабиринтных ячеек.

    Каждая ячейка случайно имеет 0–3 стены — создаётся визуальный
    лабиринтный узор поверх фона.

    Args:
        ctx: Контекст рендеринга (палитра, размеры страницы, print_friendly)
        c: Canvas
        y_bottom: Нижняя граница полосы
        band_h: Высота полосы
        cell: Размер ячейки
        accent: RGB-цвет линий
    """
    c.setStrokeColorRGB(*accent)
    c.setLineWidth(1.0)
    cols = int(ctx.page_width / cell) + 1
    rows = int(band_h / cell) + 1
    rng = create_rng(int(y_bottom + band_h * 7))
    for row in range(rows):
        for col in range(cols):
            walls = [rng.random() < 0.55 for _ in range(4)]  # верх, право, низ, лево
            draw_cell_walls(c, walls, col * cell, y_bottom + row * cell, cell)



def render_meander_border(ctx: RenderContext,
    c: canvas.Canvas,
    accent: tuple[float, float, float],
) -> None:
    """
    Рисует двойную рамку-меандр по периметру страницы.

    Внешняя рамка — сплошная толстая линия.
    Внутренняя — меандровый орнамент с прямоугольными зубцами.

    Args:
        ctx: Контекст рендеринга (палитра, размеры страницы, print_friendly)
        c: Canvas
        accent: RGB-цвет рамки
    """
    margin = 12 * mm
    inner = 18 * mm
    step = 8 * mm

    # Внешняя рамка
    c.setStrokeColorRGB(*accent)
    c.setLineWidth(1.3 if ctx.print_friendly else 2.5)
    c.rect(margin, margin, ctx.page_width - 2 * margin, ctx.page_height - 2 * margin, fill=0, stroke=1)

    # Внутренняя меандровая рамка
    c.setLineWidth(0.7 if ctx.print_friendly else 1.2)
    path = c.beginPath()
    w = ctx.page_width
    h = ctx.page_height

    pts: list[tuple[float, float]] = [(inner, inner)]
    _meander_side(pts, (inner, inner), (w - inner, inner), (0, 1), step)
    _meander_side(pts, (w - inner, inner), (w - inner, h - inner), (-1, 0), step)
    _meander_side(pts, (w - inner, h - inner), (inner, h - inner), (0, -1), step)
    _meander_side(pts, (inner, h - inner), (inner, inner), (1, 0), step)

    path.moveTo(*pts[0])
    for px, py in pts[1:]:
        path.lineTo(px, py)
    path.close()
    c.drawPath(path, stroke=1, fill=0)



def _meander_side(pts: list[tuple[float, float]],
    start: tuple[float, float],
    end: tuple[float, float],
    normal: tuple[float, float],
    tooth: float,
    *,
    depth: float = 4 * mm,
) -> None:
    """Добавляет зигзагообразные точки одной меандровой стороны к pts."""
    x0, y0 = start
    x1, y1 = end
    nx, ny = normal
    length = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
    dx = (x1 - x0) / length
    dy = (y1 - y0) / length
    pos = 0.0
    state = False
    while pos < length:
        nxt = min(pos + tooth, length)
        pts.append((x0 + dx * nxt + (depth * nx if state else 0),
                    y0 + dy * nxt + (depth * ny if state else 0)))
        if nxt < length:
            pts.append((x0 + dx * nxt + (depth * nx if not state else 0),
                        y0 + dy * nxt + (depth * ny if not state else 0)))
        state = not state
        pos = nxt



def render_corner_ornaments(ctx: RenderContext,
    c: canvas.Canvas,
    accent: tuple[float, float, float],
) -> None:
    """
    Рисует декоративные уголки — квадратные спирали в каждом углу.

    Args:
        ctx: Контекст рендеринга (палитра, размеры страницы, print_friendly)
        c: Canvas
        accent: RGB-цвет орнамента
    """
    c.setStrokeColorRGB(*accent)
    c.setLineWidth(1.0)
    size = 14 * mm
    margin = 14 * mm
    corners = [
        (margin, ctx.page_height - margin, 1, -1),
        (ctx.page_width - margin, ctx.page_height - margin, -1, -1),
        (margin, margin, 1, 1),
        (ctx.page_width - margin, margin, -1, 1),
    ]
    for cx0, cy0, sx, sy in corners:
        step_px = size / 5
        for i in range(4):
            r = size - i * step_px
            if r <= 0:
                break
            c.rect(cx0 - r * sx / 2, cy0 - r * sy / 2, r * sx, r * sy, fill=0, stroke=1)




def render_page_corner_deco(ctx: RenderContext,
    c: canvas.Canvas,
    accent: tuple[float, float, float],
    page_seed: int = 0,
) -> None:
    """
    Рисует декоративные элементы по всему периметру страницы: 2 слоя.

    Слой 1 (внешний) — крупные символы у рамки, в углах и по бокам.
    Слой 2 (внутренний) — меньшие символы с отступом, не заезжают в зону лабиринта.
    Чередование символов и цветов рандомное по номеру страницы.

    Args:
        ctx: Контекст рендеринга (палитра, размеры страницы, print_friendly)
        c: Canvas
        accent: Базовый акцентный цвет
        page_seed: Номер страницы для уникального seed
    """
    rng = create_rng(page_seed * 997 + 13)

    colors = [
        accent,
        (0.95, 0.35, 0.35),
        (0.30, 0.75, 0.45),
        (0.35, 0.55, 0.95),
        (0.95, 0.70, 0.20),
        (0.80, 0.45, 0.90),
        (0.25, 0.80, 0.85),
        (0.95, 0.55, 0.25),
    ]

    placer = _EdgePlacer(ctx, c)
    header_bottom = ctx.page_height - placer.frame_m - 32 * mm

    # Слой 1 (внешний): крупные углы + средние символы по периметру
    corner_pad = 9 * mm
    for cx, cy in _corner_positions(ctx, placer.frame_m, corner_pad):
        placer.draw(rng.choice(_symbols_big), cx, cy, 22, rng.choice(colors))

    _scatter_ring(placer, rng, colors, DecoRingSpec(
        edge_offset=7 * mm,
        start_pad=corner_pad,
        step=18 * mm,
        size=16,
        y_limit=header_bottom,
        symbols=_symbols_mid,
    ))

    # Слой 2 (внутренний): мелкие символы с большим отступом от рамки
    offset2 = 16 * mm
    _scatter_ring(placer, rng, colors, DecoRingSpec(
        edge_offset=offset2,
        start_pad=offset2,
        step=22 * mm,
        size=11,
        y_limit=header_bottom - offset2,
        symbols=_symbols_small,
    ))



def _corner_positions(ctx: RenderContext, frame_m: float, pad: float) -> list[tuple[float, float]]:
    """Координаты четырёх углов внутренней рамки страницы."""
    return [
        (frame_m + pad, ctx.page_height - frame_m - pad),
        (ctx.page_width - frame_m - pad, ctx.page_height - frame_m - pad),
        (frame_m + pad, frame_m + pad),
        (ctx.page_width - frame_m - pad, frame_m + pad),
    ]



def _scatter_ring(placer: _EdgePlacer,
    rng: random.Random,
    colors: list[tuple[float, float, float]],
    spec: DecoRingSpec,
) -> None:
    """Раскидывает символы по четырём сторонам рамки одного декоративного слоя."""
    frame_m = placer.frame_m
    x = frame_m + spec.start_pad + spec.step
    while x < placer.page_width - frame_m - spec.start_pad:
        placer.draw(rng.choice(spec.symbols), x, placer.page_height - frame_m - spec.edge_offset, spec.size, rng.choice(colors))
        placer.draw(rng.choice(spec.symbols), x, frame_m + spec.edge_offset, spec.size, rng.choice(colors))
        x += spec.step

    y = frame_m + spec.start_pad + spec.step
    while y < spec.y_limit:
        placer.draw(rng.choice(spec.symbols), frame_m + spec.edge_offset, y, spec.size, rng.choice(colors))
        placer.draw(rng.choice(spec.symbols), placer.page_width - frame_m - spec.edge_offset, y, spec.size, rng.choice(colors))
        y += spec.step



class _EdgePlacer:
    """Размещает декоративные символы, пропуская зону лабиринта."""

    def __init__(self, ctx: RenderContext, c: canvas.Canvas) -> None:
        self._ctx = ctx
        self._c = c
        self.frame_m = 8 * mm
        # Зона лабиринта: 20mm от рамки по бокам, верх ограничен плашкой заголовка
        self._bounds = Rect(
            x=self.frame_m + 20 * mm,
            y=self.frame_m + 20 * mm,
            width=ctx.page_width - 2 * (self.frame_m + 20 * mm),
            height=ctx.page_height - self.frame_m - 32 * mm - self.frame_m - 20 * mm,
        )

    @property
    def page_width(self) -> float:
        """Ширина страницы."""
        return self._ctx.page_width

    @property
    def page_height(self) -> float:
        """Высота страницы."""
        return self._ctx.page_height

    def draw(self, sym: str, x: float, y: float, size: float,
             color: tuple[float, float, float]) -> None:
        """Рисует символ, если он не попадает в зону лабиринта."""
        b = self._bounds
        if b.x < x < b.x + b.width and b.y < y < b.y + b.height:
            return
        self._c.setFillColorRGB(*color)
        self._c.setFont(self._ctx.font_bold, size)
        self._c.drawCentredString(x, y - size * 0.3, sym)
