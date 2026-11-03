"""Клиент для генерации иллюстраций через бесплатный Pollinations AI API."""

from __future__ import annotations

import logging
import time
import urllib.parse
from pathlib import Path

import httpx

from maze_book_generator.settings import (
    IMAGE_GENERATOR_PROMPT_TEMPLATE,
    IMAGE_STORAGE_SUBDIR,
    POLLINATIONS_PARAMS,
    POLLINATIONS_RATE_LIMIT_DELAY,
)


class PollinationsClient:
    """Генерирует иллюстрации через бесплатный Pollinations API (text-to-image)."""

    def __init__(self) -> None:
        """Инициализация клиента с базовым URL и параметрами."""
        self._base_url = "https://image.pollinations.ai/prompt"
        self._rate_limit_delay = POLLINATIONS_RATE_LIMIT_DELAY
        self._logger = logging.getLogger(__name__)

    def _build_prompt(self, keywords: list[str]) -> str:
        """
        Формирует промпт для модели на основе ключевых слов.

        Args:
            keywords: Список ключевых слов для иллюстрации

        Returns:
            Готовый текстовый промпт
        """
        return IMAGE_GENERATOR_PROMPT_TEMPLATE.format(keywords=", ".join(keywords))

    def _build_url(self, prompt: str) -> str:
        """Формирует URL для запроса к Pollinations с параметрами."""
        encoded = urllib.parse.quote(prompt)
        params = urllib.parse.urlencode(POLLINATIONS_PARAMS)
        return f"{self._base_url}/{encoded}?{params}"

    def generate_illustration(
        self,
        keywords: list[str],
        output_path: Path,
    ) -> Path | None:
        """
        Генерирует одну иллюстрацию через Pollinations и сохраняет в output_path.

        Args:
            keywords: Ключевые слова для промпта
            output_path: Путь для сохранения файла (.png)

        Returns:
            Путь к сохранённому файлу или None при ошибке
        """
        prompt = self._build_prompt(keywords)
        output_path = output_path.with_suffix(".png")
        url = self._build_url(prompt)

        for attempt in range(2):
            try:
                response = httpx.get(url, timeout=60, follow_redirects=True)
                response.raise_for_status()

                # Pollinations может вернуть ошибку внутри JSON даже при 200
                content_type = response.headers.get("content-type", "")
                if "image" not in content_type and len(response.content) < 1000:
                    self._logger.warning(
                        "Pollinations returned non-image content for %s (type=%s)",
                        output_path, content_type,
                    )
                    return None

                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(response.content)
                return output_path

            except Exception as exc:
                self._logger.warning("Pollinations generation failed: %s", exc)
                if attempt == 0:
                    time.sleep(2)

        return None

    def generate_book_illustrations(
        self,
        image_keywords: list[list[str]],
        book_dir: Path,
    ) -> list[Path | None]:
        """
        Генерирует иллюстрации для всех страниц книги.

        Args:
            image_keywords: Список ключевых слов по страницам
            book_dir: Директория книги (illustrations/page_N.png)

        Returns:
            Список путей к файлам (None если генерация страницы не удалась)
        """
        illustrations_dir = book_dir / IMAGE_STORAGE_SUBDIR
        results: list[Path | None] = []

        for idx, keywords in enumerate(image_keywords):
            output_path = illustrations_dir / f"page_{idx + 1}.png"
            self._logger.info("Generating illustration %d/%d...", idx + 1, len(image_keywords))
            path = self.generate_illustration(keywords, output_path)
            results.append(path)
            # Pollinations rate limit ~6 requests/minute
            if idx < len(image_keywords) - 1:
                time.sleep(self._rate_limit_delay)

        return results
