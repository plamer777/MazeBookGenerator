"""Работа с иллюстрациями: водяные знаки, маски затухания, коллаж."""

import io
import logging
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.params import Rect
from maze_book_generator.settings import (
    WATERMARK_ALPHA,
    WATERMARK_BG_DIFF_GAIN,
    WATERMARK_BG_DIFF_THRESHOLD,
    WATERMARK_EDGE_FADE_BLUR_RATIO,
    WATERMARK_EDGE_FADE_INSET_RATIO,
)
from maze_book_generator.utils import create_rng

logger = logging.getLogger(__name__)


def render_watermark_image(c: canvas.Canvas,
    image_path: str,
    area: Rect,
    alpha: float = WATERMARK_ALPHA,
) -> None:
    """
    Накладывает иллюстрацию как полупрозрачный водяной знак в центр области лабиринта.

    Изображение масштабируется с сохранением пропорций и центрируется.
    Alpha-канал применяется через Pillow — не требует удаления фона.

    Args:
        c: Canvas для рисования
        image_path: Путь к исходному PNG-файлу
        area: Область размещения watermark
        alpha: Прозрачность (0.0 — невидимо, 1.0 — непрозрачно)
    """
    try:
        img = Image.open(image_path).convert("RGBA")
        img = prepare_watermark_rgba(img, alpha)

        img_ratio = img.width / img.height
        area_ratio = area.width / area.height

        if img_ratio > area_ratio:
            draw_w = area.width
            draw_h = area.width / img_ratio
        else:
            draw_h = area.height
            draw_w = area.height * img_ratio

        draw_x = area.x + (area.width - draw_w) / 2
        draw_y = area.y + (area.height - draw_h) / 2

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        c.drawImage(
            ImageReader(buf),
            draw_x, draw_y,
            width=draw_w, height=draw_h,
            mask="auto",
            preserveAspectRatio=True,
        )
    except (OSError, ValueError) as exc:
        logger.debug("Пропуск watermark-изображения %s: %s", image_path, exc)



def prepare_watermark_rgba(img: Image.Image, alpha: float) -> Image.Image:
    """Подготавливает RGBA-изображение watermark с мягким смешиванием в фоне."""
    rgb = img.convert("RGB")
    r, g, b, src_alpha = img.split()

    scaled_alpha = src_alpha.point(lambda v: int(max(0, min(255, v * alpha))))
    bg_color = estimate_image_background_color(rgb)

    bg_layer = Image.new("RGB", rgb.size, bg_color)
    diff = ImageChops.difference(rgb, bg_layer)
    fg_strength = ImageOps.grayscale(diff)

    threshold = WATERMARK_BG_DIFF_THRESHOLD
    gain = WATERMARK_BG_DIFF_GAIN
    fg_mask = fg_strength.point(
        lambda v: int(max(0, min(255, (v - threshold) * gain)))
    )
    fg_mask = fg_mask.filter(ImageFilter.GaussianBlur(1.2))

    edge_mask = build_edge_fade_mask(rgb.width, rgb.height)
    alpha_mask = ImageChops.multiply(scaled_alpha, fg_mask)
    alpha_mask = ImageChops.multiply(alpha_mask, edge_mask)

    return Image.merge("RGBA", (r, g, b, alpha_mask))



def estimate_image_background_color(img: Image.Image) -> tuple[int, int, int]:
    """Оценивает фон по среднему цвету четырёх углов изображения."""
    w, h = img.size
    sample_points = [
        (0, 0),
        (w - 1, 0),
        (0, h - 1),
        (w - 1, h - 1),
    ]
    samples = [img.getpixel(point) for point in sample_points]
    red = int(sum(pixel[0] for pixel in samples) / len(samples))
    green = int(sum(pixel[1] for pixel in samples) / len(samples))
    blue = int(sum(pixel[2] for pixel in samples) / len(samples))
    return red, green, blue



def build_edge_fade_mask(width: int, height: int) -> Image.Image:
    """Строит маску мягкого затухания по краям (центр читаемее, края прозрачнее)."""
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    inset_x = max(2, int(width * WATERMARK_EDGE_FADE_INSET_RATIO))
    inset_y = max(2, int(height * WATERMARK_EDGE_FADE_INSET_RATIO))
    draw.ellipse(
        (inset_x, inset_y, width - inset_x, height - inset_y),
        fill=255,
    )

    blur_radius = max(2.0, min(width, height) * WATERMARK_EDGE_FADE_BLUR_RATIO)
    return mask.filter(ImageFilter.GaussianBlur(blur_radius))



def render_image_collage(ctx: RenderContext,
    c: canvas.Canvas,
    illustrations_dir: Path,
    alpha: float = WATERMARK_ALPHA,
    seed: int | None = None,
) -> None:
    """
    Рендерит коллаж: 1 крупное изображение по центру + 4 мелких по углам.

    Структура:
    - Центр: одно изображение 62–70% ширины страницы, поворот ±8°.
    - Углы (TL, TR, BL, BR): по одному изображению 20–28% ширины, поворот ±15°.

    Args:
        c: Canvas для рисования
        illustrations_dir: Папка с PNG-файлами
        alpha: Прозрачность изображений (не изменяется)
        seed: Seed для детерминированной вариативности коллажа
    """
    pool = _collage_pool(illustrations_dir, seed)
    if not pool:
        return
    rng = create_rng(seed)
    margin = 12 * mm
    for slot in _collage_slots(pool):
        _draw_collage_item(ctx, c, rng, slot, margin=margin, alpha=alpha)



def _collage_pool(illustrations_dir: Path, seed: int | None) -> list[Path]:
    """Возвращает перемешанный пул изображений на 5 слотов коллажа."""
    if not illustrations_dir.exists():
        return []
    images = list(illustrations_dir.glob("*.png"))
    if not images:
        return []
    rng = create_rng(seed)
    pool = images.copy()
    rng.shuffle(pool)
    while len(pool) < 5:
        pool.append(rng.choice(images))
    return pool



def _collage_slots(pool: list[Path],
) -> list[tuple[Path, tuple[float, float], float, float, tuple[float, float]]]:
    """Слоты коллажа: (img_path, scale_range, cx_frac, cy_frac, angle_range)."""
    return [
        (pool[0], (0.62, 0.70), 0.50, 0.50, (-8.0, 8.0)),
        (pool[1], (0.20, 0.28), 0.0, 1.0, (-15.0, 15.0)),
        (pool[2], (0.20, 0.28), 1.0, 1.0, (-15.0, 15.0)),
        (pool[3], (0.20, 0.28), 0.0, 0.0, (-15.0, 15.0)),
        (pool[4], (0.20, 0.28), 1.0, 0.0, (-15.0, 15.0)),
    ]



def _draw_collage_item(ctx: RenderContext,
    c: canvas.Canvas,
    rng: random.Random,
    slot: tuple[Path, tuple[float, float], float, float, tuple[float, float]],
    *,
    margin: float,
    alpha: float,
) -> None:
    """Рисует одно изображение коллажа: масштаб, поворот, позиция, alpha."""
    img_path, scale_range, cx_frac, cy_frac, angle_range = slot
    pw, ph = ctx.page_width, ctx.page_height
    try:
        img, rot_w, rot_h = _collage_transform(rng, _load_collage_image(img_path, alpha),
                                             scale_range, angle_range, pw)

        jitter_x = rng.uniform(-margin * 0.5, margin * 0.5)
        jitter_y = rng.uniform(-margin * 0.5, margin * 0.5)
        cx = cx_frac * pw + jitter_x
        cy = cy_frac * ph + jitter_y
        if (cx_frac, cy_frac) != (0.5, 0.5):
            # Угловые — прижимаем к краю с отступом
            cx = margin + rot_w / 2 if cx_frac < 0.5 else pw - margin - rot_w / 2
            cy = margin + rot_h / 2 if cy_frac < 0.5 else ph - margin - rot_h / 2
            cx += jitter_x
            cy += jitter_y

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(
            ImageReader(buf),
            cx - rot_w / 2, cy - rot_h / 2,
            width=rot_w, height=rot_h,
            mask="auto",
        )
    except (OSError, ValueError) as exc:
        logger.debug("Пропуск изображения коллажа %s: %s", img_path, exc)



def _collage_transform(rng,
    img: Image.Image,
    scale_range: tuple[float, float],
    angle_range: tuple[float, float],
    page_width: float,
) -> tuple[Image.Image, float, float]:
    """Масштабирует и поворачивает изображение коллажа. Возвращает (img, w, h)."""
    draw_w = page_width * rng.uniform(*scale_range)
    draw_h = draw_w * (img.height / img.width)

    angle = rng.uniform(*angle_range)
    img = img.rotate(angle, expand=True)
    rot_w = draw_w * abs(math.cos(math.radians(angle))) + draw_h * abs(math.sin(math.radians(angle)))
    rot_h = draw_w * abs(math.sin(math.radians(angle))) + draw_h * abs(math.cos(math.radians(angle)))
    return img, rot_w, rot_h



def _load_collage_image(img_path: Path, alpha: float) -> Image.Image:
    """Открывает изображение коллажа и применяет alpha-канал."""
    img = Image.open(img_path).convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda v: int(v * alpha))
    return Image.merge("RGBA", (r, g, b, a))
