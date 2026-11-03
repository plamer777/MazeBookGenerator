"""Маркеры старта/финиша и их подписи на страницах лабиринтов."""

import math

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.params import MarkerLabelSpec


def draw_triangle_marker(c: canvas.Canvas,
    cx: float,
    cy: float,
    size: float,
    angle: float,
    color: tuple[float, float, float],
) -> None:
    """
    Рисует равносторонний треугольник-маркер.

    Острие указывает в сторону angle, основание позади.

    Args:
        c: Canvas для рисования
        cx: Центр X
        cy: Центр Y
        size: Радиус описанной окружности
        angle: Угол острия (радианы)
        color: RGB-цвет заливки (0..1)
    """
    tip_x = cx + size * math.cos(angle)
    tip_y = cy + size * math.sin(angle)
    left_x = cx + size * math.cos(angle + 2 * math.pi / 3)
    left_y = cy + size * math.sin(angle + 2 * math.pi / 3)
    right_x = cx + size * math.cos(angle - 2 * math.pi / 3)
    right_y = cy + size * math.sin(angle - 2 * math.pi / 3)

    p = c.beginPath()
    p.moveTo(tip_x, tip_y)
    p.lineTo(left_x, left_y)
    p.lineTo(right_x, right_y)
    p.close()
    c.setFillColorRGB(*color)
    c.setStrokeColorRGB(*color)
    c.drawPath(p, fill=1, stroke=0)



def compute_marker_label_positions(ctx: RenderContext,
    c: canvas.Canvas,
    spec: MarkerLabelSpec,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Вычисляет позиции подписей START/FINISH без визуального наложения."""
    font_size = 7.5
    text_height = font_size * 1.25
    pad = 0.7 * mm

    start_w = c.stringWidth(spec.start_text, ctx.font_bold, font_size)
    finish_w = c.stringWidth(spec.finish_text, ctx.font_bold, font_size)

    horizontal_gap = spec.marker_radius + 1.6 * mm
    vertical_gap = spec.marker_radius + 1.2 * mm

    def label_bbox(cx: float, baseline_y: float, width: float) -> tuple[float, float, float, float]:
        """Возвращает bbox подписи как (left, bottom, right, top)."""
        left = cx - width / 2 - pad
        right = cx + width / 2 + pad
        bottom = baseline_y - pad
        top = baseline_y + text_height + pad
        return left, bottom, right, top

    def overlaps(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> bool:
        """Проверяет пересечение двух прямоугольников."""
        f_left, f_bottom, f_right, f_top = first
        s_left, s_bottom, s_right, s_top = second
        return not (
            f_right <= s_left
            or s_right <= f_left
            or f_top <= s_bottom
            or s_top <= f_bottom
        )

    sx, sy = spec.start_marker
    fx, fy = spec.finish_marker

    start_candidates = [
        (sx - (horizontal_gap + start_w / 2), sy + vertical_gap),
        (sx - (horizontal_gap + start_w / 2), sy),
        (sx - (horizontal_gap + start_w / 2), sy - vertical_gap),
        (sx, sy + 1.5 * vertical_gap),
        (sx, sy - 1.5 * vertical_gap),
        (sx + (horizontal_gap + start_w / 2), sy + vertical_gap),
    ]
    finish_candidates = [
        (fx + (horizontal_gap + finish_w / 2), fy + vertical_gap),
        (fx + (horizontal_gap + finish_w / 2), fy),
        (fx + (horizontal_gap + finish_w / 2), fy - vertical_gap),
        (fx, fy + 1.5 * vertical_gap),
        (fx, fy - 1.5 * vertical_gap),
        (fx - (horizontal_gap + finish_w / 2), fy + vertical_gap),
    ]

    for start_pos in start_candidates:
        for finish_pos in finish_candidates:
            start_bbox = label_bbox(start_pos[0], start_pos[1], start_w)
            finish_bbox = label_bbox(finish_pos[0], finish_pos[1], finish_w)
            if not overlaps(start_bbox, finish_bbox):
                return start_pos, finish_pos

    start_pos = start_candidates[0]
    finish_pos = finish_candidates[0]
    push = 1.8 * mm
    if sx <= fx:
        start_pos = (start_pos[0] - push, start_pos[1] + 0.8 * mm)
        finish_pos = (finish_pos[0] + push, finish_pos[1] - 0.8 * mm)
    else:
        start_pos = (start_pos[0] + push, start_pos[1] + 0.8 * mm)
        finish_pos = (finish_pos[0] - push, finish_pos[1] - 0.8 * mm)
    return start_pos, finish_pos



def draw_marker_label(ctx: RenderContext, c: canvas.Canvas, x: float, y: float, text: str) -> None:
    """Рисует компактную подпись маркера START/FINISH рядом с треугольником."""
    c.saveState()
    c.setFillColorRGB(0.12, 0.12, 0.12)
    c.setFont(ctx.font_bold, 7.5)
    c.drawCentredString(x, y, text)
    c.restoreState()

