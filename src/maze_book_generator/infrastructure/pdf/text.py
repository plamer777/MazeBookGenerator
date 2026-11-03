"""Текстовые утилиты рендеринга: перенос строк и центрированный вывод."""

from reportlab.pdfgen import canvas

from maze_book_generator.infrastructure.pdf.context import RenderContext
from maze_book_generator.infrastructure.pdf.params import TextBlock


def wrap_text_to_width(c: canvas.Canvas, text: str, font_name: str, font_size: float, max_width: float) -> list[str]:
    """Переносит строку на несколько строк так, чтобы каждая помещалась по ширине."""
    words = [part for part in text.split() if part]
    if not words:
        return [text.strip() or ""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if c.stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
            continue

        if c.stringWidth(current, font_name, font_size) > max_width:
            lines.extend(split_long_word(c, current, font_name, font_size, max_width))
        else:
            lines.append(current)
        current = word

    if c.stringWidth(current, font_name, font_size) > max_width:
        lines.extend(split_long_word(c, current, font_name, font_size, max_width))
    else:
        lines.append(current)
    return [line for line in lines if line]



def split_long_word(c: canvas.Canvas, word: str, font_name: str, font_size: float, max_width: float) -> list[str]:
    """Разбивает слишком длинное слово на части, чтобы не выйти за пределы рамки."""
    chunks: list[str] = []
    current = ""
    for char in word:
        candidate = f"{current}{char}"
        if current and c.stringWidth(candidate, font_name, font_size) > max_width:
            chunks.append(current)
            current = char
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [word]



def draw_centered_wrapped_text(ctx: RenderContext,
    c: canvas.Canvas,
    block: TextBlock,
) -> float:
    """Рисует многострочный центрированный текст с переносами и автоподбором размера."""
    current_size = block.font_size

    while current_size >= block.min_font_size:
        lines = wrap_text_lines(c, block.text, block.font_name, current_size, block.max_width)
        current_line_height = block.line_height * (current_size / block.font_size)
        total_height = len(lines) * current_line_height
        if total_height <= block.max_height:
            break
        current_size -= 1

    current_size = max(current_size, block.min_font_size)

    c.setFont(block.font_name, current_size)
    y = block.start_y
    current_line_height = block.line_height * (current_size / block.font_size)

    for line in lines:
        if line:
            lw = c.stringWidth(line, block.font_name, current_size)
            c.drawString((ctx.page_width - lw) / 2, y, line)
        y -= current_line_height

    return y



def wrap_text_lines(c: canvas.Canvas,
    text: str,
    font_name: str,
    font_size: float,
    max_width: float,
) -> list[str]:
    """Разбивает текст на строки с переносами по ширине."""
    c.setFont(font_name, font_size)
    wrapped: list[str] = []

    for paragraph in text.split("\n"):
        if not paragraph.strip():
            wrapped.append("")
            continue

        words = paragraph.split()
        current_line = ""
        for word in words:
            test_line = word if not current_line else f"{current_line} {word}"
            if c.stringWidth(test_line, font_name, font_size) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    wrapped.append(current_line)
                current_line = word

        if current_line:
            wrapped.append(current_line)

    return wrapped

