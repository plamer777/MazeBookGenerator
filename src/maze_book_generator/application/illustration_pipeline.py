"""Конвейер генерации иллюстраций: цепочка провайдеров с fallback.

Порядок провайдеров задаётся при создании (Replicate -> Pollinations -> HF).
Каждый следующий провайдер догенерирует только страницы, для которых
предыдущие вернули None. Целевые файлы нумеруются по исходному номеру
страницы — fallback-подмножество не перезаписывает чужие page_N.png.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

from maze_book_generator.domain.models import Book
from maze_book_generator.infrastructure.images.providers import IllustrationProvider
from maze_book_generator.settings import IMAGE_STORAGE_SUBDIR

logger = logging.getLogger(__name__)


class IllustrationPipeline:
    """Заполняет пути иллюстраций цепочкой провайдеров по приоритету."""

    def __init__(self, providers: Iterable[IllustrationProvider]) -> None:
        """
        Инициализация конвейера.

        Args:
            providers: Провайдеры в порядке приоритета (первый — основной)
        """
        self._providers = list(providers)

    def generate(
        self, image_keywords: list[list[str]], book_dir: Path
    ) -> list[Path | None]:
        """
        Генерирует иллюстрации по ключевым словам с fallback-цепочкой.

        Args:
            image_keywords: Ключевые слова для каждой уникальной страницы
            book_dir: Директория книги (файлы пишутся в IMAGE_STORAGE_SUBDIR)

        Returns:
            Список путей (None для страниц, где не сработал ни один провайдер)
        """
        # Провайдеры сами создают родительские папки при записи файлов
        illustrations_dir = book_dir / IMAGE_STORAGE_SUBDIR
        output_paths = [
            illustrations_dir / f"page_{i + 1}.png"
            for i in range(len(image_keywords))
        ]
        paths: list[Path | None] = [None] * len(image_keywords)

        for provider in self._providers:
            missing = [i for i, p in enumerate(paths) if p is None]
            if not missing:
                break
            generated = provider.generate_book_illustrations(
                [image_keywords[i] for i in missing],
                [output_paths[i] for i in missing],
            )
            for idx, path in zip(missing, generated, strict=True):
                paths[idx] = path

        return paths


def assign_illustration_paths(book: Book, paths: list[Path | None]) -> None:
    """
    Проставляет пути иллюстраций в страницы книги.

    Пары страниц (maze + solution) с одним номером получают общую иллюстрацию.
    """
    unique_pages = [p for p in book.pages if not p.is_solution]
    solutions = [p for p in book.pages if p.is_solution]

    for page, path in zip(unique_pages, paths, strict=True):
        if path is None:
            continue
        str_path = str(path)
        page.image_path = str_path
        for sol_page in solutions:
            if sol_page.page_number == page.page_number:
                sol_page.image_path = str_path
