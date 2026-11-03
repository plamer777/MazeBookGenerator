"""Общий протокол и batch-цикл для провайдеров иллюстраций."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol


class IllustrationProvider(Protocol):
    """Провайдер иллюстраций: превращает ключевые слова в файл-изображение.

    Реализуют: ReplicateClient, PollinationsClient, HFClient.
    """

    def generate_book_illustrations(
        self,
        image_keywords: list[list[str]],
        output_paths: list[Path],
    ) -> list[Path | None]:
        """Генерирует иллюстрации по ключевым словам в заданные файлы."""
        ...


def generate_batch_with_rate_limit(
    generate_one: Callable[[list[str], Path], Path | None],
    image_keywords: Sequence[list[str]],
    output_paths: Sequence[Path],
    rate_limit_delay: float,
    logger: logging.Logger,
) -> list[Path | None]:
    """
    Генерирует иллюстрации пачкой с паузой между запросами (rate limit API).

    Args:
        generate_one: Функция (keywords, output_path) -> Path | None
        image_keywords: Ключевые слова для каждой страницы
        output_paths: Целевые файлы (по одному на ключевые слова)
        rate_limit_delay: Пауза между запросами в секундах (0 — без паузы)
        logger: Логгер для прогресса

    Returns:
        Список путей к файлам (None если генерация страницы не удалась)
    """
    results: list[Path | None] = []
    total = len(image_keywords)

    for idx, (keywords, output_path) in enumerate(
        zip(image_keywords, output_paths, strict=True)
    ):
        logger.info("Generating illustration %d/%d...", idx + 1, total)
        results.append(generate_one(keywords, output_path))
        if rate_limit_delay > 0 and idx < total - 1:
            time.sleep(rate_limit_delay)

    return results
