"""Тесты ImageGenerator — генерация заглушек-изображений на PIL."""

from pathlib import Path

from PIL import Image

from maze_book_generator.infrastructure.image_generator import ImageGenerator


class TestImageGenerator:
    """Проверяет генерацию обложки и иллюстраций-заглушек."""

    def test_generate_cover_creates_png(self, tmp_path: Path) -> None:
        """Обложка должна сохраняться как валидный PNG заданного размера."""
        output = tmp_path / "cover.png"

        result = ImageGenerator().generate_cover("Test Book", output)

        assert result == output
        with Image.open(output) as img:
            assert img.format == "PNG"
            assert img.size == (1200, 800)

    def test_generate_cover_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Несуществующие родительские директории должны создаваться."""
        output = tmp_path / "nested" / "deep" / "cover.png"

        ImageGenerator().generate_cover("T", output)

        assert output.exists()

    def test_generate_illustration_creates_png(self, tmp_path: Path) -> None:
        """Иллюстрация должна сохраняться как валидный PNG заданного размера."""
        output = tmp_path / "illustration.png"

        result = ImageGenerator().generate_illustration("maze, adventure", output)

        assert result == output
        with Image.open(output) as img:
            assert img.format == "PNG"
            assert img.size == (300, 300)
