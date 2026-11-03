"""Клиент для генерации иллюстраций через бесплатный Pollinations AI API."""

from __future__ import annotations

import logging
import time
import urllib.parse
from pathlib import Path

import httpx

from maze_book_generator.infrastructure.images.providers import (
    generate_batch_with_rate_limit,
)
from maze_book_generator.settings import (
    IMAGE_GENERATOR_PROMPT_TEMPLATE,
    POLLINATIONS_BASE_URL,
    POLLINATIONS_PARAMS,
    POLLINATIONS_RATE_LIMIT_DELAY,
    POLLINATIONS_REQUEST_TIMEOUT,
)


class PollinationsClient:
    """Генерирует иллюстрации через бесплатный Pollinations API (text-to-image)."""

    def __init__(self) -> None:
        """Инициализация клиента с базовым URL и параметрами."""
        self._base_url = POLLINATIONS_BASE_URL
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
                response = httpx.get(url, timeout=POLLINATIONS_REQUEST_TIMEOUT, follow_redirects=True)
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
            except (httpx.HTTPError, OSError) as exc:
                self._logger.warning("Pollinations generation failed: %s", exc)
                if attempt == 0:
                    time.sleep(2)
            else:
                return output_path

        return None

    def generate_book_illustrations(
        self,
        image_keywords: list[list[str]],
        output_paths: list[Path],
    ) -> list[Path | None]:
        """
        Генерирует иллюстрации для страниц книги в заданные файлы.

        Args:
            image_keywords: Список ключевых слов по страницам
            output_paths: Целевые файлы иллюстраций (по одному на страницу)

        Returns:
            Список путей к файлам (None если генерация страницы не удалась)
        """
        return generate_batch_with_rate_limit(
            self.generate_illustration,
            image_keywords,
            output_paths,
            rate_limit_delay=self._rate_limit_delay,
            logger=self._logger,
        )
