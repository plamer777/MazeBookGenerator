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
    *,
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
    pad = 0.7 * mm
    start_w = c.stringWidth(spec.start_text, ctx.font_bold, font_size)
    finish_w = c.stringWidth(spec.finish_text, ctx.font_bold, font_size)
    horizontal_gap = spec.marker_radius + 1.6 * mm
    vertical_gap = spec.marker_radius + 1.2 * mm

    start_candidates = _label_candidates(spec.start_marker, start_w, horizontal_gap, vertical_gap)
    finish_candidates = _label_candidates(spec.finish_marker, finish_w, horizontal_gap, vertical_gap)

    for start_pos in start_candidates:
        for finish_pos in finish_candidates:
            start_bbox = _label_bbox(start_pos, start_w, pad, font_size)
            finish_bbox = _label_bbox(finish_pos, finish_w, pad, font_size)
            if not _bboxes_overlap(start_bbox, finish_bbox):
                return start_pos, finish_pos

    # Fallback: разносим кандидаты по горизонтали при любом пересечении
    push = 1.8 * mm
    direction = -1 if spec.start_marker[0] <= spec.finish_marker[0] else 1
    start_pos = (start_candidates[0][0] + push * direction, start_candidates[0][1] + 0.8 * mm)
    finish_pos = (finish_candidates[0][0] - push * direction, finish_candidates[0][1] - 0.8 * mm)
    return start_pos, finish_pos



def _label_candidates(marker: tuple[float, float],
    text_w: float,
    horizontal_gap: float,
    vertical_gap: float,
) -> list[tuple[float, float]]:
    """Кандидатные позиции подписи вокруг маркера."""
    mx, my = marker
    return [
        (mx - (horizontal_gap + text_w / 2), my + vertical_gap),
        (mx - (horizontal_gap + text_w / 2), my),
        (mx - (horizontal_gap + text_w / 2), my - vertical_gap),
        (mx, my + 1.5 * vertical_gap),
        (mx, my - 1.5 * vertical_gap),
        (mx + (horizontal_gap + text_w / 2), my + vertical_gap),
    ]



def _label_bbox(pos: tuple[float, float],
    width: float,
    pad: float,
    font_size: float,
) -> tuple[float, float, float, float]:
    """Возвращает bbox подписи как (left, bottom, right, top)."""
    cx, baseline_y = pos
    return (cx - width / 2 - pad, baseline_y - pad,
            cx + width / 2 + pad, baseline_y + font_size * 1.25 + pad)



def _bboxes_overlap(first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    """Проверяет пересечение двух прямоугольников."""
    f_left, f_bottom, f_right, f_top = first
    s_left, s_bottom, s_right, s_top = second
    return not (f_right <= s_left or s_right <= f_left
                or f_top <= s_bottom or s_top <= f_bottom)




def draw_marker_label(ctx: RenderContext, c: canvas.Canvas, x: float, y: float, text: str) -> None:
    """Рисует компактную подпись маркера START/FINISH рядом с треугольником."""
    c.saveState()
    c.setFillColorRGB(0.12, 0.12, 0.12)
    c.setFont(ctx.font_bold, 7.5)
    c.drawCentredString(x, y, text)
    c.restoreState()
