"""Генератор preview изображений в книжном стиле."""

import math
from pathlib import Path
from typing import Optional

from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFilter


class PreviewGenerator:
    """
    Генератор премиальных preview изображений для детских книг.

    Создаёт виды для маркетплейсов на красивом светлом детском столе:
    - preview_cover.png: миниатюра обложки
    - preview_page_N.png: миниатюры страниц
    - preview_spread.png: обложка и листы, естественно разложенные на столе
    - preview_collage.png: аккуратная сетка 2×2 (cover + 3 страницы)
    - preview_answer.png: демонстрация страницы с ответами
    - preview_promo.png: продающий промо-баннер со стикером
    """

    CANVAS_W: int = 1200
    CANVAS_H: int = 800

    # Цвет детского столика (нежный, теплый пастельно-кремовый оттенок)
    TABLE_COLOR: tuple[int, int, int] = (248, 246, 240)
    # Цвет линий стыка деревянных планок стола
    PLANK_LINE_COLOR: tuple[int, int, int] = (236, 233, 224)

    def __init__(self) -> None:
        """Инициализация генератора."""
        self.preview_width = 600
        self.preview_height = 400

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def generate_previews(self, output_dir: Path) -> list[Path]:
        """
        Генерирует полный расширенный пакет preview изображений для книги.
        """
        paths: list[Path] = []

        # Загружаем обложку и страницы
        cover_img = self._load_cover(output_dir)
        page_imgs = self._load_pages_from_pdf(output_dir, count=4)
        solution_img = self._load_solution_page(output_dir)

        # 1. Индивидуальные миниатюры
        if cover_img is not None:
            p = output_dir / "preview_cover.png"
            self._save_thumbnail(cover_img, p)
            paths.append(p)

        for i, pimg in enumerate(page_imgs[:3]):
            p = output_dir / f"preview_page_{i + 1}.png"
            self._save_thumbnail(pimg, p)
            paths.append(p)

        # 2. Обновленный разворот на деревянном столе (БЕЗ черных квадратов)
        spread_path = output_dir / "preview_spread.png"
        self._generate_book_spread(cover_img, page_imgs, spread_path)
        paths.append(spread_path)

        # 3. Сетка 2×2
        collage_path = output_dir / "preview_collage.png"
        self._generate_collage(cover_img, page_imgs[:3], collage_path)
        paths.append(collage_path)

        # 4. Превью страницы ответов
        if solution_img is not None:
            answer_path = output_dir / "preview_answer.png"
            self._generate_answer_preview(solution_img, answer_path)
            paths.append(answer_path)

        # 5. Продающий промо-баннер со стикером
        if cover_img is not None:
            promo_path = output_dir / "preview_promo.png"
            self._generate_promo_banner(cover_img, page_imgs, promo_path)
            paths.append(promo_path)

        return paths

    # ------------------------------------------------------------------
    # Загрузка исходников
    # ------------------------------------------------------------------

    def _load_cover(self, output_dir: Path) -> Optional[Image.Image]:
        """Загружает обложку. Если cover.png нет, берет стр 0 из PDF."""

        pdf_path = output_dir / "book.pdf"
        if pdf_path.exists():
            try:
                images = convert_from_path(str(pdf_path), dpi=150, first_page=1, last_page=1)
                if images:
                    return images[0].convert("RGB")
            except Exception:
                pass
        return None

    def _load_pages_from_pdf(self, output_dir: Path, count: int = 4) -> list[Image.Image]:
        """Загружает обычные страницы лабиринтов из PDF."""
        pdf_path = output_dir / "book.pdf"
        if not pdf_path.exists():
            return [self._make_placeholder(i + 1) for i in range(count)]

        try:
            images = convert_from_path(str(pdf_path), dpi=150)
            available = list(range(1, max(1, len(images) - 3)))
            if not available:
                available = list(range(1, len(images)))

            result: list[Image.Image] = []
            for i in range(count):
                idx = available[min(i * max(1, len(available) // count), len(available) - 1)]
                result.append(images[idx].convert("RGB"))
            return result
        except Exception:
            return [self._make_placeholder(i + 1) for i in range(count)]

    def _load_solution_page(self, output_dir: Path) -> Optional[Image.Image]:
        """Загружает страницу с ответами (последняя страница PDF)."""
        pdf_path = output_dir / "book.pdf"
        if not pdf_path.exists():
            return None
        try:
            images = convert_from_path(str(pdf_path), dpi=150)
            if len(images) > 1:
                return images[-1].convert("RGB")
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Генерация макетов
    # ------------------------------------------------------------------

    def _generate_book_spread(
        self,
        cover: Optional[Image.Image],
        pages: list[Image.Image],
        output_path: Path,
    ) -> None:
        """Создаёт красивый реалистичный разворот страниц на детском столе."""
        canvas = Image.new("RGB", (self.CANVAS_W, self.CANVAS_H), self.TABLE_COLOR)
        self._draw_wood_table_texture(canvas)

        cx = self.CANVAS_W // 2
        cy = self.CANVAS_H // 2

        # Оптимальные размеры страниц для разворота
        page_h = int(self.CANVAS_H * 0.50)
        page_w = int(page_h * 210 / 297) if (pages and pages[0].height > pages[0].width) else int(page_h * 297 / 210)

        # Координаты веера страниц вокруг центра
        layout: list[tuple[float, int, int]] = [
            (-14, -int(self.CANVAS_W * 0.23), -int(self.CANVAS_H * 0.12)),  # Верхняя левая
            ( 12,  int(self.CANVAS_W * 0.23), -int(self.CANVAS_H * 0.10)),  # Верхняя правая
            ( -8, -int(self.CANVAS_W * 0.21),  int(self.CANVAS_H * 0.14)),  # Нижняя левая
            ( 15,  int(self.CANVAS_W * 0.22),  int(self.CANVAS_H * 0.12)),  # Нижняя правая
        ]

        for i, (angle, dx, dy) in enumerate(layout):
            src = pages[i] if i < len(pages) else self._make_placeholder(i + 1)
            pimg = self._fit_image(src, page_w, page_h)
            pw, ph = pimg.size
            px = cx + dx - pw // 2
            py = cy + dy - ph // 2
            # Смещение тени небольшое, создающее эффект плотно лежащего листа
            self._paste_with_shadow(canvas, pimg, px, py, angle=angle, shadow_offset=12)

        # Центральная обложка (крупнее остальных)
        cover_h = int(self.CANVAS_H * 0.56)
        cover_w = int(cover_h * 210 / 297) if (cover and cover.height > cover.width) else int(cover_h * 297 / 210)
        cover_src = cover if cover is not None else self._make_placeholder(0)
        cover_img = self._fit_image(cover_src, cover_w, cover_h)
        cw, ch = cover_img.size
        cover_x = cx - cw // 2
        cover_y = cy - ch // 2

        # Обложка приподнята повыше, поэтому у неё тень глубже (offset=20)
        self._paste_with_shadow(canvas, cover_img, cover_x, cover_y, angle=2, shadow_offset=20)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, "PNG", quality=95)

    def _generate_collage(
        self,
        cover: Optional[Image.Image],
        pages: list[Image.Image],
        output_path: Path,
    ) -> None:
        """Создаёт аккуратный заполненный коллаж 2×2."""
        gap = 12
        collage = Image.new("RGB", (self.CANVAS_W, self.CANVAS_H), (235, 235, 240))

        sources: list[Image.Image] = []
        sources.append(cover if cover is not None else self._make_placeholder(0))
        for i in range(3):
            sources.append(pages[i] if i < len(pages) else self._make_placeholder(i + 1))

        positions = [
            (gap, gap),
            (self.CANVAS_W // 2 + gap // 2, gap),
            (gap, self.CANVAS_H // 2 + gap // 2),
            (self.CANVAS_W // 2 + gap // 2, self.CANVAS_H // 2 + gap // 2),
        ]

        for src, (px, py) in zip(sources, positions):
            cell = self._fit_to_cell(src, self.CANVAS_W // 2 - int(gap * 1.5), self.CANVAS_H // 2 - int(gap * 1.5))
            collage.paste(cell, (px, py))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        collage.save(output_path, "PNG", quality=95)

    def _generate_answer_preview(self, solution_page: Image.Image, output_path: Path) -> None:
        """Создаёт превью страницы ответов на детском столике."""
        canvas = Image.new("RGB", (self.CANVAS_W, self.CANVAS_H), self.TABLE_COLOR)
        self._draw_wood_table_texture(canvas)

        page_h = int(self.CANVAS_H * 0.75)
        page_w = int(page_h * 210 / 297) if solution_page.height > solution_page.width else int(page_h * 297 / 210)

        pimg = self._fit_image(solution_page, page_w, page_h)
        pw, ph = pimg.size
        px = self.CANVAS_W // 2 - pw // 2
        py = self.CANVAS_H // 2 - ph // 2

        self._paste_with_shadow(canvas, pimg, px, py, angle=-3, shadow_offset=16)

        # Маркетинговый стикер в углу страницы
        self._draw_marketing_badge(canvas, "SOLUTIONS", "INCLUDED!", x=self.CANVAS_W - 220, y=180, color=(235, 70, 50))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, "PNG", quality=95)

    def _generate_promo_banner(self, cover: Image.Image, pages: list[Image.Image], output_path: Path) -> None:
        """Создаёт рекламный баннер для маркетплейса."""
        canvas = Image.new("RGB", (self.CANVAS_W, self.CANVAS_H), self.TABLE_COLOR)
        self._draw_wood_table_texture(canvas)

        page_h = int(self.CANVAS_H * 0.65)
        page_w = int(page_h * 210 / 297) if cover.height > cover.width else int(page_h * 297 / 210)

        if pages:
            pimg = self._fit_image(pages[0], page_w, page_h)
            self._paste_with_shadow(canvas, pimg, 180, 160, angle=8, shadow_offset=12)

        cimg = self._fit_image(cover, page_w, page_h)
        self._paste_with_shadow(canvas, cimg, 140, 130, angle=-1, shadow_offset=22)

        # Большой привлекающий внимание бейдж справа
        self._draw_marketing_badge(canvas, "50+ MAZES", "AGES 4-8", x=860, y=400, radius=170, color=(255, 130, 0))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, "PNG", quality=95)

    # ------------------------------------------------------------------
    # Отрисовка фона и текстуры стола
    # ------------------------------------------------------------------

    def _draw_wood_table_texture(self, canvas: Image.Image) -> None:
        """
        Программно генерирует премиальную матовую текстуру светлого детского стола.
        Рисует продольные деревянные планки и добавляет мягкую световую виньетку.
        """
        draw = ImageDraw.Draw(canvas)

        # 1. Нарезаем стол на продольные деревянные доски (ширина доски 140px)
        plank_width = 140
        for x in range(0, self.CANVAS_W, plank_width):
            # Проводим аккуратную тонкую линию стыка досок
            draw.line([(x, 0), (x, self.CANVAS_H)], fill=self.PLANK_LINE_COLOR, width=2)

        # 2. Накладываем эффект мягкого студийного освещения (виньетка)
        # Центр кадра слегка подсвечиваем, а края уводим в мягкий уютный тон
        overlay = Image.new("RGBA", (self.CANVAS_W, self.CANVAS_H), (0, 0, 0, 0))
        o_draw = ImageDraw.Draw(overlay)

        cx, cy = self.CANVAS_W // 2, self.CANVAS_H // 2
        max_r = int(math.hypot(cx, cy))

        for r in range(max_r, 0, -8):
            t = r / max_r
            # К краям добавляем капельку затемнения для объема (альфа падает к центру)
            alpha = int(22 * t)
            o_draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(210, 205, 195, alpha))

        canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB"))

    def _paste_with_shadow(
        self,
        canvas: Image.Image,
        img: Image.Image,
        x: int,
        y: int,
        angle: float = 0,
        shadow_offset: int = 12,
    ) -> None:
        """
        Идеальное наложение объекта с поворотом и реалистичной тенью.
        ПОЛНОСТЬЮ ИСКЛЮЧАЕТ ЧЕРНЫЕ КВАДРАТЫ вокруг повернутых листов за счет RGBA.
        """
        # ШАГ 1: Переводим исходный лист в RGBA ДО ПОВОРОТА.
        # Теперь PIL заполнит углы при расширении полностью прозрачными пикселями (0,0,0,0)
        rgba_img = img.convert("RGBA")
        rotated = rgba_img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        rw, rh = rotated.size

        # ШАГ 2: Извлекаем чистую маску прозрачности повернутого листа (альфа-канал)
        # Это гарантирует, что форма тени идеально повторяет контуры листа
        alpha_channel = rotated.split()[3]

        # ШАГ 3: Создаем холст для тени с запасом под размытие
        pad = shadow_offset * 3
        shadow_mask = Image.new("L", (rw + pad * 2, rh + pad * 2), 0)
        shadow_mask.paste(alpha_channel, (pad, pad))

        # Размываем маску для создания эффекта мягкого рассеянного света
        shadow_blurred = shadow_mask.filter(ImageFilter.GaussianBlur(radius=shadow_offset))

        # Создаем полупрозрачный цвет тени (мягкий серо-коричневый, гармонирующий со столом)
        shadow_color = Image.new("RGBA", shadow_blurred.size, (50, 48, 45, 40)) # Альфа 40 — очень мягкая натуральная тень

        # Собираем финальный слой тени
        shadow_final = Image.new("RGBA", shadow_blurred.size, (0, 0, 0, 0))
        shadow_final.paste(shadow_color, (0, 0), mask=shadow_blurred)

        # ШАГ 4: Рассчитываем физическое смещение тени (свет падает чуть сверху-слева)
        sx = x - pad + int(shadow_offset * 0.5)
        sy = y - pad + int(shadow_offset * 1.0)

        # Накладываем сначала тень на основной холст через альфа-композицию
        canvas_rgba = canvas.convert("RGBA")
        canvas_rgba.paste(shadow_final, (sx, sy), mask=shadow_final)

        # ШАГ 5: Накладываем сам повернутый лист, используя его же альфу как маску
        canvas_rgba.paste(rotated, (x, y), mask=rotated)

        # Возвращаем результат в основной RGB холст
        canvas.paste(canvas_rgba.convert("RGB"))

    # ------------------------------------------------------------------
    # Маркетинговые элементы и утилиты
    # ------------------------------------------------------------------

    def _draw_marketing_badge(
        self,
        canvas: Image.Image,
        text1: str,
        text2: str,
        x: int,
        y: int,
        radius: int = 110,
        color: tuple[int, int, int] = (255, 120, 0)
    ) -> None:
        """Рисует объемный круглый стикер с кантиком и аккуратной тенью."""
        badge_canvas = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(badge_canvas)

        # Тень стикера
        b_draw.ellipse([(x - radius + 6, y - radius + 10), (x + radius + 6, y + radius + 10)], fill=(40, 38, 35, 35))
        badge_canvas = badge_canvas.filter(ImageFilter.GaussianBlur(radius=6))
        canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), badge_canvas).convert("RGB"))

        # Круг стикера
        draw = ImageDraw.Draw(canvas)
        draw.ellipse([(x - radius, y - radius), (x + radius, y + radius)], fill=color)
        draw.ellipse([(x - radius + 8, y - radius + 8), (x + radius - 8, y + radius - 8)], outline=(255, 255, 255), width=3)

        # Отрисовка текста по центру бейджа
        draw.text((x - len(text1) * 5, y - 24), text1, fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))
        draw.text((x - len(text2) * 5, y + 4), text2, fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))

    def _fit_to_cell(self, img: Image.Image, cell_w: int, cell_h: int) -> Image.Image:
        """Вписывает изображение внутрь ячейки коллажа."""
        cell = Image.new("RGB", (cell_w, cell_h), (255, 255, 255))
        fitted = self._fit_image(img, cell_w, cell_h)
        fw, fh = fitted.size
        ox = (cell_w - fw) // 2
        oy = (cell_h - fh) // 2
        cell.paste(fitted, (ox, oy))
        return cell

    def _fit_image(self, img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """Масштабирует изображение с сохранением пропорций."""
        src_w, src_h = img.size
        scale = min(target_w / src_w, target_h / src_h)
        return img.resize((max(1, int(src_w * scale)), max(1, int(src_h * scale))), Image.Resampling.LANCZOS)

    def _save_thumbnail(self, img: Image.Image, path: Path) -> None:
        """Сохраняет уменьшенную копию."""
        thumb = self._fit_image(img, self.preview_width, self.preview_height)
        path.parent.mkdir(parents=True, exist_ok=True)
        thumb.save(path, "PNG")

    def _make_placeholder(self, page_num: int, width: Optional[int] = None, height: Optional[int] = None) -> Image.Image:
        """Генерирует чистый плейсхолдер страницы."""
        w = width or self.preview_width
        h = height or self.preview_height
        img = Image.new("RGB", (w, h), color=(245, 245, 250))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(8, 8), (w - 8, h - 8)], outline=(210, 212, 220), width=2)
        label = f"Page {page_num}" if page_num > 0 else "Cover Template"
        draw.text((w // 2 - 35, h // 2 - 6), label, fill=(130, 135, 150))
        return img