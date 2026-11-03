"""Клиент для генерации иллюстраций через Hugging Face Inference API."""

from __future__ import annotations

import logging
from pathlib import Path
from time import sleep

import requests

from maze_book_generator.settings import (
    HF_IMAGE_MODEL_FALLBACKS,
    IMAGE_GENERATOR_PROMPT_TEMPLATE,
    IMAGE_STORAGE_SUBDIR,
    settings,
)

_HF_API_BASE = "https://router.huggingface.co/hf-inference/models/"
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
            url = _HF_API_BASE + model
            for attempt in range(2):
                try:
                    resp = requests.post(
                        url,
                        headers=self._headers,
                        json={"inputs": prompt},
                        timeout=120,
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
                    return output_path

                except Exception as exc:
                    _logger.warning(
                        "HF image generation failed [%s, attempt %d]: %s",
                        model, attempt + 1, exc,
                    )
                    if attempt == 0:
                        sleep(2)
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
            path = self.generate_illustration(keywords, output_path)
            results.append(path)

        return results
