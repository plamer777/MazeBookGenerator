"""Клиент для генерации иллюстраций через Hugging Face Inference API."""

from __future__ import annotations

import logging
from pathlib import Path
from time import sleep

import requests

from maze_book_generator.infrastructure.images.providers import (
    generate_batch_with_rate_limit,
)
from maze_book_generator.settings import (
    HF_API_BASE_URL,
    HF_IMAGE_MODEL_FALLBACKS,
    HF_RATE_LIMIT_DELAY,
    HF_REQUEST_TIMEOUT,
    IMAGE_GENERATOR_PROMPT_TEMPLATE,
    settings,
)

_logger = logging.getLogger(__name__)


class HFClient:
    """Генерирует иллюстрации через Hugging Face Inference API (text-to-image)."""

    def __init__(self) -> None:
        """Инициализация клиента с токеном из settings."""
        self._headers = {"Authorization": f"Bearer {settings.HF_TOKEN}"}

    def _build_prompt(self, keywords: list[str]) -> str:
        """
        Формирует промпт для модели на основе ключевых слов.

        Args:
            keywords: Список ключевых слов для иллюстрации

        Returns:
            Готовый текстовый промпт
        """
        return IMAGE_GENERATOR_PROMPT_TEMPLATE.format(keywords=", ".join(keywords))

    def generate_illustration(
        self,
        keywords: list[str],
        output_path: Path,
    ) -> Path | None:
        """
        Генерирует одну иллюстрацию и сохраняет её в output_path (.png).

        Args:
            keywords: Ключевые слова для промпта
            output_path: Путь для сохранения файла

        Returns:
            Путь к сохранённому файлу или None при ошибке
        """
        prompt = self._build_prompt(keywords)
        output_path = output_path.with_suffix(".png")

        for model in HF_IMAGE_MODEL_FALLBACKS:
            url = HF_API_BASE_URL + model
            for attempt in range(2):
                try:
                    resp = requests.post(
                        url,
                        headers=self._headers,
                        json={"inputs": prompt},
                        timeout=HF_REQUEST_TIMEOUT,
                    )
                    # 402/429 — квота исчерпана, переходим к следующей модели
                    if resp.status_code in (402, 429):
                        _logger.warning(
                            "Model %s unavailable (%s), trying next",
                            model, resp.status_code,
                        )
                        break
                    resp.raise_for_status()

                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(resp.content)
                except (requests.RequestException, OSError) as exc:
                    _logger.warning(
                        "HF image generation failed [%s, attempt %d]: %s",
                        model, attempt + 1, exc,
                    )
                    if attempt == 0:
                        sleep(2)
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
            rate_limit_delay=HF_RATE_LIMIT_DELAY,
            logger=_logger,
        )
