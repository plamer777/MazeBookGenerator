"""Клиент для генерации иллюстраций через Replicate API."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx
import replicate

from maze_book_generator.settings import (
    IMAGE_GENERATOR_PROMPT_TEMPLATE,
    IMAGE_STORAGE_SUBDIR,
    REPLICATE_DOWNLOAD_TIMEOUT,
    REPLICATE_IMAGE_MODELS,
    REPLICATE_IMAGE_PARAMS,
    REPLICATE_RATE_LIMIT_DELAY,
    settings,
)


class ReplicateClient:
    """Генерирует иллюстрации через Replicate API (text-to-image)."""

    def __init__(self) -> None:
        """Инициализация клиента с токеном из settings и списком резолвнутых моделей."""
        self._logger = logging.getLogger(__name__)
        self._client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)
        self._model_versions = self._resolve_model_versions(REPLICATE_IMAGE_MODELS)

    def _resolve_model_versions(self, model_names: list[str]) -> list[str]:
        """
        Резолвит актуальные версии для списка моделей.

        Возвращает список ref вида 'owner/model:version'. Если для модели
        не удалось получить latest_version, она пропускается.
        """
        resolved: list[str] = []
        for model_name in model_names:
            try:
                model = self._client.models.get(model_name)
                if model.latest_version is not None:
                    resolved.append(f"{model_name}:{model.latest_version.id}")
                    self._logger.info("Resolved %s to version %s", model_name, model.latest_version.id)
                else:
                    self._logger.warning("No latest_version for %s", model_name)
            except Exception as exc:
                self._logger.warning("Failed to resolve latest version for %s: %s", model_name, exc)
        if not resolved:
            raise ValueError("Failed to resolve any Replicate model version")
        return resolved

    def _try_generate(self, model_version: str, prompt: str) -> bytes | None:
        """
        Пытается сгенерировать изображение одной моделью.

        При 429 (rate limit) делает retry через ~10 секунд.
        При успехе возвращает bytes изображения, иначе None.
        """
        for attempt in range(2):
            try:
                output = self._client.run(
                    model_version,
                    input={**REPLICATE_IMAGE_PARAMS, "prompt": prompt},
                )
                result = output[0] if isinstance(output, list) else output
                url = str(result)
                response = httpx.get(url, timeout=REPLICATE_DOWNLOAD_TIMEOUT, follow_redirects=True)
                response.raise_for_status()
                return response.content
            except replicate.exceptions.ReplicateError as exc:
                status = exc.status if hasattr(exc, "status") else 0
                if status == 429 and attempt == 0:
                    self._logger.warning(
                        "Rate limit for %s, waiting 10s before retry...", model_version,
                    )
                    time.sleep(10)
                    continue
                self._logger.warning("Replicate generation failed for %s: %s", model_version, exc)
                return None
            except Exception as exc:
                self._logger.warning("Replicate generation failed for %s: %s", model_version, exc)
                return None
        return None

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
        Генерирует одну иллюстрацию через Replicate и сохраняет в output_path.

        Args:
            keywords: Ключевые слова для промпта
            output_path: Путь для сохранения файла (.png)

        Returns:
            Путь к сохранённому файлу или None при ошибке
        """
        prompt = self._build_prompt(keywords)
        output_path = output_path.with_suffix(".png")

        for model_version in self._model_versions:
            image_bytes = self._try_generate(model_version, prompt)
            if image_bytes is not None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(image_bytes)
                return output_path

        self._logger.warning("All Replicate models failed for prompt: %s", prompt)
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
            # Соблюдаем rate limit Replicate (~6 запросов/мин)
            if idx < len(image_keywords) - 1:
                time.sleep(REPLICATE_RATE_LIMIT_DELAY)

        return results
